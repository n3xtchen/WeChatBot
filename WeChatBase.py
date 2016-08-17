#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 n3xtchen <echenwen@gmail.com>
#
# Distributed under terms of the GPL-2.0 license.

"""
微信基础类
"""

import json
import time
import re
import os
import random
import logging
from collections import defaultdict
from urlparse import urlparse
from urllib import urlencode

from lxml import html
import xml.dom.minidom
import qrcode
# for media upload
import mimetypes
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests

from WeChatBot.libs.util import _transcoding
from WeChatBot.extensions import RequestWithCookie

SYNC_HOST = [
    'webpush.weixin.qq.com',
    'webpush2.weixin.qq.com',
    'webpush.wechat.com',
    'webpush1.wechat.com',
    'webpush2.wechat.com',
    'webpush1.wechatapp.com',
    # 'webpush.wechatapp.com'
]

SEND_MSG_TYPES = {
    'msg': lambda content: ('', {"Type": 1, "Content": _transcoding(content)}),
    'msgimg': lambda content: ('fun=async&f=json&', {"Type": 3, "MediaId": content}),
    'msgemotionicon': lambda content: ('fun=sys&f=json&', {
        "Type": 47, "EmojiFlag": 2, "MediaId": content
    })
}

class WebWeChat(RequestWithCookie):
    """
    web 微信的接口
    """

    def __str__(self):
        """ 基础信息 """
        description = \
            "=========================\n" + \
            "[#] Web Weixin\n" + \
            "[#] Debug Mode: " + str(self.DEBUG) + "\n" + \
            "[#] Uuid: " + self.uuid + "\n" + \
            "[#] Uin: " + str(self.uin) + "\n" + \
            "[#] Sid: " + self.sid + "\n" + \
            "[#] Skey: " + self.skey + "\n" + \
            "[#] DeviceId: " + self.device_id + "\n" + \
            "[#] PassTicket: " + self.pass_ticket + "\n" + \
            "========================="
        return description

    def __init__(self):
        """ 初始化 """
        self.DEBUG = False
        self.uuid = ''
        self.base_uri = ''
        self.redirect_uri = ''
        self.uin = ''
        self.sid = ''
        self.skey = ''
        self.pass_ticket = ''
        self.device_id = 'e' + repr(random.random())[2:17]
        self.BaseRequest = {}
        self.synckey = ''
        self.SyncKey = []
        self.User = []
        self.MemberList = []
        self.ContactList = []  # 好友
        self.GroupList = []  # 群
        self.GroupMemeberList = []  # 群友
        self.PublicUsersList = []  # 公众号／服务号
        self.SpecialUsersList = []  # 特殊账号
        self.autoReplyMode = False
        self.syncHost = ''
        self.user_agent = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/48.0.2564.109 Safari/537.36')
        self.referer = 'https://wx.qq.com/'
        self.interactive = False
        self.autoOpen = False

        # 文件保存
        self.saveFolder = os.path.join(os.getcwd(), 'saved')
        self.media_type = {
            'icon': 'jpg',
            'headimg': 'jpg',
            'msgimg': 'jpg',
            'video': 'mp4',
            'voice': 'mp3'
        }

        self.appid = 'wx782c26e4c19acffb'
        self.lang = 'zh_CN'
        self.memberCount = 0
        self.SpecialUsers = [
            'newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail', 'fmessage',
            'tmessage', 'qmessage', 'qqsync', 'floatbottle', 'lbsapp',
            'shakeapp', 'medianote', 'qqfriend', 'readerapp', 'blogapp',
            'facebookapp', 'masssendapp', 'meishiapp', 'feedsapp',
            'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
            'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c',
            'officialaccounts', 'notification_messages', 'wxid_novlwrv3lqwv11',
            'gh_22b87fa7cb3c', 'wxitil', 'userexperience_alarm',
            'notification_messages'
        ]
        self.media_count = -1

        self.init_cookie()  # 初始化 cookie

    def __getattr__(self, name):
        if name.startswith('webwxget'):
            media_type = name[len("webwxget"):]
            return lambda media_id: self.webwxget(media_type, media_id)
        elif name.startswith('webwxsend'):
            media_type = name[len("webwxsend"):]
            return lambda media_id, user_id=None: self.webwxsend(media_type, media_id, user_id)
        else:
            raise AttributeError(name)

    def load_config(self, config):
        """ 载入定制化配置 """
        if config['DEBUG']:
            self.DEBUG = config['DEBUG']
        if config['autoReplyMode']:
            self.autoReplyMode = config['autoReplyMode']
        if config['user_agent']:
            self.user_agent = config['user_agent']
        if config['interactive']:
            self.interactive = config['interactive']
        if config['autoOpen']:
            self.autoOpen = config['autoOpen']

    def get_uuid(self):
        """ 获取用户ID """
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': self.appid,
            'fun': 'new',
            'lang': self.lang,
            '_': int(time.time()),
        }
        data = self._post(url, params, False)
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        if pm:
            code = pm.group(1)
            self.uuid = pm.group(2)
            return code == '200'
        return False

    def get_qrcode(self, media_type):
        """ 获取二维码 """
        if media_type == "jpg":
            url = 'https://login.weixin.qq.com/qrcode/' + self.uuid
            params = {'t': 'webwx', '_': int(time.time())}
            data = self._post(url, params, False)
            return self._save_file('qrcode.jpg', data, 'qrcodes')
        elif media_type == "str":
            qr = qrcode.QRCode()
            qr.border = 1
            qr.add_data('https://login.weixin.qq.com/l/' + self.uuid)
            return qr.get_matrix()

    def wait_for_login(self, tip=1):
        """ 等待登录 """
        time.sleep(tip)
        url = ('https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s'
               '&uuid=%s&_=%s') % (tip, self.uuid, int(time.time()))
        data = self._get(url)
        pm = re.search(r'window.code=(\d+);', data)
        code = pm.group(1)

        if code == '201':
            return True
        elif code == '200':
            pm = re.search(r'window.redirect_uri="(\S+?)";', data)
            r_uri = pm.group(1) + '&fun=new'
            self.redirect_uri = r_uri
            self.base_uri = r_uri[:r_uri.rfind('/')]
            return True
        elif code == '408':
            logging.info('[登陆超时]')
        else:
            logging.info('[登陆异常]')
        return False

    def login(self):
        """ 登陆后获取相关信息 """
        data = self._get(self.redirect_uri)
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement

        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            return False

        self.BaseRequest = {
            'Uin': int(self.uin),
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.device_id,
        }
        return True

    def webwxinit(self):
        """ 微信初始化 """
        url = self.base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        params = {
            'BaseRequest': self.BaseRequest
        }
        dic = self._post(url, params)
        self.SyncKey = dic['SyncKey']
        self.User = dic['User']
        # synckey for synccheck
        self.synckey = '|'.join([
            str(keyVal['Key']) + '_' + str(keyVal['Val'])
            for keyVal in self.SyncKey['List']
        ])

        return dic['BaseResponse']['Ret'] == 0

    def webwxstatusnotify(self):
        """ 状态通知 """
        url = self.base_uri + \
            '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % (self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Code": 3,
            "FromUserName": self.User['UserName'],
            "ToUserName": self.User['UserName'],
            "ClientMsgId": int(time.time())
        }
        dic = self._post(url, params)

        return dic['BaseResponse']['Ret'] == 0

    def webwxgetcontact(self):
        """ 获取通讯录 """
        SpecialUsers = self.SpecialUsers
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        dic = self._post(url, {})

        self.MemberCount = dic['MemberCount']
        self.MemberList = dic['MemberList']
        ContactList = self.MemberList[:]
        GroupList = self.GroupList[:]
        PublicUsersList = self.PublicUsersList[:]
        SpecialUsersList = self.SpecialUsersList[:]

        for i in xrange(len(ContactList) - 1, -1, -1):
            Contact = ContactList[i]
            if Contact['VerifyFlag'] & 8 != 0:  # 公众号/服务号
                ContactList.remove(Contact)
                self.PublicUsersList.append(Contact)
            elif Contact['UserName'] in SpecialUsers:  # 特殊账号
                ContactList.remove(Contact)
                self.SpecialUsersList.append(Contact)
            elif Contact['UserName'].find('@@') != -1:  # 群聊
                ContactList.remove(Contact)
                self.GroupList.append(Contact)
            elif Contact['UserName'] == self.User['UserName']:  # 自己
                ContactList.remove(Contact)
        self.ContactList = ContactList

        return True

    def webwxbatchgetcontact(self):
        """ 批量获取通讯录 """
        url = self.base_uri + \
            '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
                int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Count": len(self.GroupList),
            "List": [{"UserName": g['UserName'], "EncryChatRoomId":""}
                     for g in self.GroupList]
        }
        dic = self._post(url, params)

        # blabla ...
        ContactList = dic['ContactList']
        ContactCount = dic['Count']
        self.GroupList = ContactList

        for i in xrange(len(ContactList) - 1, -1, -1):
            Contact = ContactList[i]
            MemberList = Contact['MemberList']
            for member in MemberList:
                self.GroupMemeberList.append(member)
        return True

    def get_name_by_id(self, id):
        """ 通过ID获取用户名 """
        url = self.base_uri + \
            '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
                int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Count": 1,
            "List": [{"UserName": id, "EncryChatRoomId": ""}]
        }
        dic = self._post(url, params)

        # blabla ...
        return dic['ContactList']

    # 同步，保持socket
    def testsynccheck(self):
        """ 选择可用的同步服务器 """
        for host in SYNC_HOST:
            self.syncHost = host
            [retcode, selector] = self.synccheck()
            if retcode == '0':
                return True
        return False

    def synccheck(self):
        """ 同步检查 """
        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.device_id,
            'synckey': self.synckey,
            '_': int(time.time()),
        }
        url = 'https://' + self.syncHost + \
            '/cgi-bin/mmwebwx-bin/synccheck?' + urlencode(params)
        data = self._get(url)
        pm = re.search(
            r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}', data)
        retcode = pm.group(1)
        selector = pm.group(2)
        return [retcode, selector]

    def webwxsync(self):
        """ 同步检查成功后，获取信息 """
        url = self.base_uri + \
            '/webwxsync?sid=%s&skey=%s&pass_ticket=%s' % (
                self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'SyncKey': self.SyncKey,
            'rr': ~int(time.time())
        }
        dic = self._post(url, params)
        logging.debug(json.dumps(dic))

        if dic['BaseResponse']['Ret'] == 0:
            self.SyncKey = dic['SyncKey']
            self.synckey = '|'.join([
                str(keyVal['Key']) + '_' + str(keyVal['Val'])
                for keyVal in self.SyncKey['List']
            ])
        return dic

    # 发送信息
    def webwxuploadmedia(self, image_name):
        """ 上传媒体接口 """
        url = ('https://file2.wx.qq.com/cgi-bin/mmwebwx-bin/webwxuploadmedia?'
               'f=json')
        # 计数器
        self.media_count = self.media_count + 1
        # 文件名
        file_name = image_name
        # MIME格式
        # mime_type = application/pdf, image/jpeg, image/png, etc.
        mime_type = mimetypes.guess_type(image_name, strict=False)[0]
        # 微信识别的文档格式，微信服务器应该只支持两种类型的格式。pic和doc
        # pic格式，直接显示。doc格式则显示为文件。
        media_type = 'pic' if mime_type.split('/')[0] == 'image' else 'doc'
        # 上一次修改日期
        lastModifieDate = 'Thu Mar 17 2016 00:55:10 GMT+0800 (CST)'
        # 文件大小
        file_size = os.path.getsize(file_name)
        # PassTicket
        pass_ticket = self.pass_ticket
        # clientMediaId
        client_media_id = str(int(time.time() * 1000)) + \
            str(random.random())[:5].replace('.', '')
        # webwx_data_ticket
        webwx_data_ticket = ''
        for item in self.cookie:
            if item.name == 'webwx_data_ticket':
                webwx_data_ticket = item.value
                break
        if webwx_data_ticket == '':
            return "None Fuck Cookie"

        uploadmediarequest = json.dumps({
            "BaseRequest": self.BaseRequest,
            "ClientMediaId": client_media_id,
            "TotalLen": file_size,
            "StartPos": 0,
            "DataLen": file_size,
            "MediaType": 4
        }, ensure_ascii=False).encode('utf8')

        multipart_encoder = MultipartEncoder(
            fields={
                'id': 'WU_FILE_' + str(self.media_count),
                'name': file_name,
                'type': mime_type,
                'lastModifieDate': lastModifieDate,
                'size': str(file_size),
                'mediatype': media_type,
                'uploadmediarequest': uploadmediarequest,
                'webwx_data_ticket': webwx_data_ticket,
                'pass_ticket': pass_ticket,
                'filename': (file_name, open(file_name, 'rb'),
                             mime_type.split('/')[1])
            },
            boundary='-----------------------------1575017231431605357584454111'
        )

        headers = {
            'Host': 'file2.wx.qq.com',
            'User-Agent': self.user_agent,
            'Accept': ('text/html,application/xhtml+xml,application/xml;q=0.9,*/*'
                       ';q=0.8'),
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://wx2.qq.com/',
            'Content-Type': multipart_encoder.content_type,
            'Origin': 'https://wx2.qq.com',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

        r = requests.post(url, data=multipart_encoder, headers=headers)
        response_json = r.json()
        if response_json['BaseResponse']['Ret'] == 0:
            return response_json
        return None

    def webwxsend(self, msg_type_name, content, user_id='filehelper'):
        """ 发送 """
        if msg_type_name in SEND_MSG_TYPES:
            msg_type = SEND_MSG_TYPES[msg_type_name](content)
            url = '{}/webwxsend{}?{}pass_ticket={}'.format(
                    self.base_uri, msg_type_name, msg_type[0], self.pass_ticket
                    )

            client_msg_id = str(int(time.time() * 1000)) + \
                str(random.random())[:5].replace('.', '')
            data_json = {
                "BaseRequest": self.BaseRequest,
                "Msg": {
                    "FromUserName": self.User['UserName'],
                    "ToUserName": user_id,
                    "LocalID": client_msg_id,
                    "ClientMsgId": client_msg_id
                }
            }

            data_json['Msg'].update(msg_type[1])

            headers = {'content-type': 'application/json; charset=UTF-8'}
            data = json.dumps(data_json, ensure_ascii=False).encode('utf8')
            r = requests.post(url, data=data, headers=headers)
            dic = r.json()
            return dic['BaseResponse']['Ret'] == 0
        else:
            logging.debug('无该类型信息: %s' % msg_type)
            return False

    # 服务器获取媒体
    def _save_file(self, filename, data, sub_dir):
        """ 保存文件 """
        dirName = os.path.join(self.saveFolder, sub_dir)
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        fn = os.path.join(dirName, filename)
        logging.debug('Saved file: %s' % fn)
        with open(fn, 'wb') as f:
            f.write(data)
            f.close()
        return fn

    def webwxget(self, media_type, id):
        """ 获取图片，声音或影片 """

        if media_type in self.media_type:
            url = self.base_uri + \
                '/webwxget{}?username={}&skey={}'.format(media_type, id, self.skey)
            if media_type in ['video', 'voice']:
                data = self._get(url, (('Range', 'bytes=0-'),))
            else:
                data = self._get(url)
            fn = 'img_' + id + '.' + self.media_type[media_type]
            return self._save_file(fn, data, media_type+'s')
        else:
            logging.debug("不存在该媒体类型: %s" % media_type)

    def _searchContent(self, key, content, fmat='attr'):
        """ 地理位置 """
        if fmat == 'attr':
            pm = re.search(key + r'\s?=\s?"([^"<]+)"', content)
            if pm:
                return pm.group(1)
        elif fmat == 'xml':
            pm = re.search(r'<{0}>([^<]+)</{0}>'.format(key), content)
            if not pm:
                pm = re.search(
                    r'<{0}><\!\[CDATA\[(.*?)\]\]></{0}>'.format(key), content)
            if pm:
                return pm.group(1)
        return '未知'



