#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   log.py    
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2019-2020, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2019/11/1 9:35   WANGHAN      1.0         日志模块
"""
import inspect
import logging
import os.path
import time


class Logger:
    def __init__(self, file_name='server'):
        """
            指定保存日志的文件路径，日志级别，以及调用文件
            将日志存入到指定的文件中
            当前
        """
        # current_time = time.strftime('%Y%m%d%H%M',
        #                            time.localtime(time.time()))  # 返回当前时间
        # current_path = os.path.dirname(os.path.abspath(project_path))  # 返回当前目录
        # path1 = current_path.split(project_path)  #指定分隔符对字符串进行切片
        # path2 = [path1[0], project_path]
        # path3 = ''
        # print(str(inspect.stack()[1][1]) + ' - ' + str(inspect.stack()[1][3]) + ' - 引用一次')
        new_name = '../logs/'  # 在该路径下新建下级目录

        dir_time = time.strftime('%Y%m%d', time.localtime(time.time()))  # 返回当前时间的年月日作为目录名称
        isExists = os.path.exists(new_name + dir_time)  # 判断该目录是否存在
        if not isExists:
            os.makedirs(new_name + dir_time)
        try:
            # 创建一个logger(初始化logger)
            self.log = logging.getLogger()
            self.log.setLevel(logging.DEBUG)

            # 创建一个handler，用于写入日志文件
            # 如果case组织结构式 /testsuit/featuremodel/xxx.py ， 那么得到的相对路径的父路径就是项目根目录
            log_name = new_name + dir_time + '/' + file_name + '.log'  # 定义日志文件的路径以及名称

            fh = logging.FileHandler(log_name)
            fh.setLevel(logging.DEBUG)

            # 再创建一个handler，用于输出到控制台
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)

            # 定义handler的输出格式
            formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)

            # 给logger添加handler
            self.log.addHandler(fh)
            self.log.addHandler(ch)
        except Exception as e:
            print("输出日志失败！ %s" % e)

    def info(self, msg):
        msg = str(inspect.stack()[1][1]) + ' - ' + str(inspect.stack()[1][3]) + ' - ' + msg
        self.log.info(msg)
        return

    def warning(self, msg):
        msg = str(inspect.stack()[1][1]) + ' - ' + str(inspect.stack()[1][3]) + ' - ' + msg
        self.log.warning(msg)
        return

    def error(self, msg):
        msg = str(inspect.stack()[1][1]) + ' - ' + str(inspect.stack()[1][3]) + ' - ' + msg
        self.log.error(msg)
        return
