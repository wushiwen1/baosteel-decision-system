#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   event_manager.py    
@Contact :   wanghan@inovance.com
@License :   (C)Copyright 2020-2021, inovance

@Modify Time      @Author    @Version    @Description
------------      -------    --------    -----------
2020/11/24 15:35   WANG HAN      1.0      事件管理器
"""

# import lib
import time
from queue import Queue, Empty
from threading import *

# 获取事件的阻塞时间设为1秒
EVENT_TIME_OUT = 1


class EventManager:
    def __init__(self):
        """初始化事件管理器"""
        # 事件对象列表
        self.__eventQueue = Queue()
        # 事件管理器开关
        self.__active = False
        # 事件处理线程
        self.__thread = Thread(target=self.__run)
        # 这里的__handlers是一个字典，用来保存对应的事件类型的响应函数
        # 其中每个键对应的值是一个列表，列表中保存了对该事件监听的响应函数，一对多
        self.__handlers = {}

    def __run(self):
        """引擎运行"""

        while self.__active:
            """
            # +++++++++++++++++++++++ 加心跳 +++++++++++++++++++
            """
            try:
                # EVENT_TIME_OUT获取事件的阻塞时间
                event = self.__eventQueue.get(block=True, timeout=EVENT_TIME_OUT)
                # 事件处理
                self.__eventProcess(event)
            except Empty:
                pass

    def __eventProcess(self, event):
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if event.type_ in self.__handlers:
            # 若存在，则按顺序将事件传递给处理函数执行
            for handler in self.__handlers[event.type_]:
                handler(event)

    def start(self):
        """启动"""
        # 将事件管理器设为启动
        self.__active = True
        # 启动事件处理线程
        self.__thread.start()

    def stop(self):
        """停止"""
        # 将事件管理器设为停止
        self.__active = False
        # 等待事件处理线程退出
        self.__thread.join()

    def addEventListener(self, type_, handler):
        """绑定事件类型和事件处理函数"""
        # 尝试获取该事件类型对应的处理函数列表，若无则创建
        try:
            handlerList = self.__handlers[type_]
        except KeyError:
            handlerList = []
            self.__handlers[type_] = handlerList
        # 若要注册的处理器不在该事件的处理器列表中，则注册该事件
        if handler not in handlerList:
            handlerList.append(handler)

    def removeEventListener(self, type_, handler):
        """移除监听器的处理函数"""
        try:
            handlerList = self.__handlers[type_]
            # 如果该函数存在于列表中，则移除
            if handler in handlerList:
                handlerList.remove(handler)
            # 如果函数列表为空，则从引擎中移除该事件类型
            if not handlerList:
                del self.__handlers[type_]
        except KeyError:
            pass

    def sendEvent(self, event):
        """发送事件，向事件队列中存入事件"""
        self.__eventQueue.put(event)


class Event:
    """
    事件类，传入EventManager必须是该类的实例对象
    """

    def __init__(self, type_=None):
        self.type_ = type_  # 事件类型
        self.content = None  # 用于保存具体的事件内容


# 测试
class PublicAccounts:
    """
    事件源 公众号
    """

    def __init__(self, eventManager):
        print("实例化公众号")
        self.__eventManager = eventManager

    def WriteAndSendNewArtical(self):
        """
        事件对象：写了并推送了新文章
        """
        event = Event(type_='EVENT_ARTICLE')
        event.content = {}
        event.content["article"] = '《文章名：第一百零八回》'

        # 发送事件
        print(u'公众号推送新文章\n')
        self.__eventManager.sendEvent(event)


class Listener:
    """
    监听器 订阅者
    """

    def __init__(self, username):
        self.__username = username

    # 监听器的处理函数 读文章
    def ReadArtical(self, event):
        print(u'%s 收到新文章' % self.__username)
        time.sleep(10)
        print(u'正在阅读新文章内容：%s' % event.content["article"])


def test():
    """
    测试函数
    """
    # 1.实例化『监听器』
    listener1 = Listener("小明")  # 订阅者1
    listener2 = Listener("小红")  # 订阅者2

    # 2.实例化『事件管理器』
    eventManager = EventManager()

    # 3.绑定『事件』和『监听器响应函数』
    eventManager.addEventListener('EVENT_ARTICLE', listener1.ReadArtical)
    eventManager.addEventListener('EVENT_ARTICLE', listener2.ReadArtical)

    # 4.启动『事件管理器』
    #   注意：4.1 这里会启动一个新的事件处理线程，一直监听下去,可以看__run()中while循环；
    #        4.2.同时主线程会继续执行下去
    eventManager.start()

    # 5.实例化『事件源』
    publicAcc = PublicAccounts(eventManager)

    # 6.定时启动『事件源』中的『生成事件对象以及发送事件』
    timer1 = Timer(1, publicAcc.WriteAndSendNewArtical)
    timer1.start()
    timer2 = Timer(1, publicAcc.WriteAndSendNewArtical)
    timer2.start()


if __name__ == '__main__':
    test()
