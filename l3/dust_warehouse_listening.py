#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   dust_warehouse_listening.py    
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/12 20:43   WANG HAN      1.0      除尘灰仓监听
"""

# import lib
import datetime
import time
import uuid

import numpy as np

from l3.utils.method import model_selection, predict_model
from l3.utils.modbus_client import ModbusClient
from l3.utils.model_reader import ModelReader
from l3.utils.variables import dust_warehouse_address_dict, W3, dust_stack_area_size, radius, H4, \
    dust_warehouse_status_dict, empty, \
    dust_warehouse_get_coordinates_dict, dust_stack_times, increase_height, safety_height, task_priority, active, H5, \
    status_port, sub_warehouse_range_dict, dust_warehouse_sub_warehouse_dict
from lib.dbClient.db_client import DbClient


class DustWarehouseListening:
    """
    除尘灰仓监听
    """

    def __init__(self, task_list, logger, dust_warehouse_id):
        """
        监听几号卸料口，并传入任务单
        :param dust_warehouse_id: 除尘灰id
        :param task_list: 任务单,dict类型
        """
        # 日志对象
        self.logger = logger
        # 卸料口状态的访问地址
        self.dust_warehouse_address = dust_warehouse_address_dict[dust_warehouse_id]
        # 子料场的表名和范围
        sub_warehouse_no = dust_warehouse_sub_warehouse_dict[dust_warehouse_id]
        dust_warehouse_range = sub_warehouse_range_dict[sub_warehouse_no]
        self.x_range = dust_warehouse_range[0]
        self.y_range = dust_warehouse_range[1]
        # 数据库链接
        self.db_client = DbClient()
        self.db_client.connect()
        # 初始化
        self.dust_warehouse_id = dust_warehouse_id
        self.task_list = task_list  # 任务单
        self.t = None
        self.stop = False

    def get_stack_boundaries(self):
        """
        获取堆料区的Y方向范围，该范围为可作业范围，去除了行车影响半径
        """
        # 堆料区范围
        stack_y_range = []
        position = W3
        # 当最后一个区域距料场终点在一个和两个主堆区距离之间，将其作为最后一个区域的长度
        while not dust_stack_area_size <= self.y_range[1] + radius - position < 2 * dust_stack_area_size:
            stack_y_range.append([position + radius, min(position + dust_stack_area_size - radius, self.y_range[1])])
            position = position + dust_stack_area_size
        stack_y_range.append([position + radius, self.y_range[1]])
        return stack_y_range

    def check_config(self):
        """
        当检测到配置文件更改后，将表清零
        """
        sql = "select * from dust_warehouse where dust_warehouse_id = {0}".format(self.dust_warehouse_id)
        data = self.db_client.query(sql)
        # 配置中的边界
        config_stack_boundary = self.get_stack_boundaries()
        if data:
            # 当表不为空
            data = np.array(data)
            # 数据库中边界
            database_stack_boundary = data[:, [2, 3]].tolist()
            # 检查配置有无改动
            if database_stack_boundary != config_stack_boundary:
                # 发现配置改动
                # 清空表
                sql = "delete from dust_warehouse where dust_warehouse_id = {0}".format(self.dust_warehouse_id)
                self.db_client.execute(sql)
                return tuple()
            else:
                return data

    def generate_data_2_db(self):
        """
        如果表为空，则生成数据
        :return: list类型的数据
        """
        # 获取模型
        model = self.get_model()
        # 记录当前时间
        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 读取配置
        config_stack_boundary = self.get_stack_boundaries()
        # 插入数据
        generate_data = []
        for boundary in config_stack_boundary:
            # 筛选出模型
            model0 = model_selection(model, axis=1, ge=boundary[0], lt=boundary[1])
            # 空的条件是，该区域最高点小于H5
            is_empty = int(np.max(model0[:, 2]) < H5)
            # 插入新纪录
            sql = "insert into test(id, dust_warehouse_id, boundary_min, boundary_max, stack_time, is_empty) values(" \
                  "%s, %s, %s,%s, %s,%s) "
            values = (str(uuid.uuid1()), self.dust_warehouse_id, boundary[0], boundary[1], date_time, is_empty)
            generate_data.append(list(values))
            self.db_client.execute(sql, values)
        return generate_data

    def get_model(self):
        """
        获取最新的料场模型
        """
        try:
            self.logger.info("开始获取模型")
            model_reader = ModelReader()  # 模型阅读器
            self.logger.info("除尘仓, range: {0},{1}".format(self.x_range, self.y_range))
            model_reader.connect('chuchen', self.x_range, self.y_range)
            model = model_reader.read()  # 获取模型
            model_reader.close()
            return model
        except Exception as e:
            self.logger.error(str(e))
            self.logger.error("获取模型失败，请检查原因")

    def listen(self):
        """
        开始监听
        """
        status_reader = ModbusClient(port=status_port)  # 建立状态池连接

        # 放置次数
        put_times = 0

        # 无需倒料
        completed = True

        # 空置区域
        empty_area = None

        while not self.stop:
            # 当没有停止指令时
            # 开始监听除灰仓

            # 通过地址获取卸料口状态
            status_code = status_reader.get(self.dust_warehouse_address)  # 读取所有的设备状态
            status = dust_warehouse_status_dict[status_code]

            # 任务id
            task_id = str(uuid.uuid1())

            # 开始检测
            if completed and status == "allow":
                # 当前监听到需要倒料
                # 当检测到配置文件更改后，将表清零
                data = self.check_config()  # tuple类型

                if not data:
                    # 如果表为空，则根据模型插入数据至数据库中，并记录插入的数据
                    data = self.generate_data_2_db()  # list类型

                # 数据转为array
                data = np.array(data)[:, 2:]

                # 寻找一个最近的空置区域
                if empty_area is None:
                    # 判断条件：状态为空置
                    empty_area = data[data[:, 3] == empty][0:2][0]

            elif not completed and status == "allow":
                # 当前正在倒料中
                # 从卸料区的固定抓料点抓料
                get_coordinates = dust_warehouse_get_coordinates_dict[self.dust_warehouse_id]  # 2维
                # 在空置区域里，横向X方向从最远至近依次放料
                x = self.x_range[0] + divmod(put_times, dust_stack_times)[0] * radius
                if x >= self.x_range[1]:
                    # 放完一层后，放中间
                    x = np.average(self.x_range)
                # y方向为区域的中心线
                y = np.average(empty_area)
                put_coordinates = [x, y]
                # 插入任务单
                # 抓料点和取料点之间的最高高度，从卸料区到缓冲区
                h = dust_stack_times * increase_height + safety_height

                # 放入任务
                p = task_priority.index('清理除尘仓')
                self.task_list[p][task_id] = [get_coordinates, put_coordinates, h, active, int(time.time())]

                # 开始判断倒料任务是否完成
                while True:
                    try:
                        p = task_priority.index('已完成')
                        self.logger.info('任务已完成' + str(self.task_list[p][task_id]))
                    except KeyError:
                        # 任务未完成
                        time.sleep(1)
                        continue
                    else:
                        # 任务已完成
                        # 删除已完成任务
                        self.task_list[p].pop(task_id)
                        # 结束循环
                        break

                # 放置次数 +1
                put_times += 1

            elif not completed and status == "disallow":
                # 当前不允许倒料，但是任务未完成
                # 获取卸料区模型
                model = self.get_model()
                # 判断卸料区有无H4以上（可抓）的料堆
                can_get_coordinates = model_selection(model, axis=1, le=W3 - radius)
                can_get_coordinates = model_selection(can_get_coordinates, axis=2, ge=H4)
                if can_get_coordinates.shape[0] == 0:
                    # 当没有可抓点时
                    # 获取该区域的模型
                    empty_area_model = model_selection(model, axis=1, ge=empty_area[0], lt=empty_area[1])
                    if np.max(empty_area_model[:, 2]) >= H5:
                        # 料场非空
                        # 堆放完毕，更新区域的堆放时间和非空
                        sql = 'UPDATE dust_warehouse SET stack_time = %s, is_empty = 0 where boundary_min = %s and ' \
                              'boundary_max = %s '
                        values = (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), empty_area[0], empty_area[1])
                        self.db_client.execute(sql, values)
                        # 放置次数清零
                        put_times = 0

                        # 空置区域
                        empty_area = None

                    # 此次倒料完成，跳过以下步骤，进入下个循环，继续监听
                    # 状态更新为无需倒料
                    completed = True
                    continue

                else:
                    # 当有可抓点时
                    # 每次抓完一个最高点后，预测模型，然后再抓下一个最高点，直至预测模型中没有可抓点
                    while np.max(can_get_coordinates[:, 2]) >= H4:
                        # 先抓最高点
                        get_coordinates = can_get_coordinates[np.argmax(can_get_coordinates[:, 2])][0:2]
                        # 在空置区域里，横向X方向从远至近依次放料
                        x = self.x_range[0] + divmod(put_times, dust_stack_times)[0] * radius
                        if x >= self.x_range[1]:
                            # 放完一层后，放中间
                            x = np.average(self.x_range)
                        # y方向为区域的中心线
                        y = np.average(empty_area)
                        put_coordinates = [x, y]
                        # 插入任务单
                        # 抓料点和取料点之间的最高高度，从卸料区到缓冲区
                        h = dust_stack_times * increase_height + safety_height
                        # 放入任务
                        p = task_priority.index('清理除尘仓')
                        self.task_list[p][task_id] = [get_coordinates, put_coordinates, h, active, int(time.time())]

                        # 等待该倒料任务完成
                        while True:
                            try:
                                p = task_priority.index('已完成')
                                self.logger.info('任务已完成' + str(self.task_list[p][task_id]))
                            except KeyError:
                                # 任务未完成
                                time.sleep(1)
                                continue
                            else:
                                # 任务已完成
                                # 删除已完成任务
                                self.task_list[p].pop(task_id)
                                # 结束循环
                                break

                        # 放置次数 +1
                        put_times += 1

                        # 预测模型
                        can_get_coordinates = predict_model(get_coordinates, put_coordinates, can_get_coordinates)

            # 任务未完成，还需要倒料
            completed = False

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
        self.db_client.close()  # 关闭数据库
        self.t.join()
