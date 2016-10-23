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

class WechatEcho(WeChatDispatch):

    def send_msg(self, word):
        if self.bot.webwxsendmsg(word, 'filehelper'):
            print self.name, ':[*] 消息发送成功'
            print self.bot.BaseRequest
            print self.bot.SyncKey
        else:
            print self.name, ':[*] 消息发送失败'

    def handle_msg(self, retcode, selector, msg):
        """
        处理信息接口
        """
        # f.write(json.dumps(msg))
        for msg in r['AddMsgList']:
            loging.info('[*] 你有新的消息，请注意查收')
            msg_id = msg['MsgId']

            # 接受媒体信息
            if msgType == 3:
                image = self.webwxgetmsgimg(msg_id)
            elif msgType == 34:
                voice = self.webwxgetvoice(msg_id)
            elif msgType in [43, 62]:
                video = self.webwxgetvideo(msg_id)


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
            apps[name] = WechatEcho.new_client(name, queue)
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
                    apps[name].send_msg(msg)
                else:
                    print name, ':请等候'
                print name, msg
            else:
                time.sleep(1)
        else:
            time.sleep(1)

    print u"程序结束"


