#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   feed_port_listening.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/3 16:56   WANG HAN      1.0       上料口监听
"""

# import lib
import time
import uuid

import numpy as np

from l3.utils.method import model_selection, find_nearest_point, change_task_priority
from l3.utils.modbus_client import ModbusClient
from l3.utils.model_reader import ModelReader
from l3.utils.variables import W1, H1, H4, feed_port_coordinates_dict, feed_status_address_dict, feed_type_address_dict, \
    feed_status_dict, feed_type_value_dict, \
    task_priority, feed_rise_height, active, not_empty, \
    H5, status_port, feed_port_dust_warehouse_dict, sub_warehouse_type_dict, sub_warehouse_range_dict, \
    dust_warehouse_sub_warehouse_dict
from lib.dbClient.db_client import DbClient


class ListenFeeding:
    """
    上料口监听
    """

    def __init__(self, task_list, logger, feed_port_id):
        """
        监听几号上料口，并插入任务单
        :param feed_port_id: 上料口id
        :param task_list: 任务单,dict类型
        """
        # 日志对象
        self.logger = logger
        self.feed_port_id = feed_port_id
        # 上料口坐标
        self.feed_port_coordinate = feed_port_coordinates_dict[feed_port_id]
        # 上料口状态的访问地址
        self.feed_status_address = feed_status_address_dict[feed_port_id]
        # 上料类型的访问地址
        self.feed_type_address = feed_type_address_dict[feed_port_id]
        self.task_list = task_list  # 任务单
        # 自带数据库
        self.db_client = DbClient()
        # 连接数据库
        self.db_client.connect()

        self.model = None  # 初始化模型
        self.t = None
        self.stop = False

    def get_model(self, warehouse_type, x_range, y_range):
        """
        获取最新的料场模型
        """
        try:
            model_reader = ModelReader()  # 模型阅读器
            self.logger.info("获取模型")
            self.logger.info("warehouse_type, x_range, y_range: {0},{1},{2}".format(warehouse_type, x_range, y_range))
            model_reader = model_reader.connect(warehouse_type, x_range, y_range)
            model = model_reader.read()  # 获取模型
            model_reader.close()  # 关闭数据库连接
            return model
        except Exception as e:
            self.logger.error(str(e))
            self.logger.error("获取模型失败，请检查原因")

    def listen(self):
        """
        开始监听每个上料口
        """

        status_reader = ModbusClient(port=status_port)  # 建立状态池连接
        feed_type = None  # 初始化上料类型为空
        task_id_record = []  # 已安排的任务记录表，用于判断这些任务是否完成
        no_empty_area = None
        while not self.stop:
            # 当没有停止指令时

            # 先记录原先的上料类型
            feed_type_old = feed_type

            # 开始判断上料口状态

            # 通过地址获取状态
            status_code = status_reader.get(self.feed_status_address)  # 读取所有的设备状态
            status = feed_status_dict[status_code]

            # 获取当前的上料类型 ,先记录原来的上料类型

            feed_type_code = status_reader.get(self.feed_type_address)  # 读取所有的设备状态
            feed_type = feed_type_value_dict[feed_type_code]

            # 通过上料类型获取对应料场的范围
            x_range, y_range = ([], [])
            for key, value in sub_warehouse_type_dict.items():
                if value == feed_type:
                    x_range.append(sub_warehouse_range_dict[key][0])
                    y_range.append(sub_warehouse_range_dict[key][1])
            x_range = [x_range[0][0], x_range[-1][-1]]
            y_range = [y_range[0][0], y_range[-1][-1]]

            # 把任务id记录，用于后面判断是否完成
            task_id = str(uuid.uuid1())  # 任务id
            task_id_record.append(task_id)

            # 开始检测上料状态

            if status == "plug" or (feed_type_old is not None and feed_type_old != feed_type):
                # 当检测到堵料或者上料类型切换
                # 检查有没有紧急和一般上料任务
                priority = [task_priority.index('紧急上料'), task_priority.index('上料')]
                is_exists_task, indexes = self.is_exists_task(priority, x_range, y_range, task_type='feed')
                if is_exists_task:
                    # 任务已完成
                    for index in indexes:
                        # 修改任务优先级为已完成
                        self.task_list = change_task_priority(self.task_list, index[0], index[1],
                                                              task_priority.index('已完成'))

            elif status == "emergency feed":
                # 当检测到紧急上料
                # 检查有没有紧急任务
                priority = [task_priority.index('紧急上料')]
                is_exists_emergency_feed_task = self.is_exists_task(priority, x_range, y_range, task_type='feed')[0]
                if not is_exists_emergency_feed_task:
                    # 此时没有紧急上料任务
                    priority = [task_priority.index('上料')]
                    is_exists_feed_task, indexes = self.is_exists_task(priority, x_range, y_range, task_type='feed')
                    if is_exists_feed_task:
                        # 若存在一般上料任务，优先级改为紧急
                        for index in indexes:
                            # 修改任务优先级为紧急
                            self.task_list = change_task_priority(self.task_list, index[0], index[1],
                                                                  task_priority.index('紧急上料'))
                    else:
                        # 若不存在一般上料任务，插入一条
                        # 先获取上料口关联的料场模型
                        model = self.get_model(feed_type, x_range, y_range)
                        # 筛选出主堆区的料堆，高度大于H4，要避开H1/2预留空间
                        model = model_selection(model, axis=1, lt=W1 - H1 / 2)
                        model = model_selection(model, axis=2, gt=H4)
                        # 计算取料点
                        get_coordinates = find_nearest_point(self.feed_port_coordinate, model[:, 0:2])
                        # 放入字典
                        p = task_priority.index('紧急上料')
                        self.task_list[p][task_id] = [get_coordinates, self.feed_port_coordinate, feed_rise_height,
                                                      active, int(time.time())]

            elif status == "feed":
                # 当检测到上料
                # 检查有没有安排上料任务
                priority = [task_priority.index('上料')]
                is_exists_feed_task = self.is_exists_task(priority, x_range, y_range, task_type='feed')[0]
                if not is_exists_feed_task:
                    # 若未安排一般上料任务
                    # 检查该上料口有无关联的除尘仓
                    dust_warehouse_id = feed_port_dust_warehouse_dict[self.feed_port_id]
                    if dust_warehouse_id != -1:
                        # 关联除尘灰仓
                        # 放料点为上料口
                        put_coordinates = self.feed_port_coordinate  # 2维

                        # 任务优先级为普通上料
                        p = task_priority.index('上料')

                        # 获取区域模型
                        # 除尘灰的范围
                        sub_warehouse_no = dust_warehouse_sub_warehouse_dict[dust_warehouse_id]
                        dust_warehouse_range = sub_warehouse_range_dict[sub_warehouse_no]

                        # 已知可抓料区?
                        if not no_empty_area:
                            # 若此时不知道no_empty_area,求no_empty_area，可能出现的情况：1，首次；2,之前的no_empty_area复位
                            # 获取除尘区中24小时以上且不为空的区域
                            sql = "SELECT  *  FROM  dust_warehouse  WHERE  TO_DAYS(NOW()) - TO_DAYS(stack_time) >= 1 and is_empty = {0} and dust_warehouse_id = {1}".format(
                                not_empty, dust_warehouse_id)
                            data = self.db_client.query(sql)  # 满足条件的数据
                            if data:
                                # 存在满足条件的数据

                                # 获取不为空区域
                                no_empty_area = np.array(data)[0][2:4]

                                # 因为是首次对该区域抓料，先抓距上料口最远的点
                                get_coordinates = [dust_warehouse_range[0][0], np.average(no_empty_area)]
                                # 插入任务单
                                self.task_list[p][task_id] = [get_coordinates, put_coordinates, feed_rise_height,
                                                              active, int(time.time())]
                                # 下个循环
                                continue
                        else:
                            # 若此时知道no_empty_area
                            # 判断料场是否为空
                            # 获取该非空置区域的模型
                            no_empty_area_model = self.get_model('chuchen', dust_warehouse_range[0], no_empty_area)
                            if np.max(no_empty_area_model[:, 2]) <= H5:
                                # 区域置空
                                # 上料完毕，更新为空置
                                sql = 'UPDATE dust_warehouse SET is_empty = 1 where boundary_min = %s and ' \
                                      'boundary_max = %s '
                                values = (no_empty_area[0], no_empty_area[1])
                                self.db_client.execute(sql, values)

                                # 可抓取区复位
                                no_empty_area = None
                            else:
                                # 区域非空
                                # 抓料点集合
                                no_empty_area_get_coordinates = model_selection(no_empty_area_model, axis=2, gt=H5)
                                # 先抓最远点 ,x坐标最小
                                get_coordinates = no_empty_area_get_coordinates[
                                                      np.argmin(no_empty_area_get_coordinates[:, 0])][:, 0:2]
                                # 插入任务单
                                self.task_list[p][task_id] = [get_coordinates, put_coordinates, feed_rise_height,
                                                              active, int(time.time())]
                                # 下个循环
                                continue

                    # 若上述条件均不满足

                    # 开始寻找有无倒料的任务，准备合并
                    priority = [task_priority.index('紧急清理卸料区'), task_priority.index('清理卸料区'),
                                task_priority.index('清理缓冲区')]  # 可以被合并的倒料任务优先级
                    # 寻找有无倒料任务
                    is_exists_upload_task, indexes = self.is_exists_task(priority, x_range, y_range, task_type='upload')
                    if is_exists_upload_task:
                        # 若存在倒料任务
                        # 将第一条倒料任务改为上料
                        index = indexes[0]
                        # 修改任务优先级为普通上料
                        self.task_list = change_task_priority(self.task_list, index[0], index[1],
                                                              task_priority.index('上料'))
                        # 修改目的地为上料口
                        self.task_list[index[0]][index[1]][1] = self.feed_port_coordinate
                        # 修改高度为上料高度
                        self.task_list[index[0]][index[1]][2] = feed_rise_height
                    else:
                        # 若不存在倒料任务，插入一条上料
                        # 先获取上料口关联的料场模型
                        model = self.get_model(feed_type, x_range, y_range)
                        # 筛选出主堆区的料堆，高度大于H4，要避开H1/2预留空间
                        model = model_selection(model, axis=1, lt=W1 - H1 / 2)
                        model = model_selection(model, axis=2, gt=H4)
                        # 计算取料点
                        get_coordinates = find_nearest_point(self.feed_port_coordinate, model[:, 0:2])
                        # 放入字典
                        p = task_priority.index('上料')
                        self.task_list[p][task_id] = [get_coordinates, self.feed_port_coordinate, feed_rise_height,
                                                      active, int(time.time())]
            else:
                # 此时为不上料
                # 删除已完成的该模块产生的上料任务
                for taskId in task_id_record:
                    try:
                        p = task_priority.index('已完成')
                        self.logger.info('任务已完成' + str(self.task_list[p][taskId]))
                        self.task_list[p].pop(taskId)
                    except KeyError:
                        continue
                    else:
                        task_id_record.remove(taskId)

            # 进入下个循坏

    def is_exists_task(self, priority, x_range, y_range, task_type='feed'):
        """
        根据任务单、优先级和上料口id，返回是否存在相关 激活 的任务
        :param task_type: 任务类型
        :param priority:  优先级，元组或列表类型
        :param x_range:  范围
        :param y_range:  范围
        :return: 是否存在符合条件的任务和任务索引
        """
        indexes = []
        if task_type == 'feed':
            for p in priority:
                task_list0 = self.task_list[p]
                for i in task_list0:
                    # 放料点为该上料口，且激活
                    if task_list0[i][1] == self.feed_port_coordinate and task_list0[i][3] == active:
                        indexes.append([p, i])
            if len(indexes) == 0:
                return False, None
            else:
                return True, indexes
        elif task_type == 'upload':
            min_dis = np.inf
            for p in priority:
                task_list0 = self.task_list[p]
                for i in task_list0:
                    # 取料点为该上料口关联的料仓，且激活
                    if x_range[1] >= task_list0[i][0][0] >= x_range[0] \
                            and y_range[1] >= task_list0[i][0][1] >= y_range[0] \
                            and task_list0[i][3] == active:
                        dis = (task_list0[i][0][0] - self.feed_port_coordinate[0]) ** 2 \
                              + (task_list0[i][0][1] - self.feed_port_coordinate[1]) ** 2
                        # 取料点距离该上料口距离最近的倒料任务
                        if dis <= min_dis:
                            min_dis = dis
                            indexes.append([p, i])
            if len(indexes) == 0:
                return False, None
            else:
                return True, indexes

    def run(self):
        """
        开始产生任务，异步运行
        """
        import threading
        self.t = threading.Thread(target=self.listen)
        self.t.start()

    def stop(self):
        """
        结束产生任务
        """
        self.stop = True  # 停止产生任务
        # 关闭数据库
        self.db_client.close()
        self.t.join()
