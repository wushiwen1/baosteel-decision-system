#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   variables.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/19 9:21   WANG HAN      1.0      变量表，所有的变量都放这里
"""

# import lib
import os
from configparser import ConfigParser

"""
----------------------------------------------------------------
                        1. 读取配置文件
----------------------------------------------------------------
"""
config = ConfigParser()
config.read(os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + "\\config.ini", encoding='UTF-8')

# 仓库配置

# 产生任务的划分子仓库
sub_warehouse_num = config.getint('WAREHOUSE', 'SUB_WAREHOUSE_NUM')
sub_warehouse_range_dict = eval(config.get('WAREHOUSE', 'SUB_WAREHOUSE_RANGE'))
sub_warehouse_type_dict = eval(config.get('WAREHOUSE', 'SUB_WAREHOUSE_TYPE'))
# 上料口个数与坐标
feed_port_num = config.getint('WAREHOUSE', 'FEED_PORT_NUM')
feed_port_coordinates_dict = eval(config.get('WAREHOUSE', 'FEED_PORT_COORDINATES'))
feed_port_dust_warehouse_dict = eval(config.get('WAREHOUSE', 'FEED_PORT_DUST_WAREHOUSE'))
# 卸料口对应的子料场
upload_port_num = config.getint('WAREHOUSE', 'UPLOAD_PORT_NUM')
upload_port_sub_warehouse_dict = eval(config.get('WAREHOUSE', 'UPLOAD_PORT_SUB_WAREHOUSE'))
# 除尘仓固定抓料点
dust_warehouse_num = config.getint('WAREHOUSE', 'DUST_WAREHOUSE_NUM')
dust_warehouse_sub_warehouse_dict = eval(config.get('WAREHOUSE', 'DUST_WAREHOUSE_SUB_WAREHOUSE'))
dust_warehouse_get_coordinates_dict = eval(config.get('WAREHOUSE', 'DUST_WAREHOUSE_GET_COORDINATES'))

# L3配置
H1 = config.getint('L3', 'H1')
H2 = config.getint('L3', 'H2')
H3 = config.getint('L3', 'H3')
H4 = config.getint('L3', 'H4')  # 抓斗可抓的高度
H5 = config.getint('L3', 'H5')  # 抓斗可抓的高度
# 卸料、缓冲和主堆分界线
W1 = config.getint('L3', 'W1')  # 主堆区和缓冲区分界
W2 = config.getint('L3', 'W2')  # 缓冲区和卸料区分界
W3 = config.getint('L3', 'W3')  # 除尘灰分界线
# 任务优先级
task_priority = config.get('L3', 'PRIORITY')
task_num = config.getint('L3', 'TASK_NUM')
dust_stack_area_size = config.getint('L3', 'DUST_STACK_AREA_SIZE')  # 除尘灰堆料区大小
dust_stack_times = config.getint('L3', 'DUST_STACK_TIMES')  # 除尘灰每层堆几斗
increase_height = config.getint('L3', 'INCREASE_HEIGHT')  # 放料后高度增加
safety_height = config.getint('L3', 'SAFETY_HEIGHT')  # 抓斗洒料的安全高度
# 行车作业半径
radius = config.getint('L3', 'RADIUS')  # 抓斗影响半径范围

# 上料提升高度
feed_rise_height = config.getint('L3', 'FEED_RISE_HEIGHT')

# 3D数据库配置
host = config.get('3D-DATABASE', 'address')
user = config.get('3D-DATABASE', 'user')
password = config.get('3D-DATABASE', 'password')
port = config.getint('3D-DATABASE', 'port')
database = config.get('3D-DATABASE', 'database')
table = config.get('3D-DATABASE', 'table')

# # 读取状态池配置
# pool_host = config.get('STATES', 'host')
# pool_port = config.getint('STATES', 'port')
# pool_database = config.get('STATES', 'database')

"""
------------------------------------------------------------------
                           2. 读取协议
------------------------------------------------------------------
"""

""" 与状态池的通信地址"""
status_port = 1100

# -----------上料口-----------------------

# 通信状态地址名
feed_communication_address = 30
# value映射
feed_communication_status_dict = {0: 'normal', 1: 'abnormal'}
# 每个上料口状态的地址和值，0,1,2表示上料口编号
feed_status_address_dict = {0: 31, 1: 33, 2: 35}
feed_status_dict = {0: "plug", 1: "do not feed", 2: "feed", 3: "emergency feed"}
# 每个上料口当前上何种料的地址和状态
feed_type_address_dict = {0: 32, 1: 34, 2: 36}
feed_type_value_dict = {0: "gaolu", 1: "zhongxing", 2: "liangang"}

# ----------------------除尘灰仓-------------------------------
dust_warehouse_address_dict = {0: 37}
dust_warehouse_status_dict = {0: "disallow", 1: "allow"}

# -------------------卸料口------------------------------------
# 通信状态地址名
upload_communication_address = 0
# value映射
upload_communication_status_dict = {0: 'normal', 1: 'abnormal'}
# 卸料口的地址和状态码,0,1,2,3表示卸料口编号
uploading_port_address_dict = {0: 1, 1: 2, 2: 3, 3: 4}
uploading_port_status_dict = {0: "come", 1: "upload", 2: "leave", 3: "no car"}

# ------------------3D状态---------------------------------
tri_d_status_address = 0
tri_d_status_dict = {0: 'normal', 1: 'abnormal'}

""" 与L2的通信地址"""
l2_port = 2200
# 进车允许地址
car_is_allow_address = 0
# 扫描允许地址
scan_is_allow_address = 1
# 心跳地址
heartbeat_address = 2
# 当前模式地址
mode_address = 3
# 控制命令
control_command_address = 3
# 允许状态
allow_code_dict = {'disallow': 0, 'allow': 1}
# 模式对应r
mode_dict = {0: 'auto', 1: 'semi-auto', 2: 'manually', 3: 'remote'}
# 控制命令对应
control_command_dict = {0: 'run', 1: 'stop', 2: 'pause', 3: 'scram', 4: 'reset'}

"""
------------------------------------------------------------------
                           3. 常量定义
------------------------------------------------------------------
"""

empty = 1
not_empty = 0
active = 1
hang = 0
standby = 2
