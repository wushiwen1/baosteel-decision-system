import socket
import struct
from configparser import ConfigParser

import snap7

from lib.logger.log import Logger

# 日志对象
logger = Logger(file_name='StatesClient')
# 导入配置文件
config = ConfigParser()
config.read("../config.ini", encoding='UTF-8')
mis_host = config.get('STATES', 'mis_host')  # MIS-Server的ip
mis_port = config.getint('STATES', 'mis_port')  # MIS-Server的端口
s7_host = config.get('STATES', 's7_host')  # s7-1500的ip
h3u_host = config.get('STATES', 'h3u_host')  # h3u的ip
h3u_port = config.getint('STATES', 'h3u_port')  # h3u的端口号

# 程序修改参数
s7_slot_number = 0  # s7-1500的槽号
s7_rack_number = 0  # s7-1500的机架号
s7_data_type = 132  # s7-1500的数据类型：DB块、M区、I区、Q区
s7_db_number = 1  # s7-1500的DB块号
s7_db_start = 0  # s7-1500的起始地址
s7_db_size = 44  # s7-1500的DB块数据量,单位：字节


class GetStates:
    def __init__(self):
        """
        self.mis_variable,self.s7_variable,self.h3u_variable:建立三个字典存放三种通讯数据
        """
        self.mis_variable = {}
        self.s7_variable = {}
        self.h3u_variable = {}
        self.socktclient_mis = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 初始化
        self.socktclient_h3u = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 初始化
        self.socktclient_mis.connect((mis_host, mis_port))  # 建立连接
        self.s7_heartbeat = 0
        self.h3u_heartbeat = 0
        print(11)
    def s7_connect(self):  # 建立与s7-1500的s7通讯
        self.snap7client = snap7.client.Client()  # 初始化
        self.snap7client.connect(s7_host, s7_slot_number, s7_rack_number)  # IP地址，第二个数字机架，第三个数字是cpu的槽号，请去plc控制柜查看;

    def h3u_connect(self):  # 建立与h3u的TCP/IP通讯
        self.socktclient_h3u.connect((h3u_host, h3u_port))  # 建立连接
        self.socktclient_h3u.settimeout(5)  # 通讯连接超时间

    def mis_connect(self):  # 建立与mis-server的TCP/IP通讯
        self.socktclient_mis.settimeout(5)  # 通讯连接超时间

    def s7_read(self):  # 与s7-1500的数据读写
        """心跳检测"""
       # self.s7_heartbeat = self.s7_heartbeat + 1
        self.s7_heartbeat=255
        s7_out_pre = struct.pack('!B', self.s7_heartbeat)  # 打包成字节流
        self.snap7client.write_area(s7_data_type, s7_db_number, s7_db_start, s7_out_pre)
        s7=254
        s7_er= struct.pack('!B',  s7)
        self.snap7client.write_area(s7_data_type, s7_db_number, s7_db_start+1,  s7_er)
        '''读数据'''
        self.db_pre = self.snap7client.read_area(s7_data_type, s7_db_number, s7_db_start,
                                                 s7_db_size)  # 读取的数据，以字节流的形式读上来
        print(self.db_pre[0])
       # if self.db_pre[0] != self.s7_heartbeat:
       #     raise Exception('赛迪PLC心跳异常')
       # if self.s7_heartbeat >= 30:
       #     self.s7_heartbeat = 0

        self.s7_variable['feeding_status'] = 0  # 预留接口
        self.s7_variable['zero_feeding_allow'] = self.bool_bytes(self.db_pre[2], self.db_pre[3])  # 字节流转字
        self.s7_variable['weight_zero'] = self.real_bytes(self.db_pre[4], self.db_pre[5], self.db_pre[6],
                                                          self.db_pre[7])
        self.s7_variable['flow_zero'] = self.real_bytes(self.db_pre[8], self.db_pre[9], self.db_pre[10],
                                                        self.db_pre[11])
        self.s7_variable['type_zero'] = self.word_bytes(self.db_pre[12], self.db_pre[13])
        self.s7_variable['one_feeding_allow'] = self.bool_bytes(self.db_pre[14], self.db_pre[15])
        self.s7_variable['weight_one'] = self.real_bytes(self.db_pre[16], self.db_pre[17], self.db_pre[18],
                                                         self.db_pre[19])
        self.s7_variable['flow_one'] = self.real_bytes(self.db_pre[20], self.db_pre[21], self.db_pre[22],
                                                       self.db_pre[23])
        self.s7_variable['two_feeding_allow'] = self.bool_bytes(self.db_pre[24], self.db_pre[25])
        self.s7_variable['weight_two'] = self.real_bytes(self.db_pre[26], self.db_pre[27], self.db_pre[28],
                                                         self.db_pre[29])
        self.s7_variable['flow_two'] = self.real_bytes(self.db_pre[30], self.db_pre[31], self.db_pre[32],
                                                       self.db_pre[33])
        self.s7_variable['receive_run'] = self.bool_bytes(self.db_pre[34], self.db_pre[35])
        self.s7_variable['receive_weight'] = self.real_bytes(self.db_pre[36], self.db_pre[37], self.db_pre[38],
                                                             self.db_pre[39])
        self.s7_variable['receive_flow'] = self.real_bytes(self.db_pre[40], self.db_pre[41], self.db_pre[42],
                                                           self.db_pre[43])
        print('s7数据')
        print(list(self.db_pre))
        print(self.s7_variable['zero_feeding_allow'])
        print(self.s7_variable['weight_zero'])
        print(self.s7_variable['flow_zero'])

    # step_value = 0
    #  for i in values_type:
    #      if i == 2:
    #          self.mis_variable[step_value] ==self.word_bytes(self.db_pre[start_addres[step_value]],self.db_pre[start_addres[step_value]+1])
    #      elif  i==4:
    #         self.mis_variable[step_value]'''

    def h3u_read(self):  # 与h3u的数据读写
        h3u_tosend = b"\x12\x34"  # 发送的数据
        self.socktclient_h3u.send(h3u_tosend)
        h3u_recved = self.socktclient_h3u.recv(512)  # 读取的数据
        self.h3u_variable['uploading_status'] = 0  # 预留接口
        self.h3u_variable['one_uploading_status'] = self.word_bytes(h3u_recved[3], h3u_recved[2])  # 字节流转字
        self.h3u_variable['two_uploading_status'] = self.word_bytes(h3u_recved[5], h3u_recved[4])
        self.h3u_variable['three_uploading_status'] = self.word_bytes(h3u_recved[7], h3u_recved[6])
        self.h3u_variable['four_uploading_status'] = self.word_bytes(h3u_recved[9], h3u_recved[8])
        self.h3u_variable['zero_raster'] = self.word_bytes(h3u_recved[11], h3u_recved[10])
        self.h3u_variable['one_raster'] = self.word_bytes(h3u_recved[13], h3u_recved[12])
        self.h3u_variable['two_raster'] = self.word_bytes(h3u_recved[15], h3u_recved[14])
        print('h3u数据')
        print(list(h3u_recved))
        print(self.h3u_variable['one_uploading_status'])
        print(self.h3u_variable['two_uploading_status'])
        print(self.h3u_variable['three_uploading_status'])
        print(self.h3u_variable['four_uploading_status'])

    def mis_read(self):  # 与mis-server的数据读写
        mis_tosend = b"\x12\x34\x45\x65\x67\x76\x77\x56\x34\x32"
        self.socktclient_mis.send(mis_tosend)
        mis_recved = self.socktclient_mis.recv(512)  # 接收到的数据
        self.mis_variable['communication_status'] = 0  # 预留接口
        self.mis_variable['one_working_status'] = self.word_bytes(mis_recved[2], mis_recved[3])  # 字节流转字
        self.mis_variable['two_working_status'] = self.word_bytes(mis_recved[4], mis_recved[5])
        self.mis_variable['one_contaminate_status'] = self.word_bytes(mis_recved[6], mis_recved[7])
        self.mis_variable['two_contaminate_status'] = self.word_bytes(mis_recved[8], mis_recved[9])
        print('mis数据')
        print(list(mis_recved))
        print(self.mis_variable['one_working_status'])
        print(self.mis_variable['two_working_status'])

    def bool_bytes(self, bool_0, bool_1):  # 字节流转bool
        value_bool = bool_0
        return value_bool

    def word_bytes(self, word_0, word_1):  # 字节流转字
        value_word = word_1 + word_0 * 256
        return value_word

    def real_bytes(self, real_0, real_1, real_2, real_3):  # 字节流转real
        list_bytes = [real_3, real_2, real_1, real_0]
        value_real = struct.unpack('<f', struct.pack('4B', *list_bytes))[0]
        return value_real

    def run_connect(self):  # 封装通讯连接
        """ s7_con_threa = threading.Thread(target=self.s7_connect)
           h3u__con_threa = threading.Thread(target=self.h3u_connect)
           mis_con_threa = threading.Thread(target=self.mis_connect)
           s7_con_threa.start()
           h3u__con_threa.start()
           mis_con_threa.start()
           s7_con_threa.join()
           h3u__con_threa.join()
           mis_con_threa.join()"""
        self.s7_connect()
        self.mis_connect()
        self.h3u_connect()

    def run_read(self):  # 封装数据读写
        """s7_re_threa = threading.Thread(target=self.s7_read)
            h3u__re_threa = threading.Thread(target=self.h3u_read)
            mis_re_threa = threading.Thread(target=self.mis_read)
            s7_re_threa.start()
            h3u__re_threa.start()
            mis_re_threa.start()
            s7_re_threa.join()
            h3u__re_threa.join()
            mis_re_threa.join()"""
        self.s7_read()
        self.h3u_read()
        self.mis_read()

    def communication_close(self):  # 封装通讯断开
        self.socktclient_mis.close()
        self.snap7client.disconnect()
        self.socktclient_h3u.close()
