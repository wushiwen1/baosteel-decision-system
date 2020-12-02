import modbus_tk.defines as cst
import modbus_tk.modbus_tcp as modbus_tcp

from lib.logger.log import Logger

# 日志对象
logger = Logger(file_name='StatesClient')
# 程序接口
local_port = 1100


class StatesOutput:
    """建立modbustcp通讯输出状态数据"""

    def __init__(self):
        self.slave1 = None
        self.modbussever = modbus_tcp.TcpServer(port=local_port)  # address=''默认表示获取本机地址
        self.heart_beat = 0

    def modbus_server(self):  # 建立tcp服务器
        self.modbussever.start()
        logger.info("建立1号站MODBUS-TCP服务器")

    def allocating_address(self):
        # 建立第一个从机
        self.slave1 = self.modbussever.add_slave(1)  # 站号
        # 卸料口地址分配
        self.slave1.add_block('A', cst.HOLDING_REGISTERS, 0, 5)  # 地址0，长度5
        self.slave1.add_block('B', cst.HOLDING_REGISTERS, 5, 3)  # 地址5，长度3
        # 上料口地址分配
        self.slave1.add_block('C', cst.HOLDING_REGISTERS, 30, 5)  # 地址30，长度5
        self.slave1.add_block('D', cst.HOLDING_REGISTERS, 35, 6)  # 地址35，长度6
        self.slave1.add_block('E', cst.HOLDING_REGISTERS, 41, 8)  # 地址40，长度5
        self.slave1.add_block('F', cst.HOLDING_REGISTERS, 49, 9)  # 地址45，长度5
        # 3D地址分配
        self.slave1.add_block('G', cst.HOLDING_REGISTERS, 80, 5)  # 地址30，长度5
        # 心跳地址分配
        self.slave1.add_block('H', cst.HOLDING_REGISTERS, 100, 2)  # 地址30，长度5
        logger.info("1号站分配MODBUS-TCP地址")

    def run_data(self, mis_variables, s7_variables, h3u_variables, calculate_variables):
        self.mis_variables = mis_variables
        self.s7_variables = s7_variables
        self.h3u_variables = h3u_variables
        self.calculate_variables = calculate_variables
        # 接收心跳数据存放
        # self.slave=self.modbussever.get_slave(1)
        # self.values=self.slave.get_values('H',100,2)
        # 数据设置
        self.slave1.set_values('A', 0,
                               [self.h3u_variables['uploading_status'], self.h3u_variables['one_uploading_status'],
                                self.h3u_variables['two_uploading_status'],
                                self.h3u_variables['three_uploading_status'],
                                self.h3u_variables['four_uploading_status']])
        self.slave1.set_values('C', 30,
                               [self.s7_variables['feeding_status'], self.calculate_variables['zero_feeding_request'],
                                self.calculate_variables['zero_feed_type'],
                                self.calculate_variables['one_feeding_request'],
                                self.calculate_variables['one_feed_type']])
        self.slave1.set_values('D', 35, [self.calculate_variables['two_feeding_request'],
                                         self.calculate_variables['two_feed_type'],
                                         self.calculate_variables['warehouse_run_stop'],
                                         self.s7_variables['zero_feeding_allow'],
                                         0, int(self.s7_variables['weight_zero'])])
        self.slave1.set_values('E', 41, [0, int(self.s7_variables['flow_zero']), self.s7_variables['one_feeding_allow'],
                                         0, int(self.s7_variables['weight_one']), 0, int(self.s7_variables['flow_one']),
                                         self.s7_variables['two_feeding_allow']])
        self.slave1.set_values('F', 49, [0, int(self.s7_variables['weight_two']), 0, int(self.s7_variables['flow_two']),
                                         self.s7_variables['receive_run'], 0, int(self.s7_variables['receive_weight']),
                                         0, int(self.s7_variables['receive_flow'])])
        self.slave1.set_values('G', 80,
                               [self.mis_variables['communication_status'], self.mis_variables['one_working_status'],
                                self.mis_variables['two_working_status'], self.mis_variables['one_contaminate_status'],
                                self.mis_variables['two_contaminate_status']])
        # 心跳加1检测
        self.heart_beat = self.heart_beat + 1
        self.slave1.set_values('H', 100, self.heart_beat)
        if self.heart_beat >= 255:
            self.heart_beat = 0

    def run_modbus(self):  # 封装
        self.modbus_server()
        self.allocating_address()
