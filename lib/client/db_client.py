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

# import lib
import pymysql


host = "127.0.0.1"
user = "root"
password = "123456"
port = 3306
database = "baosteel_database"


class DbClient:
    def __init__(self):
        self.conn = None
        self.db_client = None

    def connect(self):
        """
        连接数据库
        """
        self.conn = pymysql.connect(host=host,
                                    user=user,
                                    password=password,
                                    database=database,
                                    port=port,
                                    charset="utf8")  # 连接mysql

    def query(self, sql, args=None):
        """
        查询数据

        :return: 查询的数据
        """
        # 执行 sql 语句
        cursor = self.conn.cursor()
        cursor.execute(sql, args)
        # 显示出所有数据
        data = cursor.fetchall()
        cursor.close()
        return data

    def execute(self, sql, args=None):
        # 执行 sql 语句，无返回，适用于 插入数据，删除数据，更新数据
        cursor = self.conn.cursor()
        cursor.execute(sql, args)
        self.conn.commit()
        cursor.close()

    def close(self):
        # 关闭数据库连接
        self.conn.close()
