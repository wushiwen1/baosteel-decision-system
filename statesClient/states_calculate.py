import time
from configparser import ConfigParser

from lib.logger.log import Logger

# 日志对象
logger = Logger(file_name='StatesClient')
# 导入配置文件
config = ConfigParser()
config.read("../config.ini", encoding='UTF-8')
zero_full_load = config.getint('STATES', 'zero_full_load')  # o号上料口的满载重量
one_full_load = config.getint('STATES', 'one_full_load')  # 1号上料口的满载重量
two_full_load = config.getint('STATES', 'two_full_load')  # 2号上料口的满载重量


class StatesCalculate:
    """中间计算步骤类"""

    def __init__(self):
        self.calculate_variable = {}
        self.temp = 0  # 临时变量
        self.rising_edge = 0  # 上升沿
        self.falling_edge = 0  # 下降沿
        self.t_rising = 0  # 上升沿当前时间
        self.t_falling = 0  # 下降沿当前时间
        self.calculate_variable['warehouse_run_stop'] = 0  # 初始化

    def run_result(self, s7_variables, h3u_variables):  # 计算过程
        self.zero_feeding_allow = s7_variables['zero_feeding_allow']
        self.weight_zero = s7_variables['weight_zero']
        self.flow_zero = s7_variables['flow_zero']
        self.zero_feed_type = s7_variables['type_zero']
        self.one_feeding_allow = s7_variables['one_feeding_allow']
        self.weight_one = s7_variables['weight_one']
        self.flow_one = s7_variables['flow_one']
        self.two_feeding_allow = s7_variables['two_feeding_allow']
        self.weight_two = s7_variables['weight_two']
        self.flow_two = s7_variables['flow_two']
        self.warehouse_run_stop = s7_variables['receive_run']
        self.zero_raster = h3u_variables['zero_raster']
        self.one_raster = h3u_variables['one_raster']
        self.two_raster = h3u_variables['two_raster']

        # 0号计算是否堵料预留
        if self.zero_feeding_allow == 1:  # 外部信号判断是否允许上料
            self.calculate_variable['zero_feeding_request'] = 1
            self.calculate_variable['zero_feed_type'] = 0  # 无论外部是否允许上料，必须创建字典，否则key：zero_feed_type不存在
        else:
            if self.zero_feed_type == 0:  # 做到配置项里面，堵料找赛迪合计
                self.calculate_variable['zero_feed_type'] = 0
            elif self.zero_feed_type == 1:
                self.calculate_variable['zero_feed_type'] = 1
            else:
                self.calculate_variable['zero_feed_type'] = 2
            if self.zero_raster == 0:  # 光栅判断
                if self.weight_zero >= (1 / 2 * zero_full_load):  # 实际重量>1/2漏斗总重量
                    self.calculate_variable['zero_feeding_request'] = 1
                elif (1 / 2 * zero_full_load) > self.weight_zero >= (
                        1 / 3 * zero_full_load):  # 1/2漏斗总重量>实际重量>1/3漏斗总重量
                    self.calculate_variable['zero_feeding_request'] = 2
                else:
                    self.calculate_variable['zero_feeding_request'] = 3  # 实际重量<1/3漏斗总重量
            else:
                self.calculate_variable['zero_feeding_request'] = 0  # 堵料
                logger.warning("0号上料口堵料")

        # 1号计算是否堵料预留
        if self.one_feeding_allow == 1:  # 外部信号判断是否允许上料
            self.calculate_variable['one_feeding_request'] = 1
            self.calculate_variable['one_feed_type'] = 1
        else:
            self.calculate_variable['one_feed_type'] = 1
            if self.one_raster == 0:  # 光栅判断
                if self.weight_one >= (1 / 2 * one_full_load):  # 实际重量>1/2漏斗总重量
                    self.calculate_variable['one_feeding_request'] = 1
                elif (1 / 2 * one_full_load) > self.weight_one >= (
                        1 / 3 * one_full_load):  # 1/2漏斗总重量>实际重量>1/3漏斗总重量
                    self.calculate_variable['one_feeding_request'] = 2
                else:
                    self.calculate_variable['one_feeding_request'] = 3  # 实际重量<1/3漏斗总重量
            else:
                self.calculate_variable['one_feeding_request'] = 0  # 堵料
                logger.warning("1号上料口堵料")
        # 2号计算是否堵料预留
        if self.two_feeding_allow == 1:  # 外部信号判断是否允许上料
            self.calculate_variable['two_feeding_request'] = 1
            self.calculate_variable['two_feed_type'] = 2
        else:
            self.calculate_variable['two_feed_type'] = 2
            if self.two_raster == 0:  # 光栅判断
                if self.weight_two >= (1 / 2 * two_full_load):  # 实际重量>1/2漏斗总重量
                    self.calculate_variable['two_feeding_request'] = 1
                elif (1 / 2 * two_full_load) > self.weight_two >= (
                        1 / 3 * two_full_load):  # 1/2漏斗总重量>实际重量>1/3漏斗总重量
                    self.calculate_variable['two_feeding_request'] = 2
                else:
                    self.calculate_variable['two_feeding_request'] = 3  # 实际重量<1/3漏斗总重量
            else:
                self.calculate_variable['two_feeding_request'] = 0  # 堵料
                logger.warning("2号上料口堵料")
        # 灰仓定时
        '''上升沿判断'''
        if self.temp == 0:
            self.rising_edge = 0
            self.temp = self.warehouse_run_stop
            if self.temp == 1:
                self.rising_edge = 1
                self.t_rising = time.time()
        '''下降沿判断'''
        if self.temp == 1:
            self.falling_edge = 0
            self.temp = self.warehouse_run_stop
            if self.temp == 0:
                self.falling_edge = 1
                self.t_falling = time.time()
        if self.rising_edge == 1:
            t_new_rising = time.time()
            t_temp_rising = t_new_rising - self.t_rising
            if t_temp_rising > 30:
                self.calculate_variable['warehouse_run_stop'] = 1
            else:
                self.calculate_variable['warehouse_run_stop'] = 0
        if self.falling_edge == 1:
            t_new_falling = time.time()
            t_temp_falling = t_new_falling - self.t_falling
            if t_temp_falling <= 30:
                self.calculate_variable['warehouse_run_stop'] = 1
            else:
                self.calculate_variable['warehouse_run_stop'] = 0
