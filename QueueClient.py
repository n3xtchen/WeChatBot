#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 n3xtchen <echenwen@gmail.com>
#
# Distributed under terms of the GPL-2.0 license.

"""
远端队列
"""

import os
import readline
from argparse import ArgumentParser
import atexit
from multiprocessing.managers import BaseManager

readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')
histfile = os.path.join(os.path.expanduser("~"), ".pyhist")

try:
    readline.read_history_file(histfile)
    readline.set_history_length(1000)
except IOError:
    pass

atexit.register(readline.write_history_file, histfile)
del os, histfile

# 参数配置
parser = ArgumentParser(description='队列服务器')
parser.add_argument('--host', dest='host', default="0.0.0.0",
                    help=u'主机地址')
parser.add_argument('--port', dest='port', type=int,
                    default=50000, help=u'端口')
parser.add_argument('--auth-key', dest='auth_key', 
                    default="n3xtchen", help=u'认证码')
args = parser.parse_args()

class QueueManager(BaseManager): pass
QueueManager.register('get_queue')
manager = QueueManager(
    address=(args.host, args.port),
    authkey=args.auth_key
)
manager.connect()

queue = manager.get_queue()

def input_loop():
    line = ''
    while line != 'stop':
        line = raw_input('Prompt ("stop" to quit): ')
        print 'n3xtchen %s' % line
        if line.startswith('post '):
            msg = line[5:]
            queue.put(msg)
        elif line == 'get':
            print queue.get()

input_loop()

