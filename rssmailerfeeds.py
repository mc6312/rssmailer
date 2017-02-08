#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" rssmailerfeeds.py

    Copyright 2013-2017 mc6312

    This file is part of RSSMailer.

    RSSMailer is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    RSSMailer is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with RSSMailer.  If not, see <http://www.gnu.org/licenses/>."""


from urllib.parse import urlsplit
from urllib.request import urlopen, URLError
from http.client import HTTPException
from socket import error as socket_error
from html.parser import HTMLParser
from xml.sax import parse as xml_parse, SAXParseException
import rssparser
from configparser import RawConfigParser
import re
from time import time, sleep
import subprocess
import threading
from tempfile import NamedTemporaryFile
from hashlib import md5
from collections import namedtuple

from rssmailerconfig import *


MAX_FEED_FNAME_SIZE = 64
_FNAME_HASH_EDGE = MAX_FEED_FNAME_SIZE - 8



def url_to_file_name(url):
    """Преобразует URL в строку, состоящую только из символов ASCII,
    допустимых для имен файлов, и не длиннее MAX_FEED_FNAME_SIZE символов"""

    def url_char(c):
        o = ord(c)

        if (c not in '.-_=@') and (not c.isalnum()):
            return u'_'
        elif (o >= 33) and (o <= 127):
            return c
        else:
            return u'%x' % o

    p = urlsplit(url)

    s = u''.join(map(url_char, u''.join(filter(None, (p.netloc, p.path, p.query)))))
    if len(s) > MAX_FEED_FNAME_SIZE:
        s = s[:_FNAME_HASH_EDGE] + u'%x' % hash(s)

    return s


def download_url(url, timeout, fstdout, fstderr):
    """Загрузка данных с указанного адреса.

    url     - адрес
    timeout - таймаут в секундах, по превышении которого закачка должна прерываться
    fstdout - файловый объект для скачиваемых данных
    fstderr - файловый объект для прочего вывода внешнего процесса
    Для загрузки вызывается внешний процесс, выдающий данные в stdout.

    В случае успеха ф-я возвращает None, иначе - строку с сообщением
    об ошибке."""

    # если когда-нито будет возможность настройки на качалку, отличную от wget
    # это нужно будет вынести в конфиг
    WGET_ERRORS = {1:u'error',
        2:u'parameter parse error',
        3:u'file I/O error',
        4:u'network failure',
        5:u'SSL verification failure',
        6:u'username/password authentication failure',
        7:u'protocol error',
        8:u'server issued an error response'}

    # пока приколочу wget гвоздями. потом, возможно, сделаю настройку (для curl или еще чего)
    try:
        r = subprocess.call([u'wget', u'-q', u'--timeout', u'%d' % timeout, u'--tries', u'1', u'-O', u'-', url], stdout=fstdout, stderr=fstderr)
        if r:
            es = u'wget error %d' % r

            if r in WGET_ERRORS:
                es += u': %s' % WGET_ERRORS[r]

            return es
    except Exception as ex:
        return u'subprocess.call() error %s' % str(ex)

    return None



def text_hash(txt):
    """Нормализует юникодную строку txt (удаляя всё, кроме букв и цифр,
    и приводя к нижнему регистру), считает от нее md5 и возвращает дайджест."""

    # utf-8 потому, что hashlib жреть только 8-битные строки (точнее даже, байты)
    txt = txt.strip()
    return u'' if not txt else md5((u''.join(filter(lambda c: c.isalnum(), txt))).lower().encode('utf-8', errors='replace')).hexdigest()


class RSSFeed(rssparser.RSSHandler):
    """Разбор ленты RSS, проверка на уникальность записей и т.п.
    Стараниями разных [censored], генерящих кривые ленты, приходится проверять
    уникальность не только поля guid, но и link."""

    recordids = namedtuple('recordids', 'link dhash')
    # link - ссылка на запись из ленты
    # dhash - хэш описания записи

    def __init__(self, env, url, title, timeout, skip=False):
        rssparser.RSSHandler.__init__(self)

        self.url = url

        fbasename = url_to_file_name(url)
        self.guidListFileName = os.path.join(env.feedDir, fbasename + u'.guids')

        # данные для проверки на уникальность записи
        # словарь - для загрузки-сохранения
        # ключи - guid'ы, значения - экземпляры recordids
        self.guids = {}
        # и отдельные множества - для проверки (чтоб не лазать вручную в содержимое словаря)
        self.links = set()
        # т.к. разные жопорукие постят в ленты одинаковые псто с разными
        # guid'ами и ссылками, буду проверять еще и по хэшу содержимого
        self.hashes = set()

        self.items = []
        self.newItems = 0
        self.title = title
        self.timeout = timeout
        self.skip = skip
        self.delete = False # костыль для удалятора в осн. модуле

        self.dltime = 0.0
        self.error = None

    def load_guids(self):
        """Файл истории событий. В нем хранятся guid и link.
        Для совместимости с предыдущей версией при загрузке проверяется
        кол-во полей в файле."""

        self.guids.clear()
        self.links.clear()
        self.hashes.clear()

        if os.path.isfile(self.guidListFileName):
            with open(self.guidListFileName, 'r', encoding=IOENCODING) as f:
                for s in f:
                    s = s.strip()
                    if not s:
                        continue

                    # не уверен, что guid в rss не может содержать ";", но пока плевать
                    s = list(map(lambda t: t.strip(), s.split(u';')))
                    ls = len(s)

                    s_guid = s[0]

                    # link
                    if ls > 1 and s[1] and s[1] != s_guid:
                        s_link = s[1].lower() # url'ы вроде бы регистронезависимы?
                        self.links.add(s_link)
                    else:
                        s_link = u''

                    # description hash
                    if ls > 2 and s[2]:
                        s_dhash = s[2]
                        self.hashes.add(s_dhash)
                    else:
                        s_dhash = u''

                    # guid
                    self.guids[s_guid] = self.recordids(s_link, s_dhash)

    def save_guids(self):
        with open(self.guidListFileName, 'w+', encoding=IOENCODING) as f:
            for guid in self.guids:
                r = self.guids[guid]
                f.write(u'%s;%s;%s\n' % (guid, r.link, r.dhash))

    def flush_item(self, item):
        dhash = text_hash(item.description)

        # проверка на уникальность поста
        # не хочу громоздить if ... в одну строку, так нагляднее

        if item.guid in self.guids:
            return

        # возможно, не совсем правильно, т.к. в кривых лентах могут и линки разные при одинаковых гуидах оказаться...
        if item.link in self.links:
            return

        if dhash and dhash in self.hashes:
            return

        self.items.append(item)

        self.guids[item.guid] = self.recordids(item.link.lower() if item.link and item.link != item.guid else u'', dhash)
        self.links.add(item.link)

        if dhash:
            self.hashes.add(dhash)

        self.newItems += 1

    def download(self):
        """Засасывает ленту, отбрасывая ранее
        загруженные элементы с помощью списка guid'ов"""

        try:
            self.load_guids()
            del self.items[:]
            self.newItems = 0

            dltime0 = time()
            try:
                # засасывать будем с помощью внешнего процесса
                # а именно wget

                # заставляем wget молча срать в stdout, который перенаправлен во временный файл
                with NamedTemporaryFile() as tempf:
                    with open(os.devnull, 'w') as nulldev:
                        #print('downloading from', self.url)
                        es = download_url(self.url, self.timeout, tempf, nulldev)
                        #print('end download:', es)
                        if es:
                            self.error = es
                            return False

                    tempf.flush()
                    tempf.seek(0)

                    # скармливаем имя, а не объект - иначе на питоне 3.4 парсер может глупо икнуть
                    xml_parse(tempf.name, self)

            finally:
                self.dltime = time() - dltime0

            #self.save_guids()
            #не будем теперь гуиды сохранять отседова. будем только после успешного отсыла почты.

            self.error = None
            return True

        #except (SAXParseException, OSError), msg:
        except Exception as ex:
            # гребём всё
            self.error = str(ex)
            #print(self.error)
            return False


class RSSLoaderThread(threading.Thread):
    def __init__(self, feed):
        threading.Thread.__init__(self)
        self.feed = feed
        self.error = None

    def run(self):
        # здесь - никаких логов, ибо в сочетании с многопоточностью получается хня
        try:
            #print('begin ', self.feed.url)
            self.feed.download()
            #print('end', self.feed.url)
        except Exception as ex:
            self.error = str(ex)


def load_feeds(env, feeds):
    """Грузит все ленты из списка feeds пачками по maxdownloads.
    Возвращает список успешно загруженных."""

    feeds = list(filter(lambda f: not f.skip, feeds))

    if not feeds:
        return []

    nfeeds = len(feeds)
    env.logger.info(u'downloading %d feed(s)' % nfeeds)

    fnumfmt = u'%%.%1dd/%d' % (len(str(nfeeds)), nfeeds)

    dltime = time()
    try:
        fix = 0
        while nfeeds:
            ndlds = nfeeds if nfeeds < env.settDownloads else env.settDownloads
            #print ndlds

            # стартуем ndlds загрузок
            #print 'loading %d feeds' % ndlds

            loaders = []
            fbundle = feeds[fix:fix+ndlds]

            #print('bundle of %d downloads' % ndlds)

            for feed in fbundle:
                t = RSSLoaderThread(feed)
                loaders.append(t)
                t.start()

            # ждем, пока все не отработают.
            # тут можно получить бесконечный цикл, надо че-то придумать
            for thrd in loaders:
                if t.is_alive():
                    t.join()
                else:
                    sleep(0.1)
            #while filter(lambda t: t.is_alive(), loaders):
            #    sleep(0.1)

            # какаем в лог результатами текущей порции закачек
            for fsubix, feed in enumerate(fbundle):
                fsubix += 1
                feedn = u'feed %s "%s"' % (fnumfmt % (fix + fsubix), feed.title)

                if feed.error:
                    env.logger.error(u'error downloading %s - %s' % (feedn, feed.error))
                else:
                    env.logger.debug(u'%s downloaded by %d sec., %s new(s)' % (feedn, feed.dltime, (u'%d' % feed.newItems) if feed.newItems else u'no'))

            nfeeds -= ndlds
            fix += ndlds

    finally:
        dltime = time() - dltime

        env.logger.info(u'total download time is %d sec.' % dltime)

    ret = list(filter(lambda f: f.error is None and f.newItems, feeds))

    env.logger.info(u'feeds with news: %d' % len(ret))

    return ret


class RSSFeedSources(list):
    CV_SKIP = u'skip'
    #CO_SKIP = set((u'yes', u'true'))
    CV_URL = u'url'
    CV_TIMEOUT = u'timeout'

    def load(self, env):
        """Разбирает файл с именем feedListFileName, возвращает
        список экземпляров RSSFeed.
        Неправильные записи игнорируются, повтор URL отбрасывается.
        Используется список, а не словарь или set, т.к. нужно сохранять
        тот же порядок записей, что в файле."""

        env.logger.debug(u'loading feed list from %s' % env.feedListFileName)

        srcs = []
        urls = set()

        cfg = CfgParser(env.feedListFileName)
        cfg.load()

        for ftitle in cfg.sections():
            fskip = cfg.get_bool(ftitle, self.CV_SKIP)

            ftimeout = cfg.get_int(ftitle, self.CV_TIMEOUT, DOWNLOAD_TIMEOUT, DOWNLOAD_TIMEOUT_MIN, DOWNLOAD_TIMEOUT_MAX)

            furl = cfg.get_str(ftitle, self.CV_URL).strip()
            if not furl:
                env.logger.error(u'no URL specified in section "%s" of file "%s"' % (ftitle, env.feedListFileName))

            if furl in urls:
                continue

            feed = RSSFeed(env, furl, ftitle, ftimeout, fskip)
            self.append(feed)

    def save(self, env):
        env.logger.debug(u'saving feed list to %s' % env.feedListFileName)

        cfg = CfgParser(env.feedListFileName)

        for feed in self:
            if not cfg.has_section(feed.title):
                cfg.add_section(feed.title)

            cfg.set(feed.title, self.CV_URL, feed.url)
            cfg.set(feed.title, self.CV_SKIP, 'yes' if feed.skip else 'no')

            if feed.timeout != DOWNLOAD_TIMEOUT:
                cfg.set(feed.title, self.CV_TIMEOUT, str(feed.timeout))

        cfg.save()

    def find_title(self, title):
        title = title.lower()

        for feed in self:
            if feed.title.lower == title:
                return feed


class HTMLText(HTMLParser):
    """Вспомогательный класс для удаления разметки из HTML"""

    EOLTAGS = set((u'br', u'p'))

    def __init__(self, lbchr=u'\n'):
        """Необязательный параметр lbchr содержит строку,
        вставляемую в обработанный текст вместо символа перевода строки.
        По умолчанию - как раз символ перевода строки."""

        HTMLParser.__init__(self)
        self.text = u''
        self.linebreakchar = lbchr

    def handle_starttag(self, tag, attrs):
        self.handle_startendtag(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.EOLTAGS:
            self.text += u'\n'

    def handle_data(self, data):
        self.text += data

    def to_text(self, html):
        """Разбирает html, возвращает чистый текст.
        Символы перевода строки заменяются self.linebreakchar."""

        # чистим от HTML-разметки
        self.reset()
        self.feed(html)

        #print self.text

        # чистим от лишних переводов строки
        t = filter(None, self.text.split(u'\n'))
        #print t

        # чистим от лишних пробелов
        return self.linebreakchar.join(map(lambda s: u' '.join(s.split()), t))


if __name__ == '__main__':
    import sys
    print(u'[debug]\n')
    env = RSSMailerEnvironment()
    env.process_command_line(sys.argv)
    env.load_settings()
    srcs = RSSFeedSources()
    srcs.load(env)
    #print(srcs)
    #exit(0)

    feeds = load_feeds(env, srcs)
    #print(feeds)
    #print('%d with news' % len(feeds))

    srcs[0].download()
    print(srcs[0].dltime)
    """for fsrc in srcs:
        fsrc.load_guids()
        print fsrc.title
        print fsrc.url
        print fsrc.filters
        print fsrc.guids
        print fsrc.download()
        #print fsrc.newItems"""
