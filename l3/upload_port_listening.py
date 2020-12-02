#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   upload_port_listening.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/6 11:37   WANG HAN      1.0        卸料口监听
"""

# import lib

from l3.utils.method import model_selection, change_task_priority
from l3.utils.modbus_client import ModbusClient
from l3.utils.model_reader import ModelReader
from l3.utils.variables import uploading_port_address_dict, W2, \
    H3, uploading_port_status_dict, task_priority, car_is_allow_address, allow_code_dict, scan_is_allow_address, \
    active, hang, l2_port, status_port, upload_port_sub_warehouse_dict, sub_warehouse_range_dict, \
    sub_warehouse_type_dict


class ListenUploading:
    """
    卸料口监听
    """

    def __init__(self, task_list, logger, upload_port_id):
        """
        监听几号卸料口，并传入任务单
        :param upload_port_id: 卸料口id
        :param task_list: 任务单,dict类型
        """
        # 日志对象
        self.logger = logger
        # 卸料口状态的访问地址
        self.uploading_port_address = uploading_port_address_dict[upload_port_id]
        # 对应的子料场id
        sub_warehouse_no = upload_port_sub_warehouse_dict[upload_port_id]
        # 卸料区的范围
        self.x_range = sub_warehouse_range_dict[sub_warehouse_no][0]
        self.y_range = sub_warehouse_range_dict[sub_warehouse_no][1]
        # 料场类型
        self.warehouse_type = sub_warehouse_type_dict[sub_warehouse_no]
        # L2客户端
        self.l2_client = ModbusClient(port=l2_port)
        # 初始化
        self.task_list = task_list  # 任务单
        self.t = None
        self.stop = False

    def get_model(self):
        """
        获取最新的料场模型
        """
        try:
            self.logger.info("开始获取模型")
            model_reader = ModelReader()  # 模型阅读器
            self.logger.info("料场类型, range: {0},{1},{2}".format(self.warehouse_type, self.x_range, self.y_range))
            model_reader.connect(self.warehouse_type, self.x_range, self.y_range)
            model = model_reader.read()  # 获取模型
            model_reader.close()
            return model
        except Exception as e:
            self.logger.error(str(e))
            self.logger.error("获取模型失败，请检查原因")

    def is_enable_into_car(self):
        """
        是否允许进车
        """
        # 获取模型
        model = self.get_model()
        model = model_selection(model, axis=1, gt=W2)  # 3号堆模型，卸料区
        model = model_selection(model, axis=2, ge=H3)  # 卸料区高度大于H3（卸料区限高）
        if model.shape[0] == 0:
            # 无高于限高的料堆
            # 允许进车
            return True
        else:
            # 不允许进车
            return False

    def listen(self):
        """
        开始监听
        """
        status_reader = ModbusClient(port=status_port)  # 建立状态池连接
        # 此时无车
        no_car_coming = True
        while not self.stop:
            # 当没有停止指令时
            # 开始判断上料口状态

            # 通过地址获取卸料口状态
            status_code = status_reader.get(self.uploading_port_address)  # 读取所有的设备状态
            status = uploading_port_status_dict[status_code]

            # 开始检测卸料状态

            if no_car_coming and status == "come":
                # 当此时无车且监听到来车
                # 检查有没有来车紧急任务
                priority = [task_priority.index('来车紧急清理卸料区')]
                is_exists_car_emergency_task = self.is_exists_task(priority)[0]

                if not is_exists_car_emergency_task:
                    # 不存在来车紧急清理任务
                    priority = [task_priority.index('紧急清理卸料区')]
                    is_exists_emergency_task, indexes = self.is_exists_task(priority)

                    if is_exists_emergency_task:
                        # 存在紧急清理卸料区任务
                        # 修改任务优先级为来车紧急清理
                        for index in indexes:
                            self.task_list = change_task_priority(self.task_list, index[0], index[1],
                                                                  task_priority.index('来车紧急清理卸料区'))
                    else:
                        # 不存在紧急清理卸料区任务
                        if self.is_enable_into_car():
                            # 允许进车
                            self.l2_client.set(car_is_allow_address, allow_code_dict['allow'])
                            # 状态更新为有车正在进入
                            no_car_coming = False
                            # 挂起该区域的所有倒料任务
                            priority = [task_priority.index('来车紧急清理卸料区'), task_priority.index('紧急清理卸料区'),
                                        task_priority.index('清理卸料区')]
                            is_exists_upload_task, indexes = self.is_exists_task(priority)

                            if is_exists_upload_task:
                                for index in indexes:
                                    # 修改任务状态为挂起
                                    self.task_list[index[0]][index[1]][3] = hang

            elif status == "upload":
                # 当此监听到正在卸料
                # 检查该区域的所有倒料任务是否挂起
                priority = [task_priority.index('来车紧急清理卸料区'), task_priority.index('紧急清理卸料区'),
                            task_priority.index('清理卸料区')]
                is_exists_upload_task, indexes = self.is_exists_task(priority)

                if is_exists_upload_task:
                    # 若存在激活任务，则挂起
                    for index in indexes:
                        # 修改任务状态为挂起
                        self.task_list[index[0]][index[1]][3] = hang

            elif status == "leave" and not no_car_coming:
                # 当此时有车，且监听到车要走
                # 有挂起任务？
                priority = [task_priority.index('来车紧急清理卸料区'), task_priority.index('紧急清理卸料区'),
                            task_priority.index('清理卸料区')]
                is_exists_hang_task, indexes = self.is_exists_task(priority, status=hang)

                if is_exists_hang_task:
                    # 若存在挂起任务，则激活
                    for index in indexes:
                        # 修改任务状态为激活
                        self.task_list[index[0]][index[1]][3] = active

                # 允许扫描
                self.l2_client.set(scan_is_allow_address, allow_code_dict['allow'])

                # 状态更新为无车
                no_car_coming = True

    def is_exists_task(self, priority, status=active):
        """
        根据任务单、优先级和上料口id，返回是否存在相关激活的倒料任务
        :param priority:  优先级，元组或列表类型
        :param status:  任务状态
        :return: 是否存在符合条件的任务和任务索引
        """
        indexes = []
        for p in priority:
            task_list0 = self.task_list[p]
            for i in task_list0:
                # 取料点为该卸料口的仓库区域，且判断状态
                if self.x_range[1] >= task_list0[i][0][0] >= self.x_range[0] \
                        and self.y_range[1] >= task_list0[i][0][1] >= self.y_range[0] \
                        and task_list0[i][3] == status:
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
        self.t.join()
