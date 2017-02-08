#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" rssmailerconfig.py

    Copyright 2013-2017 mc6312

    This file is part of RSSMailer.

    Foobar is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Foobar is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with RSSMailer.  If not, see <http://www.gnu.org/licenses/>."""

import sys
import os, os.path
from collections import namedtuple
from configparser import RawConfigParser
from locale import getdefaultlocale
from rssmailerlogger import init_logger


IOENCODING = getdefaultlocale()[1]
if not IOENCODING:
    IOENCODING = sys.getfilesystemencoding()


DOWNLOAD_TIMEOUT = 10
DOWNLOAD_TIMEOUT_MIN = 1
DOWNLOAD_TIMEOUT_MAX = 60
DOWNLOAD_STREAMS = 10


CONFIG_EXAMPLE = u"""[settings]
; количество одновременных загрузок (если не указано - %d)
downloads = 10

[mail]
; адрес отправителя
from = sender@someserver.net
; адреса получателей, не менее одного, разделяются запятыми
; если получатели не указаны - отправитель будет слать самому себе
to = stinky@shitty.poo, cthoolhu@oldones.org
; адрес SMTP-сервера (и при необходимости порт)
smtp = smtp.someserver.net:587
; логин (если нужна аутентификация)
login = username
; пароль.
; если указан пароль, но логин не указан - в качестве логина
; используется адрес отправителя (для упрощения общения с gmail и подобными)
; если указан логин, но не указан пароль - будет ругань и никаких писем.
; так как пароль тут хранится в открытом виде, советую завести в качестве
; ящика-отправителя (mail.from) какую-то отдельную мыльницу, не используемую
; больше ни для чего
password = PaSsWoRd
; использовать ли TLS
tls = yes
; кодировка писем. если не указана - будет использована UTF-8
charset = utf-8
; текст, добавляемый в начале заголовков всех писем
subject-prefix =
; текст, добавляемый в конце заголовков всех писем
subject-suffix =
""" % DOWNLOAD_STREAMS


class CfgParser(RawConfigParser):
    """Обертка с костылями, ибо исходный парсер шибко туп"""

    def __init__(self, fname):
        RawConfigParser.__init__(self)

        self.filename = fname

    def load(self):
        if os.path.exists(self.filename):
            self.read(self.filename, encoding=IOENCODING)

    def save(self):
        with open(self.filename, 'w+', encoding=IOENCODING) as f:
            self.write(f, True)

    def get_str(self, section, option, default=u'', sstrip=True):
        """Возвращает значение переменной с именем option из секции section.
        Если переменная заключена в одинарные или двойные кавычки - они удаляются.
        Если переменная отсутствует, возвращает default."""

        if self.has_option(section, option):
            s = self.get(section, option)
            # может, в глубинах пыхтоновых библиотек есть готовая обрезалка
            # кавычек, но я ее не нашел
            if len(s) >= 2:
                c = s[0]
                if (c in '\'"') and (s[-1] == c):
                    s = s[1:-1]

                # пробелы в начале и в конце не трогаем!
                # поддержка кавычек присобачена как раз для сохранения пробелов,
                # которые стандартный парсер обрезает

            return s

        else:
            return default

    def get_path(self, section, option, default=None):
        """Возвращает значение переменной с именем option из секции section.
        Если переменная существует, возвращает ее значение, развернув
        переменные окружения (в т.ч. "~/"), относительный путь в абсолютный.
        Внимание! Проверка на существование пути не производится!
        Если переменная отсутствует, возвращает default."""

        if self.has_option(section, option):
            v = os.path.abspath(os.path.expandvars(os.path.expanduser(self.get(section, option))))
        else:
            return default

    def get_bool(self, section, option, default=False):
        """Возвращает значение переменной с именем option из секции section.
        Если переменная отсутствует, возвращает default."""

        if self.has_option(section, option):
            return self.getboolean(section, option)
        else:
            return default

    def get_int(self, section, option, default=0, minv=None, maxv=None):
        """Возвращает значение переменной с именем option из секции section.
        Если переменная отсутствует, возвращает default.
        Если указан диапазон (minv и/или maxv), возвращает значение в пределах
        диапазона."""

        if self.has_option(section, option):
            v = self.getint(section, option)
            if (minv is not None) and (v < minv):
                v = minv
            if (maxv is not None) and (v > maxv):
                v = maxv

            return v
        else:
            return default


class RSSMailerEnvironment():
    CS_MAIL = u'mail'
    CS_SETTINGS = u'settings'

    WORK_MODE_DOWNLOAD, WORK_MODE_LIST, WORK_MODE_DISABLE,\
    WORK_MODE_ENABLE, WORK_MODE_ADD, WORK_MODE_DELETE, WORK_MODE_SENDMAIL = range(7)

    __WORK_MODE_CMDS = {'download':WORK_MODE_DOWNLOAD,
        'list':WORK_MODE_LIST,
        'disable':WORK_MODE_DISABLE,
        'enable':WORK_MODE_ENABLE,
        'add':WORK_MODE_ADD,
        'delete':WORK_MODE_DELETE,
        'sendmail':WORK_MODE_SENDMAIL}

    def __init__(self):
        # defaults
        self.settDownloads = DOWNLOAD_STREAMS

        self.mailFrom = None
        self.mailTo = []
        self.mailHost = None
        self.mailLogin = None
        self.mailPassword = None
        self.mailTLS = False
        self.mailCharset = 'utf-8'
        self.mailSubjectPrefix = u''
        self.mailSubjectSuffix = u''

        self.settLogToSyslog = False
        self.settLogDebug = False
        self.settDontSendMail = False
        self.settLocalConfig = False

        self.workDir = None
        self.feedDir = None
        self.feedListFileName = None
        self.configFileName = None
        self.logFileName = None

        self.workMode = None

        self.logger = None

    def load_settings(self):
        """Загрузка настроек"""

        if self.settLocalConfig:
            self.workDir = os.path.dirname(os.path.realpath(sys.argv[0]))
        else:
            self.workDir = os.path.join(os.path.expanduser('~'), u'.rssmailer')

        self.feedDir = os.path.join(self.workDir, u'feeds')
        self.feedListFileName = os.path.join(self.workDir, u'feeds.cfg')
        self.configFileName = os.path.join(self.workDir, u'config.cfg')
        self.logFileName = os.path.join(self.workDir, u'rssmailer.log')

        if not os.path.isdir(self.workDir):
            os.mkdir(self.workDir)

        if not os.path.isdir(self.feedDir):
            os.mkdir(self.feedDir)

        if not os.path.isfile(self.feedListFileName):
            #raise ValueError
            print(u'Warning! Feed list file "%s" is not found' % self.feedListFileName)

        if not os.path.isfile(self.configFileName):
            with open(self.configFileName, 'w+', encoding=IOENCODING) as f:
                f.write(CONFIG_EXAMPLE)

            raise Exception(u'config file "%s" is not found, created new one' % self.configFileName)

        cfg = CfgParser(self.configFileName)
        cfg.load()

        #
        self.settDownloads = cfg.get_int(self.CS_SETTINGS, u'downloads', DOWNLOAD_STREAMS, 1, 128)

        #
        self.mailFrom = cfg.get_str(self.CS_MAIL, u'from')
        self.mailTo = list(filter(None, map(lambda t: t.strip(), cfg.get_str(self.CS_MAIL, u'to', u'').split(u','))))

        self.mailHost = cfg.get_str(self.CS_MAIL, u'smtp')
        self.mailLogin = cfg.get_str(self.CS_MAIL, u'login')
        self.mailPassword = cfg.get_str(self.CS_MAIL, u'password')
        self.mailTLS = cfg.get_bool(self.CS_MAIL, u'tls')
        self.mailCharset = cfg.get_str(self.CS_MAIL, u'charset', IOENCODING)

        self.mailSubjectPrefix = cfg.get_str(self.CS_MAIL, u'subject-prefix').lstrip()
        self.mailSubjectSuffix = cfg.get_str(self.CS_MAIL, u'subject-suffix').rstrip()

        if not self.mailFrom:
            raise ValueError(u'config error: "from" addres not specified')

        if not self.mailTo:
            self.mailTo = [self.mailFrom]

        if not self.mailHost:
            raise ValueError(u'config error: SMTP address not specified')

        if not self.mailLogin:
            if self.mailPassword:
                self.mailLogin = self.mailFrom
        elif not self.mailPassword:
            raise ValueError(u'config error: have login but password is missing')

        #
        self.logger = init_logger(self)


    def process_command_line(self, argv):
        """Проверяет аргументы argv (см. sys.argv).
        Возвращает кортеж из двух элементов.
        В случае успешной обработки параметров:
        - первый элемент - список оставшихся необработанными параметров
          (для обработки где-то снаружи)
        - второй элемент - None
        В случае ошибки:
        - первый элемент - None,
        - второй элемент - строка с сообщением об ошибке."""

        if len(argv) < 2:
            return (None, u'''rssmailer [options] <command> [args]

download                - download feeds
list                    - list feeds from configuration file
disable f1 [...fN]      - disable downloading of feeds with specified numbers
enable f1 [...fN]       - enable downloading of feeds with specified numbers
add [url "title"]       - add feeds (more than one pair url/title may be specified)
delete f1 [...fN]       - remove specified feeds from configuration file
sendmail <parameters>   - send email message; parameters are: subject body [attach]
                          subject - message subject
                          body - message text
                          attach - list of file names

-s, --syslog            - copy log output (stderr) to syslog
-d, --debug             - log debug messages
-l, --local-config      - search for config and data files in the application
                          file directory (default location is ~/.rssmailer)
-m, --dont-send-mail    - don't send emails after feed downloading''')

        opts = []

        nargs = len(argv)
        #print(nargs)
        ixarg = 1
        while ixarg < nargs:
            if self.workMode is None:
                arg = argv[ixarg]
                #print('%d: %s' % (ixarg, arg))

                # пока не приехала команда - аргументы считаем настроечными опциями или командами
                if arg in self.__WORK_MODE_CMDS:
                    self.workMode = self.__WORK_MODE_CMDS[arg]
                elif arg in ('-s', '--syslog'):
                    self.settLogToSyslog = True
                elif arg in ('-d', '--debug'):
                    self.settLogDebug = True
                elif arg in ('-l', '--local-config'):
                    self.settLocalConfig = True
                elif arg in ('-m', '--dont-send-mail'):
                    self.settDontSendMail = True
                else:
                    return (None, u'unsupported command line parameter - "%s"' % arg)

                ixarg += 1
            else:
                opts = argv[ixarg:]
                break

        return (opts, None)


#
# test
#
if __name__ == '__main__':
    env = RSSMailerEnvironment()
    opts, es = env.process_command_line([None, 'download'])
    print('options:', opts)
    print('error:  ', es)
    #es = env.process_command_line(sys.argv)
    if es:
        exit(1)
    env.load_settings()
    env.logger.info('mode is %d' % env.workMode)
    print(env)
