#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   plc_client.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2019-2020, inovance

@Modify Time      @Author    @Version    @Desciption
------------      -------    --------    -----------
2020/8/26 17:18   WANG HAN      1.0         None
"""
import snap7


class PlcClient:
    def __init__(self, logger):
        self.plc = snap7.client.Client()
        self.logger = logger

    def connect(self, address, rack, slot):
        try:
            self.plc.connect(address, rack, slot)
        except Exception as e:
            self.logger.error(e)
            self.logger.error('连接失败')

    def queryData(self, db_number, start, size):
        try:
            data = self.plc.db_read(db_number, start, size)
            print(data)
        except Exception as e:
            self.logger.error(e)
            self.logger.error(str(self.plc), '查询数据发生错误')
        finally:
            if self.plc.get_connected():
                self.plc.disconnect()

    # 发送数据
    def sendData(self, db_number, start, data):
        """
          发送数据
        """
        try:
            data = strtoBytesArray(data)
            if not data.strip():
                self.logger.error('发送数据不能为空')
                return
            self.plc.db_write(db_number, start, data)
        except Exception as e:
            self.logger.error(e)
            self.logger.error(str(self.plc), '发送数据发生错误')
        finally:
            if self.plc.get_connected():
                self.plc.disconnect()


def strtoBytesArray(strdata):
    # 将bytes字符串转化为bytes
    strarry = strdata.split()
    list = []
    for itm in strarry:
        list.append(itm)

    return bytearray(list)
