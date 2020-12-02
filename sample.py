#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   sample.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/10/30 16:58   WANG HAN      1.0         None
"""

# import lib
# 导入日志，加上模块名
from configparser import ConfigParser

from lib.logger.log import Logger

logger = Logger(file_name='l3')

# 导入配置文件

config = ConfigParser()
config.read("../config.ini")
scanner_model = config.get('SCANNER', 'scanner_model')  # 扫描仪型号
scanner_host = config.get('SCANNER', 'scanner_host')
scanner_port = config.getint('SCANNER', 'scanner_port')
scanner_height = config.getint('SCANNER', 'scanner_height')
scanner_numbers = config.getint('SCANNER', 'scanner_numbers')  # 扫描仪个数
