#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   generate_task.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/2 19:17   WANG HAN      1.0     产生倒料任务
"""

# import lib
import time
import uuid

import numpy as np

from l3.utils.method import model_selection, find_nearest_point, predict_model
from l3.utils.model_reader import ModelReader
from l3.utils.variables import W2, radius, W1, H1, H2, H3, H4, \
    safety_height, task_priority, active, task_num, sub_warehouse_range_dict, sub_warehouse_type_dict


def cal_put_coordinates(boundary_center_coordinates, put_coordinates_array):
    """
    计算放料点，原则是先放中心区，从远至近
    :param boundary_center_coordinates: 该区域离上料口最近的边界中心点位置
    :param put_coordinates_array:  可放料点集合
    :return: 放料点坐标
    """
    # 在中心方向上的可放料点
    can_put_coordinate = model_selection(put_coordinates_array, axis=0, eq=boundary_center_coordinates[0])
    if can_put_coordinate.shape[0] != 0:
        # 在中心方向上有可放料点
        # 取距上料口最近的点
        put_coordinates = can_put_coordinate[np.argmin(can_put_coordinate[:, 1])]
    else:
        # 在中心方向上无可放料点
        # 取距中心方向最近点放料
        put_coordinates = find_nearest_point(boundary_center_coordinates, put_coordinates_array)
    return put_coordinates


class GenerateTask:
    """
    任务产生的主线程
    """

    def __init__(self, task_list, logger, sub_warehouse_no):
        """
        根据子仓库编号的料场模型产生倒料任务，并插入任务单
        :param sub_warehouse_no: 子仓库编号
        :param task_list: 任务单,dict类型
        """
        # 日志对象
        self.logger = logger
        self.sub_warehouse_no = sub_warehouse_no
        self.task_list = task_list  # 任务单
        # 连接数据库
        self.model_reader = self.connect_db()
        # 初始化
        self.model = None  # 初始化模型
        self.t = None  # 产生任务的线程
        self.generate_completed = False  # 任务规划未完成
        self.stop = False  # 是否继续产生任务的结束标志

    def connect_db(self):
        """
        连接数据库
        """
        model_reader = ModelReader()  # 模型阅读器
        warehouse_type = sub_warehouse_type_dict[self.sub_warehouse_no]
        x_range = sub_warehouse_range_dict[self.sub_warehouse_no][0]
        y_range = sub_warehouse_range_dict[self.sub_warehouse_no][1]
        model_reader.connect(warehouse_type, x_range, y_range)
        return model_reader

    def update_model(self):
        """
        更新料场模型
        """
        try:
            self.model = self.model_reader.update()
        except ConnectionRefusedError:
            self.logger.error("子料仓" + str(self.sub_warehouse_no) + "数据库未连接,请先调用connect_db方法")

    def generate(self):
        """
        开始产生任务
        """
        while not self.stop:
            # 当没有停止指令时
            # 开始规划任务
            perform_completed = False  # 规划的task_num任务执行完成数量
            generate_times = 0  # 规划的次数
            task_id_record = []  # 已安排的任务记录表，用于判断这些任务是否完成

            # 更新模型
            self.update_model()

            # 开始规划任务小于每批次产生的任务数量，由于任务规划中模型是靠预测出来的，所以此任务数量不宜设置过大
            while generate_times < task_num:
                # 规划的次数 +1
                generate_times += 1
                # 模型划分
                model3 = model_selection(self.model, axis=1, gt=W2)  # 3号堆模型，卸料区
                # 2号堆模型，缓冲区，前预留H2/2空间，防止坡度过大
                model2 = model_selection(self.model, axis=1, ge=W1 - radius, le=W2 - H2 / 2)
                model1 = model_selection(self.model, axis=1, le=W1 - H1 / 2)  # 1号堆模型，主堆区，预留H1/2空间，防止坡度过大

                # 需倒料点集
                unload_stock_emergency_clean_points = model_selection(model3, axis=2, ge=H3)  # 紧急清理卸料区点集
                unload_stock_clean_points = model_selection(model3, axis=2, ge=H4, lt=H3)  # 清理卸料区点集
                cache_stock_clean_points = model_selection(model2, axis=2, ge=H2)  # 清理缓冲区点集

                # 可堆放点集

                # 主堆区分三层
                if np.min(model1[:, 2]) < H1 / 3:
                    main_stock_can_stacked_points = model_selection(model1, axis=2, lt=H1 / 3)[:, 0:2]  # 主堆区可堆放点（二维）

                elif 2 * H1 / 3 >= np.min(model1[:, 2]) >= H1 / 3:
                    # 主堆区可堆放点（二维）
                    main_stock_can_stacked_points = model_selection(model1, axis=2, lt=2 * H1 / 3)[:, 0:2]

                else:
                    main_stock_can_stacked_points = model_selection(model1, axis=2, lt=H1)[:, 0:2]  # 主堆区可堆放点（二维）

                # 缓冲区分二层
                if np.min(model2[:, 2]) < H2 / 2:
                    cache_stock_can_stacked_points = model_selection(model2, axis=2, lt=H2 / 2)[:, 0:2]  # 缓冲区可堆放点（二维）

                else:
                    cache_stock_can_stacked_points = model_selection(model2, axis=2, lt=H2)[:, 0:2]  # 缓冲区可堆放点（二维）

                # 提升高度
                h1 = np.max(model1[:, 2]) + safety_height  # 送往1号堆的提升高度，1号堆最高+抓斗安全距离
                h2 = np.max(model2[:, 2]) + safety_height  # 送往2号堆的提升高度，2号堆最高+抓斗安全距离

                # 开始产生任务
                get_coordinates = np.array([])
                put_coordinates = np.array([])
                task_id = str(uuid.uuid1())

                # 把任务id记录，用于后面判断是否完成
                task_id_record.append(task_id)

                # 有紧急清理卸料区点
                if unload_stock_emergency_clean_points.shape[0] >= 0:
                    # 先抓其中的最高点
                    get_coordinates = unload_stock_emergency_clean_points[
                        np.argmax(unload_stock_emergency_clean_points[:, 2])]
                    # 在缓冲区计算放料点
                    # 缓冲区边界中心点
                    boundary_center_coordinates = [np.average(sub_warehouse_range_dict[self.sub_warehouse_no][0]), W1]
                    put_coordinates = cal_put_coordinates(boundary_center_coordinates, cache_stock_can_stacked_points)
                    # 抓料点和取料点之间的最高高度，从卸料区到缓冲区
                    h = max(h2, get_coordinates[2] + safety_height)
                    # 插入任务
                    p = task_priority.index('紧急清理卸料区')
                    self.task_list[p][task_id] = [get_coordinates[0:2], put_coordinates, h, active,
                                                  int(time.time())]
                    # 需要倒料，任务规划进行中
                    self.generate_completed = False

                # 有清理卸料区点
                elif unload_stock_clean_points.shape[0] >= 0:
                    # 先抓其中的最高点
                    get_coordinates = unload_stock_clean_points[np.argmax(unload_stock_clean_points[:, 2])]
                    # 在主堆区计算放料点
                    boundary_center_coordinates = [np.average(sub_warehouse_range_dict[self.sub_warehouse_no][0]),
                                                   sub_warehouse_range_dict[self.sub_warehouse_no][1][0]]
                    put_coordinates = cal_put_coordinates(boundary_center_coordinates, main_stock_can_stacked_points)
                    # 抓料点和取料点之间的最高高度，从卸料区到主堆区
                    h = max(h1, h2, get_coordinates[2] + safety_height)
                    # 放入字典
                    p = task_priority.index('清理卸料区')
                    self.task_list[p][task_id] = [get_coordinates[0:2], put_coordinates, h, active,
                                                  int(time.time())]
                    # 需要倒料，任务规划进行中
                    self.generate_completed = False

                # 有清理缓冲区点
                elif cache_stock_clean_points.shape[0] >= 0:
                    # 先抓其中的最高点
                    get_coordinates = cache_stock_clean_points[np.argmax(cache_stock_clean_points[:, 2])]
                    # 在主堆区计算放料点
                    boundary_center_coordinates = [np.average(sub_warehouse_range_dict[self.sub_warehouse_no][0]),
                                                   sub_warehouse_range_dict[self.sub_warehouse_no][1][0]]
                    put_coordinates = cal_put_coordinates(boundary_center_coordinates, main_stock_can_stacked_points)
                    # 抓料点和取料点之间的最高高度，从缓冲区到主堆区
                    h = max(h1, get_coordinates[2] + safety_height)
                    # 放入字典
                    p = task_priority.index('清理缓冲区')
                    self.task_list[p][task_id] = [get_coordinates[0:2], put_coordinates, h, active,
                                                  int(time.time())]
                    # 需要倒料，任务规划进行中
                    self.generate_completed = False

                # 无需倒料
                else:
                    self.generate_completed = True  # 任务规划完毕

                # 任务规划后的模型预测
                self.model = predict_model(get_coordinates, put_coordinates, self.model)

                # 判断任务是否规划完毕
                if not self.generate_completed:
                    continue
                else:
                    break

            # 开始判断任务是否完成
            while not perform_completed:
                for taskId in task_id_record:
                    try:
                        p = task_priority.index('已完成')
                        self.logger.info("子料仓" + str(self.sub_warehouse_no) + '任务已完成' + str(self.task_list[p][taskId]))
                    except KeyError:
                        perform_completed = False
                        break
                    else:
                        perform_completed = True
                time.sleep(1)

            # 删除已完成任务
            for taskId in task_id_record:
                p = task_priority.index('已完成')
                self.task_list[p].pop(taskId)

            # 继续循环

    def run(self):
        """
        开始产生任务，异步运行
        """
        import threading
        self.logger.info("子料仓" + str(self.sub_warehouse_no) + '产生倒料任务的线程开始运行')
        self.t = threading.Thread(target=self.generate)
        self.t.start()

    def stop(self):
        """
        结束产生任务
        """
        self.stop = True  # 停止产生任务
        self.model_reader.close()  # 关闭数据库连接
        self.t.join()  # 阻塞
        self.logger.info("子料仓" + str(self.sub_warehouse_no) + '产生倒料任务的线程结束运行')
