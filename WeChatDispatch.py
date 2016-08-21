#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 n3xtchen <echenwen@gmail.com>
#
# Distributed under terms of the GPL-2.0 license.

"""
WechatQueue
    可用对象
    self.queue 线程安全队列
    self.bot 微信客户端

    # 需要实现的方法
    def handleMsg(self, retcode, selector, msg):
        处理信息接口
        pass

    def sendMsg(self, content):
        发送信息接口
        pass
"""

import time
import sys
import os
import platform
import random
import multiprocessing
import threading
import logging
from collections import defaultdict

from libs.util import _print_qr
from WeChatBase import WebWeChat

class WeChatDispatch(object):
    """ 队列分发 """

    status = 0  # 运行状态

    time_out = 20  # 同步最短时间间隔（单位：秒）
    beat_time_out = (60, 600)

    stop_beat_event = None
    listen_process = None
    beat_thread = None

    def __init__(self, name, queue):
        """
        name: 队列名称
        queue: 线程安全的队列，用于通讯调度
        """
        self.name = name
        self.bot = WebWeChat()
        self.queue = queue

    def _run(self, str, func, *args):
        """ 运行方法，并输出日志 """
        logging.debug(str)
        if func(*args):
            logging.debug('%s... 成功' % (str))
        else:
            logging.debug('%s... 失败' % (str))
            logging.debug('[*] 退出程序')
            exit()

    def handleMsg(self, retcode, selector, msg):
        """
        处理信息接口
        """
        pass

    def sendMsg(self, content):
        """
        发送信息接口
        """
        pass

    def listenMsgMode(self):
        """ 监听信息 """
        logging.debug('[*] 进入消息监听模式 ... 成功')
        while True:
            last_check_ts = time.time()
            [retcode, selector] = self.bot.synccheck()
            logging.debug('retcode: %s, selector: %s' % (retcode, selector))
            if retcode == '0' and selector in ['2', '6', '7']:
                r = self.bot.webwxsync()
            self.handleMsg(retcode, selector, r)

            if retcode in ('1100', '1101'):
                self.queue.send('quit')
                break
            if retcode == '0' and selector == '0':
                time.sleep(1)

            if (time.time()-last_check_ts) <= self.time_out:
                time.sleep(1)
            logging.debug("Last Check At %s, now is %s" % (
                last_check_ts, time.time()))

    def beat(self):
        """ 心跳线程 """
        self.queue.put(self.name+":start")
        self.stop_beat_event = threading.Event()
        while not self.stop_beat_event.wait(1):
            self.queue.put(self.name+":beat")
            time.sleep(random.randint(*self.beat_time_out))

    def start(self):
        """
        启动

        queuen: 发送消息队列
        """

        bot = self.bot

        logging.debug('[*] 微信网页版 ... 开动')

        self._run('[*] 正在获取 uuid ... ', bot.get_uuid)
        logging.debug('[*] 正在获取二维码 ... 成功')
        """ 生成二维码 """
        if sys.platform.startswith('win'):
            os.startfile(bot.get_qrcode('jpg'))
        else:
            _print_qr(bot.get_qrcode('str'))

        logging.info('[*] 请使用微信扫描二维码以登录 ... ')
        while True:
            if not bot.wait_for_login():
                continue
                logging.info('[*] 请在手机上点击确认以登录 ... ')
            if not bot.wait_for_login(0):
                continue
            break

        self._run('[*] 正在登录 ... ', bot.login)
        self._run('[*] 微信初始化 ... ', bot.webwxinit)
        self._run('[*] 开启状态通知 ... ', bot.webwxstatusnotify)
        self._run('[*] 获取联系人 ... ', bot.webwxgetcontact)

        logging.info('[*] 应有 %s 个联系人，读取到联系人 %d 个' %
                   (bot.MemberCount, len(bot.MemberList)))
        logging.info(('[*] 共有 %d 个群 | %d 个直接联系人 | %d 个特殊账号 ｜ '
                    '%d 公众号或服务号') % (
                        len(bot.GroupList), len(bot.ContactList),
                        len(bot.SpecialUsersList), len(bot.PublicUsersList)))

        self._run('[*] 获取群 ... ', bot.webwxbatchgetcontact)
        logging.debug('[*] 微信网页版 ... 开动')
        logging.debug(self)

        self._run('[*] 进行同步线路测试 ... ', self.bot.testsynccheck)

        # 启动监听程序
        self.listen_process = multiprocessing.Process(target=self.listenMsgMode)
        self.listen_process.start()

        # 发送信息，在初始化之后，就成常量了
        #   self.BaseRequest
        #   self.pass_ticket
        # 要注意通讯录的更新，同步线程与当前线程是隔离的，定期更新当前的通讯录
        #   FromUserName
        #   ToUserName
        # 如果多进程编程，需要注意!!!!!
        self.beat_thread = threading.Thread(
            target=self.beat
        )
        self.beat_thread.start()

    def quit(self):
        """ 退出，删除线程进程 """
        if self.listen_process:
            self.listen_process.terminate()
        # 停止心跳包
        self.stop_beat_event.set()
        self.beat_thread.join()

    @classmethod
    def new_client(cls, name, queue):
        """ 启动新实例 """
        app = cls(name, queue)
        app.start()
        return app


