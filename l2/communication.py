import json
import socket
import struct
from configparser import ConfigParser
import time
import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp
import snap7
from lib.logger.log import Logger

# 日志对象
logger = Logger(file_name='communication')

# 导入配置文件
config = ConfigParser()
config.read("../config.ini", encoding='UTF-8')
mis_host = config.get('STATES', 'mis_host')  # MIS-Server的ip
mis_port = config.getint('STATES', 'mis_port')  # MIS-Server的端口
one_car_host = config.get('L2', 'one_car_host')  # 1号行车的ip
two_car_host = config.get('L2', 'two_car_host')  # 1号行车的ip
h3u_host = config.get('STATES', 'h3u_host')  # h3u的ip
h3u_port = config.getint('STATES', 'h3u_port')  # h3u的端口号

# 程序接口
local_port = 1101  # 本程序端口号
default = 65535  # 默认数值
one_s7_slot_number = 0  # s7-1500的槽号
one_s7_rack_number = 0  # s7-1500的机架号
one_s7_data_type = 132  # s7-1500的数据类型：DB块、M区、I区、Q区
one_s7_db_number = 1  # s7-1500的DB块号
one_s7_db_start = 0  # s7-1500的起始地址
one_s7_db_size = 44  # s7-1500的DB块数据量,单位：字节
two_s7_slot_number = 0  # s7-1500的槽号
two_s7_rack_number = 0  # s7-1500的机架号
two_s7_data_type = 132  # s7-1500的数据类型：DB块、M区、I区、Q区
two_s7_db_number = 1  # s7-1500的DB块号
two_s7_db_start = 0  # s7-1500的起始地址
two_s7_db_size = 44  # s7-1500的DB块数据量,单位：字节


class Communication:
    def __init__(self):
        """
        创建字典存放通讯数据
        """
        self.l3_dict = {}
        self.wincc_dict = {}
        self.car_dict = {}
        self.h3u_dict = {}
        self.mis_dict = {}
        self.modbussever = modbus_tcp.TcpServer(port=local_port)  # 初始化mosbus
        self.master = modbus_tcp.TcpMaster(host=h3u_host, port=h3u_port)
        self.sockt_mis = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 初始化
        self.snap7client_one = snap7.client.Client()  # 1号行车初始化
        self.snap7client_two = snap7.client.Client()  # 2#行车初始化
        self.one_real_sign=0
        self.one_turn_sign = 0
        self.one_stop_sign = 0
        self.l2_heart_beat = 0
        print(111)

    def modbus_server(self):  # 建立modbus服务
        self.modbussever.start()
        # logger.info("建立2号站MODBUS-TCP服务器")

    def allocating_address(self):
        # 建立第一个从机
        self.slave = self.modbussever.add_slave(2)  # 站号
        # 建立modbus地址块
        self.slave.add_block('0', cst.HOLDING_REGISTERS, 0, 200)  # 地址0，长度200
        logger.info("2号站分配MODBUS-TCP地址")
        list = [default] * 200  # 初始化数值
        self.slave.set_values('0', 0, list)

    def run_value(self, mysql_statistics, sna7_feedback):  # 需要mysql、snap7返回数据过来
        self.slave_1 = self.modbussever.get_slave(2)
        # wincc给进来数据
        wincc_values = self.slave_1.get_values('0', 0, 11)
        self.wincc_dict['run_stype'] = wincc_values[0]
        self.wincc_dict['work_stype'] = wincc_values[1]
        self.wincc_dict['statistics_stype'] = wincc_values[2]
        self.wincc_dict['wincc_work_id'] = wincc_values[3]
        self.wincc_dict['wincc_work_feeding_x'] = wincc_values[4]
        self.wincc_dict['wincc_work_feeding_y'] = wincc_values[5]
        self.wincc_dict['wincc_work_feeding_h'] = wincc_values[6]
        self.wincc_dict['wincc_work_emptying_x'] = wincc_values[7]
        self.wincc_dict['wincc_work_emptying_y'] = wincc_values[8]
        self.wincc_dict['wincc_work_emptying_h'] = wincc_values[9]
        # 输出给wincc数据,来源mysql
        self.wincc_dict['dust_warehouse'] = mysql_statistics['dust_warehouse']
        self.wincc_dict['neutral_uploading'] = mysql_statistics['neutral_uploading']
        self.wincc_dict['blast_furnace_uploading'] = mysql_statistics['blast_furnace_uploading']
        self.wincc_dict['steelmaking_uploading'] = mysql_statistics['steelmaking_uploading']
        self.wincc_dict['neutral_feeding'] = mysql_statistics['neutral_feeding']
        self.wincc_dict['blast_furnace_feeding'] = mysql_statistics['blast_furnace_feeding']
        self.wincc_dict['steelmaking_feeding'] = mysql_statistics['steelmaking_feeding']
        self.slave.set_values('0', 10,
                              [self.wincc_dict['neutral_uploading'], 0, self.wincc_dict['blast_furnace_uploading'], 0,
                               self.wincc_dict['steelmaking_uploading'], 0])
        self.slave.set_values('0', 16,
                              [self.wincc_dict['neutral_feeding'], 0, self.wincc_dict['blast_furnace_feeding'], 0,
                               self.wincc_dict['steelmaking_feeding'], 0,  self.wincc_dict['dust_warehouse'] ,0])
        # l3给进来的数据
        l3_values = self.slave_1.get_values('0', 50, 12)
        self.l3_dict['one_car_allow'] = l3_values[0]
        self.l3_dict['two_car_allow'] = l3_values[1]
        self.l3_dict['three_car_allow'] = l3_values[2]
        self.l3_dict['four_car_allow'] = l3_values[3]
        self.l3_dict['scan_allow'] = l3_values[4]
        self.l3_dict['l3_work_id'] = l3_values[5]
        self.l3_dict['l3_work_feeding_x'] = l3_values[6]
        self.l3_dict['l3_work_feeding_y'] = l3_values[7]
        self.l3_dict['l3_work_feeding_h'] = l3_values[8]
        self.l3_dict['l3_work_emptying_x'] = l3_values[9]
        self.l3_dict['l3_work_emptying_y'] = l3_values[10]
        self.l3_dict['l3_work_emptying_h'] = l3_values[11]
        # 给到l3和wincc的数据:完成任务id和状态字，来源行车
        self.car_dict['one_result_id'] = sna7_feedback['one_result_id']
        self.car_dict['one_host_word'] = sna7_feedback['one_host_word']
        self.car_dict['two_result_id'] = sna7_feedback['two_result_id']
        self.car_dict['two_host_word'] = sna7_feedback['two_host_word']
        self.slave.set_values('0', 90,
                              [self.car_dict['one_result_id'], self.car_dict['one_host_word']])
        self.slave.set_values('0', 110,
                              [self.car_dict['two_result_id'], self.car_dict['two_host_word']])
        # 心跳,循环加1
        self.l2_heart_beat = self.l2_heart_beat + 1
        self.slave.set_values('0', 150, self.l2_heart_beat)
        if self.l2_heart_beat >= 255:
            self.l2_heart_beat = 0
            # 总故障标志位，预留


    def snap7_connect1(self):  # 与1#1500建立通讯连接
        self.snap7client_one.connect(one_car_host, one_s7_slot_number,
                                     one_s7_rack_number)  # IP地址，第二个数字机架，第三个数字是cpu的槽号，请去plc控制柜查看;


    def snap7_connect2(self):  # 与2#1500建立通讯连接
        self.snap7client_two.connect(two_car_host, two_s7_slot_number,
                                     two_s7_rack_number)  # IP地址，第二个数字机架，第三个数字是cpu的槽号，请去plc控制柜查看;


    def snap7_rw1(self, one_translate_work):  # 与1500读写数据
        word = []  #存放字典的values
        byte = []  #存放拆分出的字节
        m=0     #地址初始化
        sna7_feedback={}  #行车返回值
        for word_value in one_translate_work.values():  # 字典按顺序解析出value的值
            word.append(word_value)
        for byte_value in word:
            byte.append(struct.pack('!B', self.word_to_byte(byte_value)[0]))  # 打包成字节流
            byte.append(struct.pack('!B', self.word_to_byte(byte_value)[1]))  # 打包成字节流
        for out_one in byte[:(len(byte))]: #1号行车发送字节流
            self.snap7client_one.write_area(one_s7_data_type, one_s7_db_number, one_s7_db_start+m,out_one)
            m+=1
        db_pre_one = self.snap7client_one.read_area(one_s7_data_type, one_s7_db_number, one_s7_db_start,
                                                   one_s7_db_size)  # 读取的数据，以字节流的形式读上来
        sna7_feedback['one_result_id']=self.word_bytes(db_pre_one[0],db_pre_one[1])
        sna7_feedback['one_host_word'] = self.word_bytes(db_pre_one[2], db_pre_one[3])
        return  sna7_feedback

    def snap7_rw2(self, two_translate_work):  # 与1500读写数据
        word = []  #存放字典的values
        byte = []  #存放拆分出的字节
        m=0      #地址初始化
        sna7_feedback={}  #行车返回值
        for word_value in two_translate_work.values():  # 字典按顺序解析出value的值
            word.append(word_value)
        for byte_value in word:
            byte.append(struct.pack('!B', self.word_to_byte(byte_value)[0]))  # 打包成字节流
            byte.append(struct.pack('!B', self.word_to_byte(byte_value)[1]))  # 打包成字节流
        for out_one in byte[:(len(byte))]: #1号行车发送字节流
            self.snap7client_two.write_area(one_s7_data_type, one_s7_db_number, one_s7_db_start+m,out_one)
            m+=1
        db_pre_two = self.snap7client_two.read_area(two_s7_data_type, two_s7_db_number, two_s7_db_start,
                                                    two_s7_db_size)  # 读取的数据，以字节流的形式读上来
        sna7_feedback['two_result_id'] = self.word_bytes(db_pre_two[40], db_pre_two[41])
        sna7_feedback['two_host_word'] = self.word_bytes(db_pre_two[42], db_pre_two[43])
        return  sna7_feedback

    def h3u_modbus(self,raster_gate_control):
        back_do={}
        if raster_gate_control['one_control_raster']==1:   #1号光栅控制
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 400, output_value=1)
        else:
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 400, output_value=0)
        if raster_gate_control['two_control_raster']==1:   #2号光栅控制
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 401, output_value=1)
        else:
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 401, output_value=0)
        if raster_gate_control['three_control_raster'] == 1:  # 3号光栅控制
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 402, output_value=1)
        else:
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 402, output_value=0)
        if raster_gate_control['one_control_gate'] == 1:  # 1号闸门控制
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 403, output_value=1)
        else:
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 403, output_value=0)
        if raster_gate_control['two_control_gate'] == 1:  # 2号闸门控制
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 404, output_value=1)
        else:
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 404, output_value=0)
        if raster_gate_control['three_control_gate'] == 1:  # 3号闸门控制
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 405, output_value=1)
        else:
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 405, output_value=0)
        if raster_gate_control['four_control_gate'] == 1:  # 4号闸门控制
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 406, output_value=1)
        else:
            self.master.execute(3, cst.WRITE_SINGLE_REGISTER, 406, output_value=0)
        do = self.master.execute(3, cst.READ_HOLDING_REGISTERS, 407, 7)
        back_do['one_raster_do']=do[0]
        back_do['two_raster_do'] = do[1]
        back_do['three_raster_do'] = do[2]
        back_do['one_gate_do'] = do[3]
        back_do['two_gate_do'] = do[4]
        back_do['three_gate_do'] = do[5]
        back_do['four_gate_do'] = do[6]
        return  back_do

    def mis_wr(self,mis_control):
        j_dict ={}
        if mis_control['one_3d_run']==1 and  self.one_real_sign==0:   #开启实时扫描
            while 1:
                self.sockt_mis.connect((mis_host, mis_port))  # 建立连接
                logger.info("1#3d建立通讯连接成功")
                one_dict = {
                    "task_id": 1,  # 任务序号
                    "type_id": 1002,  # 任务类型，触发转动构图
                    "priority": 1,  # 任务优先级
                    "source_id": 1,  # 任务源ID
                    "crane_id": 1,  # 起重机标识号
                    "return_code": 0  # 无意义
                }
                self.sockt_mis.send(json.dumps(one_dict).encode())
                logger.info("1#3d发送实时扫描运行数据成功")
                recmsg = self.sockt_mis.recv(512)
                j_dict = json.loads(recmsg)  # json转字典
                print(j_dict)
                if  j_dict[ "type_id"]==1002 and j_dict[ "task_id"]==1:
                    self.sockt_mis.close()
                    logger.info("1#3d通讯短连接完成")
                    self.one_turn_sign = 0
                    self.one_real_sign = 1
                    self.one_stop_sign = 0
                    print(1)
                    return j_dict["return_code"]
        elif mis_control['one_3d_run']==2 and  self.one_turn_sign==0:   #开启转动扫描
            while 1:
                self.sockt_mis.connect((mis_host, mis_port))  # 建立连接
                logger.info("1#3d建立通讯连接成功")
                one_dict = {
                    "task_id": 1,  # 任务序号
                    "type_id": 1001,  # 任务类型，触发转动构图
                    "priority": 1,  # 任务优先级
                    "source_id": 1,  # 任务源ID
                    "crane_id": 1,  # 起重机标识号
                    "return_code": 0  # 无意义
                }
                self.sockt_mis.send(json.dumps(one_dict).encode())
                logger.info("1#3d发送转动扫描运行数据成功")
                recmsg = self.sockt_mis.recv(512)
                j_dict = json.loads(recmsg)  # json转字典

                if j_dict["type_id"] == 1001 and j_dict["task_id"] == 1:
                    self.sockt_mis.close()
                    logger.info("1#3d通讯短连接完成")
                    self.one_turn_sign = 1
                    self.one_real_sign = 0
                    self.one_stop_sign = 0
                    return j_dict["return_code"]
        elif mis_control['one_3d_run']==3 and  self.one_stop_sign==0:   #停止实时扫描
            while 1:
                self.sockt_mis.connect((mis_host, mis_port))  # 建立连接
                logger.info("1#3d建立通讯连接成功")
                one_dict = {
                    "task_id": 1,  # 任务序号
                    "type_id": 1003,  # 任务类型，触发转动构图
                    "priority": 1,  # 任务优先级
                    "source_id": 1,  # 任务源ID
                    "crane_id": 1,  # 起重机标识号
                    "return_code": 0  # 无意义
                }
                self.sockt_mis.send(json.dumps(one_dict).encode())
                logger.info("1#3d发送停止扫描数据成功")
                recmsg = self.sockt_mis.recv(512)
                j_dict = json.loads(recmsg)  # json转字典
                if j_dict["type_id"] == 1003 and j_dict["task_id"] == 1:
                    self.sockt_mis.close()
                    logger.info("1#3d通讯短连接完成")
                    self.one_turn_sign = 0
                    self.one_real_sign=0
                    self.one_stop_sign =1
                    return j_dict["return_code"]
        else:
            j_dict["return_code"]=0
            return  j_dict["return_code"]



    def word_to_byte(self, word):   #字转字节
        byte = []
        byte.append(int(word / 256))  # python3运算符/结果为小数
        byte.append(word % 256)
        return byte

    def word_bytes(self, word_0, word_1):  # 字节流转字
        value_word = word_1 + word_0 * 256
        return value_word

    def ds(self):
        self.snap7client_one.disconnect()

if __name__ == '__main__':
    rt = Communication()
    mis_control={}
    rt.snap7_connect1()
    rt.snap7_connect2()
    # while 1:
    ft = {'er': 257, 'rt':45,'sd':45,'cv':67,'iu':90,'rr': 3,'sw':2,'qw':45,'uy':89,'vy':31,'aq':15,'as':19,'mn':23,'zo':13}
    #     rt.snap7_rw(ft)
    # rt.mis_connect()
    #mis_control['one_3d_run'] = 4
    while 1:
        #c=rt.mis_wr(mis_control)
        rt.snap7_rw1(ft)

