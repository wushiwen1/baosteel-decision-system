#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   modbus_client.py
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/12 19:21   WANG HAN      1.0    与l2的通讯客户端
"""

# import lib
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as mt


class ModbusClient:
    def __init__(self, port):
        self.m = mt.TcpMaster(port=port)

    def set(self, key, value):
        self.m.execute(1, cst.WRITE_SINGLE_REGISTER, key, output_value=value)

    def get(self, key):
        return self.m.execute(1, cst.READ_HOLDING_REGISTERS, key, 1)

    def mget(self, keys, *args):
        """
        读多个地址
        :param keys:
        :param args: 多个地址
        :return: 返回地址的值
        """
        args = list_or_args(keys, args)  # list类型
        result = []
        for arg in args:
            result.append(self.get(arg))
        return result

    def close(self):
        self.m.close()


def list_or_args(keys, args):
    # returns a single new list combining keys and args
    try:
        iter(keys)
        # a string or bytes instance can be iterated, but indicates
        # keys wasn't passed as a list
        if isinstance(keys, (str, bytes)):
            keys = [keys]
        else:
            keys = list(keys)
    except TypeError:
        keys = [keys]
    if args:
        keys.extend(args)
    return keys
