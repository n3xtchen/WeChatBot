#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 n3xtchen <echenwen@gmail.com>
#
# Distributed under terms of the GPL-2.0 license.

"""
命令行工具
"""

import json
import time
import re
import random
import multiprocessing
from multiprocessing import Process, Queue, Manager
from threading import Thread
import logging
from collections import defaultdict
from urlparse import urlparse
from lxml import html

from WeChatBot.extensions import ChatBot
from WeChatBot.WeChatDispatch import WeChatDispatch

class WechatPing(WeChatDispatch):

    def sendMsg(self, word):
        if self.bot.webwxsendmsg(word, 'filehelper'):
            print self.name, ':[*] 消息发送成功'
            print self.bot.BaseRequest
            print self.bot.SyncKey
        else:
            print self.name, ':[*] 消息发送失败'

    def handleMsg(self, retcode, selector, msg):
        """
        处理信息接口
        """

        if retcode == '1100':
            print '[*] 你在手机上登出了微信，债见'
        if retcode == '1101':
            print '[*] 你在其他地方登录了 WEB 版微信，债见'
        elif retcode == '0':
            # 正常
            if selector == '2':
                srcName = msg['raw_msg']['FromUserName']
                dstName = msg['raw_msg']['ToUserName']
                content = msg['raw_msg']['Content'].replace(
                    '&lt;', '<').replace('&gt;', '>')
                message_id = msg['raw_msg']['MsgId']
                print message_id, srcName, '->', dstName, ':', content
            elif selector == '6':
                print '[*] 收到疑似红包消息'
            elif selector == '7':
                print '[*] 你在手机上玩微信被我发现了'

if __name__ == '__main__':

    from multiprocessing.managers import BaseManager

    logger = logging.getLogger(__name__)
    import coloredlogs
    coloredlogs.install(level='DEBUG')

    class QueueManager(BaseManager): pass
    QueueManager.register('get_queue', callable=lambda:queue)
    m = QueueManager(address=('', 50000), authkey='n3xtchen')
    m.connect()
    queue = m.get_queue()

    apps = {}
    a = ''
    while a != 'stop':
        a = queue.get()
        print a
        if a.startswith('add'):
            name = 'u'+str(random.randint(1, 10))
            apps[name] = WechatPing.new_client(name, queue)
            print name
            continue
        if ':' in a:
            name, msg = a.split(":", 1)
            if name in apps:
                if msg == 'start':
                    apps[name].status = 1
                if msg == 'quit' and apps[name].status == 1:
                    apps[name].quit()
                    print name, 'is quit'
                elif apps[name].status == 1:
                    apps[name].sendMsg(msg)
                else:
                    print name, ':请等候'
                print name, msg
            else:
                time.sleep(1)
        else:
            time.sleep(1)

    print u"程序结束"


