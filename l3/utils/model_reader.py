#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   model_reader.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/2 13:54   WANG HAN      1.0      从数据库读取3D数据
"""

import numpy as np
# import lib
import pymysql

from l3.utils.variables import host, password, user, database, port, table


class ModelReader:
    def __init__(self):
        self.conn = None
        self.db_client = None
        self.warehouse_type = None
        self.x_range = None
        self.y_range = None

    def connect(self, warehouse_type, x_range, y_range):
        """

        :param warehouse_type:  料场类型
        :param x_range: X的范围，闭区间
        :param y_range: Y的范围，闭区间
        :return:
        """
        self.warehouse_type = warehouse_type
        self.x_range = x_range
        self.y_range = y_range
        self.conn = pymysql.connect(host=host,
                                    user=user,
                                    password=password,
                                    database=database,
                                    port=port,
                                    charset="utf8")  # 连接mysql

        self.db_client = self.conn.cursor()

    def read(self):
        """
        读取模型

        :return: data,array格式
        """
        if self.warehouse_type and self.x_range and self.y_range:
            sql = "SELECT X,Y,Z FROM " + table + " WHERE (X BETWEEN {0} AND {1}) " \
                                                 "AND (Y BETWEEN {2} AND {3}) AND type = {4}" \
                .format(self.x_range[0], self.x_range[1], self.y_range[0], self.y_range[1], self.warehouse_type)
            # 执行 sql 语句
            self.db_client.execute(sql)
            # 显示出所有数据
            data = self.db_client.fetchall()
            return np.array(data)
        else:
            raise ConnectionRefusedError("数据库未连接,请先调用connect方法")

    def update(self):
        self.read()

    def close(self):
        # 关闭数据库连接
        self.conn.close()
