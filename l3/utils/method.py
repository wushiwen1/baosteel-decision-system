#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   method.py    
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/11 15:16   WANG HAN      1.0         L3的通用方法
"""

# import lib

import numpy as np

from l3.utils.variables import radius, increase_height


def model_selection(model, axis=None, eq=None, ge=None, gt=None, le=None, lt=None):
    """
    输入模型，筛选出模型符合条件的集合

    :param model: 输入模型，np.array
    :param axis: 索引
    :param eq: 高度等于
    :param ge: 高度大于等于阈值
    :param gt: 高度大于阈值
    :param le: 高度小于等于阈值
    :param lt: 高度小于阈值
    :return: np.array
    """
    # 求得条件筛选后的模型
    model0 = model.copy()
    if axis is None:
        raise NameError('axis未申明')
    if eq is not None:
        model0 = model[model[:, axis] == eq]
    elif ge is not None:
        if gt is not None:
            raise SyntaxError('ge,gt重复')
        if le is None and lt is None:
            model0 = model[model[:, axis] >= ge]
        elif le is not None:
            model0 = model[(model[:, axis] <= le) & (model[:, axis] >= ge)]
        elif lt is not None:
            model0 = model[(model[:, axis] < lt) & (model[:, axis] >= ge)]
    elif gt is not None:
        if le is None and lt is None:
            model0 = model[model[:, axis] > gt]
        elif le is not None:
            model0 = model[(model[:, axis] <= le) & (model[:, axis] > gt)]
        elif lt is not None:
            model0 = model[(model[:, axis] < lt) & (model[:, axis] > gt)]
    elif le is not None:
        if lt is not None:
            raise SyntaxError('le,lt重复')
        model0 = model[model[:, axis] <= le]
    elif lt is not None:
        model0 = model[model[:, axis] < lt]
    return model0


def find_nearest_point(input_point, array):
    """
    在array点集里找离input_point最近点
    :param input_point: 输入点 2维，list
    :param array:  待寻找的点集合 2维
    :return: 点集array中离input_point的最近点
    """
    import kdtree
    tree = None
    try:
        tree = kdtree.create(array)
    except ValueError:
        tree = kdtree.create(array.tolist())
    finally:
        output_point = np.array(tree.search_nn(input_point)[0].data)
        return output_point


def change_task_priority(task_list, task_priority_before, task_id, task_priority_after):
    """
    修改任务优先级
    :param task_list:  任务单
    :param task_priority_before: 之前的优先级
    :param task_id: 任务id
    :param task_priority_after: 想要变成的优先级
    """
    task = task_list[task_priority_before][task_id]
    task_list[task_priority_before].pop(task_id)
    task_list[task_priority_after][task_id] = task
    return task_list


# noinspection PyIncorrectDocstring
def predict_model(get_coordinate, put_coordinate, model, reduce_height=None):
    """
    预测一次任务规划后的料场形状
    :param reduce_height: 抓料后的料堆减少高度
    :param model: 输入模型
    :param get_coordinate: 抓取点，2维或三维
    :param put_coordinate: 放料点，2维或三维
    :return: 预测后的模型 ，三维
    """
    # 抓料点更新范围，radius为作业半径
    x_range_get = [get_coordinate[0] - radius, get_coordinate[0] + radius]
    y_range_get = [get_coordinate[1] - radius, get_coordinate[1] + radius]
    idx_get = np.argwhere((model[:, 0] >= x_range_get[0]) & (model[:, 0] <= x_range_get[1]) &
                          (model[:, 1] >= y_range_get[0]) & (model[:, 1] <= y_range_get[1]))
    idx_get = idx_get.reshape(idx_get.shape[0])

    # 放料点更新范围
    x_range_put = [put_coordinate[0] - radius, put_coordinate[0] + radius]
    y_range_put = [put_coordinate[1] - radius, put_coordinate[1] + radius]
    idx_put = np.argwhere((model[:, 0] >= x_range_put[0]) & (model[:, 0] <= x_range_put[1]) &
                          (model[:, 1] >= y_range_put[0]) & (model[:, 1] <= y_range_put[1]))
    idx_put = idx_put.reshape(idx_put.shape[0])

    # 更新模型
    model[idx_get] -= [0, 0, reduce_height]
    model[idx_put] += [0, 0, increase_height]

    return model
