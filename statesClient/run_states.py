import time

from retrying import retry

from lib.logger.log import Logger
from statesClient import get_states, states_output
from statesClient import states_calculate

# 日志对象
logger = Logger(file_name='StatesClient')


@retry(stop_max_attempt_number=5, stop_max_delay=1000)  # 发生错误，重复调用5次，与最近的方法结合
def connect():
    getstates = get_states.GetStates()
    statescalculate = states_calculate.StatesCalculate()
    statesoutput = states_output.StatesOutput()
    getstates.run_connect()
    statesoutput.run_modbus()
    return getstates, statescalculate, statesoutput  # 返回实例化类


def run():
    while 1:
        try:
            getstates, statescalculate, statesoutput = connect()
        except Exception as e:
            logger.error("%s 导致通讯连接失败" % e)
            continue
        else:
            logger.info("数据连接成功")
            logger.info("数据开始交互")
            while 1:
                try:
                    t1 = time.time()
                    time.sleep(1)
                    getstates.run_read()
                    if getstates.s7_variable == {} or getstates.h3u_variable == {} or getstates.mis_variable == {}:
                        if getstates.s7_variable == {}:
                            logger.warning('s7数据读取为空')
                        if getstates.h3u_variable == {}:
                            logger.warning('h3u数据读取为空')
                        if getstates.mis_variable == {}:
                            logger.warning('mis数据读取为空')
                        continue
                    else:
                        print(getstates.s7_variable, getstates.h3u_variable, getstates.mis_variable)
                except Exception as e:
                    logger.error("%s 异常导致主流程读写数据结束 " % e)
                    break
                else:
                    try:
                        statescalculate.run_result(getstates.s7_variable, getstates.h3u_variable)
                        print(getstates.s7_variable, getstates.h3u_variable, getstates.mis_variable,
                              statescalculate.calculate_variable)
                    except Exception as e:
                        logger.error("%s 异常导致主流程计算数据结束" % e)
                        break
                    else:
                        try:
                            statesoutput.run_data(getstates.mis_variable, getstates.s7_variable, getstates.h3u_variable,
                                                  statescalculate.calculate_variable)
                            print(11111112222222)
                        except Exception as e:
                            logger.error("%s 异常导致主流程输出状态结束" % e)
                            break
                    t2 = time.time()
                    t_total = t2 - t1
                    print('循环时间：%f' % t_total)
            getstates.communication_close()


if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        print(e)
