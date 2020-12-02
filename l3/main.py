#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   main.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/9 10:00   WANG HAN      1.0         None
"""

# import lib
import time
import uuid

from l3.dust_warehouse_listening import DustWarehouseListening
from l3.feed_port_listening import ListenFeeding
from l3.generate_task import GenerateTask
from l3.upload_port_listening import ListenUploading
from l3.utils.modbus_client import ModbusClient
from l3.utils.variables import feed_communication_address, upload_communication_address, tri_d_status_address, \
    feed_communication_status_dict, upload_communication_status_dict, tri_d_status_dict, mode_address, \
    control_command_address, control_command_dict, mode_dict, feed_port_num, \
    task_priority, active, status_port, l2_port, upload_port_num, dust_warehouse_num, sub_warehouse_type_dict
from lib.logger.log import Logger

# 日志对象
logger = Logger(file_name='l3')


def get_status_pool():
    """
    判断各外围设备的状态
    :return: bool，状态是否OK
    """
    status_reader = ModbusClient(port=status_port)  # 建立状态池连接
    all_status_address = [feed_communication_address, upload_communication_address, tri_d_status_address]
    code = status_reader.mget(all_status_address)  # 读取所有的设备状态
    status = [feed_communication_status_dict[code[0]], upload_communication_status_dict[code[1]],
              tri_d_status_dict[code[2]]]
    if status == ['normal', 'normal', 'normal']:
        # 状态正常
        return True
    else:
        logger.error("feed_communication_address, upload_communication_address, tri_d_status_address状态异常，状态为"
                     + str(status))
        return False


def shift_auto_and_run():
    """
        监听是否变成全自动运动模式
        :return: bool，状态是否OK
    """
    l2_client = ModbusClient(port=l2_port)  # L2客户端
    all_status_address = [mode_address, control_command_address]
    code = l2_client.mget(all_status_address)  # 读取所有的设备状态
    logger.error("l2_client通讯中断，请检查L2的Modbus_server连接")
    status = [mode_dict[code[0]], control_command_dict[code[1]]]
    if status == ['auto', 'run']:
        # 全自动模式，且是运行
        return True
    else:
        logger.error("mode_address, control_command_address状态异常，状态为"
                     + str(status))
        return False


def generate_standby_task(task_list, task_id):
    """
    产生待机任务
    :param task_list:传入任务单
    :param task_id: 任务id
    :return: 插入后的task_list
    """
    # 产生待机任务
    p = task_priority.index('待机')
    task_list[p][task_id] = [None, None, None, active, int(time.time())]
    return task_list


def do_not_need_upload(generate_task_list):
    """
    判断各个子料场是否都完成倒料规划，如果是，则返回true，只要还存在一个子料场还需倒料，返回false
    :param generate_task_list: 子料场产生任务对象集合
    :return: 
    """
    for generate_task in generate_task_list:
        if not generate_task.generate_completed:
            return False
    return True


def run_l3(task_list):
    """
    运行L3
    :param task_list:
    :return:
    """
    # 实例化
    try:
        # 子料场产生任务的对象集合
        logger.info('开始实例化产生任务的对象集合')
        generate_task_list = []
        # 非除尘仓的产生任务对象
        for key, value in sub_warehouse_type_dict.items():
            if value != 'chuchen':
                generate_task_list.append(GenerateTask(task_list, logger, sub_warehouse_no=key))

        # 上料口监听的对象集合
        logger.info('开始实例化上料口监听的对象集合')
        listen_feeding_list = []
        for i in range(feed_port_num):
            listen_feeding_list.append(ListenFeeding(task_list, logger, feed_port_id=i))

        # 卸料口监听的对象集合
        logger.info('开始实例化卸料口监听的对象集合')
        listen_uploading_list = []
        for i in range(upload_port_num):
            listen_uploading_list.append(ListenUploading(task_list, logger, upload_port_id=i))

        # 除尘仓对象集合
        logger.info('开始实例化除尘仓对象集合')
        dust_warehouse_listening_list = []
        for i in range(dust_warehouse_num):
            dust_warehouse_listening_list.append(DustWarehouseListening(task_list, logger, dust_warehouse_id=i))

    except Exception as e:
        logger.error("实例化失败，错误原因：" + str(e))

    else:

        # 初始化状态
        auto_and_run = False  # 当前不是全自动运行模式
        arrange_standby_task = False  # 当前未安排待机任务

        # 开始运行
        logger.info('开始运行L3系统')
        while True:

            # 待机任务id
            task_id = str(uuid.uuid1())
            try:
                shift_auto_and_run_status = shift_auto_and_run()
            except ConnectionRefusedError:
                logger.error("l2_client通讯中断，请检查L2的Modbus_server连接")
                time.sleep(100)
                continue
            else:

                if shift_auto_and_run_status and not auto_and_run:
                    # 当监听到L2刚切换到全自动运行模式

                    # 先产生一条待机任务
                    task_list = generate_standby_task(task_list, task_id)

                    # 等待该待机任务执行完成
                    while True:
                        try:
                            p = task_priority.index('已完成')
                            logger.info('待机任务已完成' + str(task_list[p][task_id]))
                        except KeyError:
                            # 任务未完成
                            time.sleep(0.1)
                            continue
                        else:
                            # 任务已完成
                            # 删除已完成任务
                            task_list[p].pop(task_id)
                            break

                    try:
                        # 获取状态池当各状态
                        is_all_status_ok = get_status_pool()
                    except ConnectionRefusedError:
                        logger.error("状态池通讯中断，请检查状态池的连接")
                        time.sleep(100)
                        continue
                    else:
                        # 开始判断状态池当各状态
                        if is_all_status_ok:
                            # 状态均正常，异步启动四个模块

                            # 启动任务产生模块
                            for generate_task in generate_task_list:
                                generate_task.run()

                            # 启动上料口监听模块
                            for listen_feeding in listen_feeding_list:
                                listen_feeding.run()

                            # 启动上料口监听模块
                            for listen_uploading in listen_uploading_list:
                                listen_uploading.run()

                            # 启动除尘灰监听
                            for dust_warehouse_listening in dust_warehouse_listening_list:
                                dust_warehouse_listening.run()

                            # 启动成功
                            auto_and_run = True

                # 当监听到L2刚切换到不是全自动且运行状态下
                elif not shift_auto_and_run_status and auto_and_run:

                    # 结束各子模块
                    for generate_task in generate_task_list:
                        generate_task.stop()

                    for listen_feeding in listen_feeding_list:
                        listen_feeding.stop()

                    for listen_uploading in listen_uploading_list:
                        listen_uploading.stop()

                    for dust_warehouse_listening in dust_warehouse_listening_list:
                        dust_warehouse_listening.stop()

                    # 结束成功
                    auto_and_run = False

                elif shift_auto_and_run_status and auto_and_run:
                    # 各状态正常，且四个模块正在异步运行中

                    # 判断各子料场是否倒料任务完成且待机任务是否安排
                    if do_not_need_upload(generate_task_list) and not arrange_standby_task:

                        # 如果每个子料场都无需倒料，且未安排待机任务
                        # 则产生待机任务至任务序列中

                        task_list = generate_standby_task(task_list, task_id)
                        arrange_standby_task = True

                    else:
                        # 删除已完成的待机任务
                        try:
                            p = task_priority.index('已完成')
                            # 删除已完成任务
                            task_list[p].pop(task_id)
                        except KeyError:
                            # 没有已完成的待机任务
                            continue
                        else:
                            # 待机任务执行完成，状态改为未安排待机任务
                            arrange_standby_task = False
