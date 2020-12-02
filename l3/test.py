# import numpy as np
# import datetime
#
# from dbClient.db_client import DbClient
#
#
# # def change_table_by_config():
# #     sql = "select * from dust_warehouse"
# #     data = db_client.query(sql)
# #     if data:
# #         # 当表不为空
# #         data = np.array(data)
# #         database_stack_boundary = data[:, [2, 3]].tolist()
# #         config_stack_boundary = [[4000, 7000], [7000, 10000], [10000, 13000], [13000, 16000], [16000, 19000]]
# #         date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 记录最晚时间
# #         is_empty = 0  # 全部不为空
# #         print(database_stack_boundary, config_stack_boundary)
# #         if database_stack_boundary != config_stack_boundary:
# #             print('不一样')
# #             sql = "TRUNCATE `dust_warehouse`;"
# #             db_client.execute(sql)  # 清空原有记录
# #             for boundary in config_stack_boundary:
# #                 # values = (boundary[0],boundary[0], boundary[1], boundary[1])
# #                 # record = np.array(self.db_client.query(sql, values))  # 记录数据
# #                 # record_id = record[:,0]  # 记录id
# #                 # date_time = max(record[:, 4])  # 记录最晚时间
# #                 # is_empty = min(record[:, 5])  # 标记空置
# #                 # sql = "delete from test where id = %s or id = %s"
# #                 # values = tuple(record_id)
# #                 # self.db_client.execute(sql, values)  # 删除原有记录
# #                 sql = "insert into dust_warehouse(id, dust_warehouse_id, boundary_min, boundary_max, stack_time, is_empty) values(%s, %s, %s,%s, %s,%s)"
# #                 values = (str(uuid.uuid1()), 0, boundary[0], boundary[1], date_time, is_empty)
# #                 db_client.execute(sql, values)  # 插入新纪录
#
#
# from dbClient.db_client import DbClient
#
# db_client = DbClient()
# db_client.connect()
# sql = "select * from dust_warehouse "
# # # value = (6000, 6000, 9000, 9000)
# record_data = db_client.query(sql)  # 记录数据
# print(record_data[0])
# # data = record_data[:, 0]
# # print(data)
# sql = "select * from dust_warehouse"
# record_data = np.array(db_client.query(sql))[:, 2:]  # 记录数据
# print(record_data[record_data[:, 3] == 0][0][0:2])
# # if db_client.query(sql):
# #     print(np.array(db_client.query(sql)))
# # values = (str(uuid.uuid1()), 0, 3000, 6000, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0)
# # sql = "insert into test(id, dust_warehouse_id, boundary_min, boundary_max, stack_time, is_empty) values(%s, %s, %s,%s, %s,%s)"
# # # sql = 'UPDATE test SET boundary_min=4000, boundary_max=60000 where id =2'
# # db_client.execute(sql,values)
# # change_table_by_config()
# db_client.close()
# from l3.lib.variables import feed_status_address_dict, uploading_port_status_dict
#
# print(uploading_port_status_dict)
import time

from l3.main import run_l3


def put(q):
    for i in range(1000):
        q[i] = i


def get(q):
    for i in range(1000):
        print('删除', q[i])
        q.pop(i)


if __name__ == '__main__':
    import multiprocessing as mp

    d = mp.Manager().dict()
    p1 = mp.Process(target=run_l3, args=(d,))  # 注意当参数只有一个时，应加上逗号

    # p2 = mp.Process(target=get, args=(d,))
    p1.start()
    time.sleep(0.1)
    p1.join()
    # p2.start()
    # p2.join()
    # print(d)
