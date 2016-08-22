#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 n3xtchen <echenwen@gmail.com>
#
# Distributed under terms of the GPL-2.0 license.

"""
队列服务
"""

import logging

from argparse import ArgumentParser
from multiprocessing import managers, Queue

class QueueManager(managers.BaseManager):
    """ 队列管理器 """
    pass


def start_server():
    """
    启动服务
    """
    # 参数配置
    parser = ArgumentParser(description='队列服务器')
    parser.add_argument('--host', dest='host', default="0.0.0.0",
                        help=u'主机地址')
    parser.add_argument('--port', dest='port', type=int,
                        default=50000, help=u'端口')
    parser.add_argument('--auth-key', dest='auth_key',
                        default="n3xtchen", help=u'认证码')
    args = parser.parse_args()

    # 新建队列
    queue = Queue()

    # 启动服务
    try:
        logging.warning(u"队列服务将启动...\n 地址:%s:%s", args.host, args.port)
        QueueManager.register('get_queue', callable=lambda: queue)
        manager = QueueManager(
            address=(args.host, args.port),
            authkey=args.auth_key
        )
        server = manager.get_server()
        server.serve_forever()
    except:
        logging.error(u"请检查你的IP与端口是否被占用!")


if __name__ == '__main__':

    start_server()


