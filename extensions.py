#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 n3xtchen <echenwen@gmail.com>
#
# Distributed under terms of the GPL-2.0 license.

"""
外部拓展
"""

import logging

import urllib2
import cookielib
import requests
import json

from urllib import urlencode

from libs.util import _decode_dict

class RequestWithCookie(object):
    """ 带cookie的请求 """

    def init_cookie(self):
        """ 初始化cookie """

        self.cookie = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
        opener.addheaders = [('User-agent', self.user_agent)]
        urllib2.install_opener(opener)

    def _get(self, url, headers=None):
        """ http get """
        request = urllib2.Request(url=url)
        request.add_header('Referer', self.referer)
        if headers:
            for name, content in headers:
                request.add_header(name, content)
        response = urllib2.urlopen(request)
        data = response.read()
        logging.debug(url)
        logging.debug(' '.join(data.split()))
        return data

    def _post(self, url, params, jsonfmt=True):
        """ http post """
        if jsonfmt:
            request = urllib2.Request(url=url, data=json.dumps(params))
            request.add_header(
                'ContentType', 'application/json; charset=UTF-8')
        else:
            request = urllib2.Request(url=url, data=urlencode(params))
        response = urllib2.urlopen(request)
        data = response.read()
        logging.debug(url)
        logging.debug(' '.join(data.split()))
        if jsonfmt:
            return json.loads(data, object_hook=_decode_dict)
        return data


class ChatBot(object):
    """
    聊天机器人
    """

    def _xiaodoubi(self, word):
        url = 'http://www.xiaodoubi.com/bot/chat.php'
        try:
            r = requests.post(url, data={'chat': word})
            return r.content
        except:
            return "让我一个人静静 T_T..."

    def _simsimi(self, word):
        key = ''
        url = 'http://sandbox.api.simsimi.com/request.p?key=%s&lc=ch&ft=0.0&text=%s' % (
            key, word)
        r = requests.get(url)
        ans = r.json()
        if ans['result'] == '100':
            return ans['response']
        else:
            return '你在说什么，风太大听不清列'


