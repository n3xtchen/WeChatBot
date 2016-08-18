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
import sys
import os
import platform
import random
import multiprocessing
import logging
from collections import defaultdict
from urlparse import urlparse
from lxml import html

from libs.util import _print_qr
from extensions import ChatBot
from WeChatBase import WebWeChat

def catchKeyboardInterrupt(fn):
    def wrapper(*args):
        try:
            return fn(*args)
        except KeyboardInterrupt:
            print '\n[*] 强制退出程序'
            logging.debug('[*] 强制退出程序')
    return wrapper


class WechatCmd(WebWeChat, ChatBot):

    time_out = 20  # 同步最短时间间隔（单位：秒）

    def _safe_open(self, path):
        """ 打开文件，如图片 """
        if self.autoOpen:
            if platform.system() == "Linux":
                os.system("xdg-open %s &" % path)
            else:
                os.system('open %s &' % path)

    def _run(self, str, func, *args):
        """ 运行方法，并输出日志 """
        self._echo(str)
        if func(*args):
            print '成功'
            logging.debug('%s... 成功' % (str))
        else:
            print('失败\n[*] 退出程序')
            logging.debug('%s... 失败' % (str))
            logging.debug('[*] 退出程序')
            exit()

    def _echo(self, str):
        """ 输出，并清理 """
        sys.stdout.write(str)
        sys.stdout.flush()

    def genQRCode(self):
        """ 生成二维码 """
        if sys.platform.startswith('win'):
            os.startfile(self.get_qrcode('jpg'))
        else:
            _print_qr(self.get_qrcode('str'))

    def _showMsg(self, message):

        srcName = None
        dstName = None
        groupName = None
        content = None

        msg = message
        logging.debug(msg)

        if msg['raw_msg']:
            srcName = self.getUserRemarkName(msg['raw_msg']['FromUserName'])
            dstName = self.getUserRemarkName(msg['raw_msg']['ToUserName'])
            content = msg['raw_msg']['Content'].replace(
                '&lt;', '<').replace('&gt;', '>')
            message_id = msg['raw_msg']['MsgId']

            if content.find('http://weixin.qq.com/cgi-bin/redirectforward?args=') != -1:
                # 地理位置消息
                data = self._get(content).decode('gbk').encode('utf-8')
                pos = self._searchContent('title', data, 'xml')
                tree = html.fromstring(self._get(content))
                url = tree.xpath('//html/body/div/img')[0].attrib['src']

                for item in urlparse(url).query.split('&'):
                    if item.split('=')[0] == 'center':
                        loc = item.split('=')[-1:]

                content = '%s 发送了一个 位置消息 - 我在 [%s](%s) @ %s]' % (
                    srcName, pos, url, loc)

            if msg['raw_msg']['ToUserName'] == 'filehelper':
                # 文件传输助手
                dstName = '文件传输助手'

            if msg['raw_msg']['FromUserName'][:2] == '@@':
                # 接收到来自群的消息
                if re.search(":<br/>", content, re.IGNORECASE):
                    [people, content] = content.split(':<br/>', 1)
                    groupName = srcName
                    srcName = self.getUserRemarkName(people)
                    dstName = 'GROUP'
                else:
                    groupName = srcName
                    srcName = 'SYSTEM'
            elif msg['raw_msg']['ToUserName'][:2] == '@@':
                # 自己发给群的消息
                groupName = dstName
                dstName = 'GROUP'

            # 收到了红包
            if content == '收到红包，请在手机上查看':
                msg['message'] = content

            # 指定了消息内容
            if 'message' in msg.keys():
                content = msg['message']

        if groupName != None:
            print '%s |%s| %s -> %s: %s' % (message_id, groupName.strip(),
                                            srcName.strip(), dstName.strip(),
                                            content.replace('<br/>', '\n'))
            logging.info('%s |%s| %s -> %s: %s' % (message_id, groupName.strip(),
                                                   srcName.strip(), dstName.strip(),
                                                   content.replace('<br/>', '\n')))
        else:
            print '%s %s -> %s: %s' % (message_id, srcName.strip(), dstName.strip(),
                                       content.replace('<br/>', '\n'))
            logging.info('%s %s -> %s: %s' % (message_id, srcName.strip(),
                                              dstName.strip(),
                                              content.replace('<br/>', '\n')))

    def handleMsg(self, r):
        for msg in r['AddMsgList']:
            print '[*] 你有新的消息，请注意查收'
            logging.debug('[*] 你有新的消息，请注意查收')

            if self.DEBUG:
                fn = 'msg' + str(int(random.random() * 1000)) + '.json'
                with open(fn, 'w') as f:
                    f.write(json.dumps(msg))
                print '[*] 该消息已储存到文件: ' + fn
                logging.debug('[*] 该消息已储存到文件: %s' % (fn))

            msgType = msg['MsgType']
            name = self.getUserRemarkName(msg['FromUserName'])
            content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')
            msgid = msg['MsgId']

            if msgType == 1:
                raw_msg = {'raw_msg': msg}
                self._showMsg(raw_msg)
                if self.autoReplyMode:
                    ans = self._xiaodoubi(content) + '\n[微信机器人自动回复]'
                    if self.webwxsendmsg(ans, msg['FromUserName']):
                        print '自动回复: ' + ans
                        logging.info('自动回复: ' + ans)
                    else:
                        print '自动回复失败'
                        logging.info('自动回复失败')
            elif msgType == 3:
                image = self.webwxgetmsgimg(msgid)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发送了一张图片: %s' % (name, image)}
                self._showMsg(raw_msg)
                self._safe_open(image)
            elif msgType == 34:
                voice = self.webwxgetvoice(msgid)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发了一段语音: %s' % (name, voice)}
                self._showMsg(raw_msg)
                self._safe_open(voice)
            elif msgType == 42:
                info = msg['RecommendInfo']
                print '%s 发送了一张名片:' % name
                print '========================='
                print '= 昵称: %s' % info['NickName']
                print '= 微信号: %s' % info['Alias']
                print '= 地区: %s %s' % (info['Province'], info['City'])
                print '= 性别: %s' % ['未知', '男', '女'][info['Sex']]
                print '========================='
                raw_msg = {'raw_msg': msg, 'message': '%s 发送了一张名片: %s' % (
                    name.strip(), json.dumps(info))}
                self._showMsg(raw_msg)
            elif msgType == 47:
                url = self._searchContent('cdnurl', content)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发了一个动画表情，点击下面链接查看: %s' % (name, url)}
                self._showMsg(raw_msg)
                self._safe_open(url)
            elif msgType == 49:
                appMsgType = defaultdict(lambda: "")
                appMsgType.update({5: '链接', 3: '音乐', 7: '微博'})
                print '%s 分享了一个%s:' % (name, appMsgType[msg['AppMsgType']])
                print '========================='
                print '= 标题: %s' % msg['FileName']
                print '= 描述: %s' % self._searchContent('des', content, 'xml')
                print '= 链接: %s' % msg['Url']
                print '= 来自: %s' % self._searchContent('appname', content, 'xml')
                print '========================='
                card = {
                    'title': msg['FileName'],
                    'description': self._searchContent('des', content, 'xml'),
                    'url': msg['Url'],
                    'appname': self._searchContent('appname', content, 'xml')
                }
                raw_msg = {'raw_msg': msg, 'message': '%s 分享了一个%s: %s' % (
                    name, appMsgType[msg['AppMsgType']], json.dumps(card))}
                self._showMsg(raw_msg)
            elif msgType == 51:
                raw_msg = {'raw_msg': msg, 'message': '[*] 成功获取联系人信息'}
                self._showMsg(raw_msg)
            elif msgType in [43, 62]:
                video = self.webwxgetvideo(msgid)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发了一段视频: %s' % (name, video)}
                self._showMsg(raw_msg)
                self._safe_open(video)
            elif msgType == 10002:
                raw_msg = {'raw_msg': msg, 'message': '%s 撤回了一条消息' % name}
                self._showMsg(raw_msg)
            else:
                logging.debug('[*] 该消息类型为: %d，可能是表情，图片, 链接或红包: %s' %
                              (msg['MsgType'], json.dumps(msg)))
                raw_msg = {
                    'raw_msg': msg, 'message': '[*] 该消息类型为: %d，可能是表情，图片, 链接或红包' % msg['MsgType']}
                self._showMsg(raw_msg)

    def getUserRemarkName(self, id):
        name = '未知群' if id[:2] == '@@' else '陌生人'
        if id == self.User['UserName']:
            return self.User['NickName']  # 自己

        if id[:2] == '@@':
            # 群
            name = self.getGroupName(id)
        else:
            # 特殊账号
            for member in self.SpecialUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']

            # 公众号或服务号
            for member in self.PublicUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']

            # 直接联系人
            for member in self.ContactList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']
            # 群友
            for member in self.GroupMemeberList:
                if member['UserName'] == id:
                    name = member['DisplayName'] if member[
                        'DisplayName'] else member['NickName']

        if name == '未知群' or name == '陌生人':
            logging.debug(id)
        return name

    def getUSerID(self, name):
        for member in self.MemberList:
            if name == member['RemarkName'] or name == member['NickName']:
                return member['UserName']
        return None

    def sendMsg(self, name, word, isfile=False):
        id = self.getUSerID(name)
        if id:
            if isfile:
                with open(word, 'r') as f:
                    for line in f.readlines():
                        line = line.replace('\n', '')
                        self._echo('-> ' + name + ': ' + line)
                        if self.webwxsendmsg(line, id):
                            print ' [成功]'
                        else:
                            print ' [失败]'
                        time.sleep(1)
            else:
                if self.webwxsendmsg(word, id):
                    print '[*] 消息发送成功'
                    logging.debug('[*] 消息发送成功')
                else:
                    print '[*] 消息发送失败'
                    logging.debug('[*] 消息发送失败')
        else:
            print '[*] 此用户不存在'
            logging.debug('[*] 此用户不存在')

    def getGroupName(self, id):
        name = '未知群'
        for member in self.GroupList:
            if member['UserName'] == id:
                name = member['NickName']
        if name == '未知群':
            # 现有群里面查不到
            GroupList = self.get_name_by_id(id)
            for group in GroupList:
                self.GroupList.append(group)
                if group['UserName'] == id:
                    name = group['NickName']
                    MemberList = group['MemberList']
                    for member in MemberList:
                        self.GroupMemeberList.append(member)
        return name

    def sendMsgToAll(self, word):
        for contact in self.ContactList:
            name = contact['RemarkName'] if contact[
                'RemarkName'] else contact['NickName']
            id = contact['UserName']
            self._echo('-> ' + name + ': ' + word)
            if self.webwxsendmsg(word, id):
                print ' [成功]'
            else:
                print ' [失败]'
            time.sleep(1)

    def sendImg(self, name, file_name):
        response = self.webwxuploadmedia(file_name)
        media_id = ""
        if response is not None:
            media_id = response['MediaId']
        user_id = self.getUSerID(name)
        response = self.webwxsendmsgimg(media_id, user_id)

    def sendEmotion(self, name, file_name):
        response = self.webwxuploadmedia(file_name)
        media_id = ""
        if response is not None:
            media_id = response['MediaId']
        user_id = self.getUSerID(name)
        response = self.webwxsendmsgemotion(media_id, user_id)

    def listenMsgMode(self):
        print '[*] 进入消息监听模式 ... 成功'
        logging.debug('[*] 进入消息监听模式 ... 成功')
        self._run('[*] 进行同步线路测试 ... ', self.testsynccheck)
        playWeChat = 0
        redEnvelope = 0
        while True:
            last_check_ts = time.time()
            [retcode, selector] = self.synccheck()
            logging.debug('retcode: %s, selector: %s' % (retcode, selector))
            if retcode == '1100':
                print '[*] 你在手机上登出了微信，债见'
                logging.debug('[*] 你在手机上登出了微信，债见')
                break
            if retcode == '1101':
                print '[*] 你在其他地方登录了 WEB 版微信，债见'
                logging.debug('[*] 你在其他地方登录了 WEB 版微信，债见')
                break
            elif retcode == '0':
                # 正常
                if selector == '2':
                    # 新信息
                    r = self.webwxsync()
                    if r is not None:
                        self.handleMsg(r)
                elif selector == '6':
                    r = self.webwxsync()
                    if r is not None:
                        logging.debug(r)
                    # 红包
                    # TODO
                    redEnvelope += 1
                    print '[*] 收到疑似红包消息 %d 次' % redEnvelope
                    logging.debug('[*] 收到疑似红包消息 %d 次' % redEnvelope)
                elif selector == '7':
                    # 进入/离开聊天界面
                    playWeChat += 1
                    print '[*] 你在手机上玩微信被我发现了 %d 次' % playWeChat
                    logging.debug('[*] 你在手机上玩微信被我发现了 %d 次' % playWeChat)
                    r = self.webwxsync()
                elif selector == '0':
                    # 正常
                    time.sleep(1)
            if (time.time()-last_check_ts) <= self.time_out:
                time.sleep(1)
            logging.debug("Last Check At %s, now is %s" % (
                last_check_ts, time.time()))

    @catchKeyboardInterrupt
    def start(self):
        self._echo('[*] 微信网页版 ... 开动')
        print
        logging.debug('[*] 微信网页版 ... 开动')
        while True:
            self._run('[*] 正在获取 uuid ... ', self.get_uuid)
            self._echo('[*] 正在获取二维码 ... 成功')
            print
            logging.debug('[*] 微信网页版 ... 开动')
            self.genQRCode()
            print '[*] 请使用微信扫描二维码以登录 ... '
            if not self.wait_for_login():
                continue
                print '[*] 请在手机上点击确认以登录 ... '
            if not self.wait_for_login(0):
                continue
            break

        self._run('[*] 正在登录 ... ', self.login)
        self._run('[*] 微信初始化 ... ', self.webwxinit)
        self._run('[*] 开启状态通知 ... ', self.webwxstatusnotify)
        self._run('[*] 获取联系人 ... ', self.webwxgetcontact)
        self._echo('[*] 应有 %s 个联系人，读取到联系人 %d 个' %
                   (self.MemberCount, len(self.MemberList)))
        print
        self._echo(('[*] 共有 %d 个群 | %d 个直接联系人 | %d 个特殊账号 ｜ '
                    '%d 公众号或服务号') % (
                        len(self.GroupList), len(self.ContactList),
                        len(self.SpecialUsersList), len(self.PublicUsersList)))
        print
        self._run('[*] 获取群 ... ', self.webwxbatchgetcontact)
        logging.debug('[*] 微信网页版 ... 开动')
        if self.DEBUG:
            print self
        logging.debug(self)

        if self.interactive and raw_input('[*] 是否开启自动回复模式(y/n): ') == 'y':
            self.autoReplyMode = True
            print '[*] 自动回复模式 ... 开启'
            logging.debug('[*] 自动回复模式 ... 开启')
        else:
            print '[*] 自动回复模式 ... 关闭'
            logging.debug('[*] 自动回复模式 ... 关闭')

        listenProcess = multiprocessing.Process(target=self.listenMsgMode)
        listenProcess.start()

        while True:
            text = raw_input('')
            if text == 'quit':
                listenProcess.terminate()
                logging.debug('[*] 退出微信')
                exit()
            elif text[:2] == '->':
                [name, word] = text[2:].split(':', 1)
                if name == 'all':
                    self.sendMsgToAll(word)
                else:
                    self.sendMsg(name, word)
            elif text[:3] == 'm->':
                [name, file] = text[3:].split(':', 1)
                self.sendMsg(name, file, True)
            elif text[:3] == 'f->':
                print '发送文件'
                logging.debug('发送文件')
            elif text[:3] == 'i->':
                print '发送图片'
                [name, file_name] = text[3:].split(':', 1)
                self.sendImg(name, file_name)
                logging.debug('发送图片')
            elif text[:3] == 'e->':
                print '发送表情'
                [name, file_name] = text[3:].split(':', 1)
                self.sendEmotion(name, file_name)
                logging.debug('发送表情')
            elif text[:3] == 'g->':
                print '发送群组'
                [gid, word] = text[3:].split(':', 1)
                self.webwxsendmsg(word, gid)
                logging.debug('发送群组')


if sys.stdout.encoding == 'cp936':
    sys.stdout = UnicodeStreamFilter(sys.stdout)


if __name__ == '__main__':

    logger = logging.getLogger(__name__)
    import coloredlogs
    coloredlogs.install(level='DEBUG')

    webwx = WechatCmd()
    webwx.start()
