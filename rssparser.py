#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" rssparser.py

    Copyright 2013-2017 mc6312

    This file is part of RSSMailer (or other program).

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


""" Можно было бы весь модуль переделать под использование feedparser
    (т.к. он поддерживает кроме RSS еще и ATOM, и вообще нефиг
    велосипеды изобретать).
    Но feedparser страшно медленный, потому пока ну его фпень."""


from xml.sax.handler import ContentHandler as SAXContentHandler
from collections import namedtuple

from re import compile as re_compile, UNICODE as RE_UNICODE
from datetime import datetime

# RSS RFC-2822 date format: Tue, 2 Jul 2013 11:49:23 +0400
rx_rfc2822time = re_compile(r'\w+, (\d+ \w+ \d+ \d+:\d+)', RE_UNICODE)

# ATOM date format: 2014-06-24T16:11:28+02:00
rx_atomtime = re_compile(r'(\w+-\w+-\w+T\w+:\w+):\w+(\+\w+:\w+)?', RE_UNICODE)


def parse_time(s):
    """Жрет строку с датой/временем в формате RFC 2822 или ATOM,
    возвращает datetime.datetime (только дату и время без секунд).
    Если строка в неправильном формате - вернет текущие дату/время, ибо
    падать всей качалке из-за криворуких уеб-программистов западло.
    Timezone пока не поддерживается."""

    r = rx_rfc2822time.match(s)
    if r:
        return datetime.strptime(r.group(1), '%d %b %Y %H:%M')

    r = rx_atomtime.match(s)
    if r:
        return datetime.strptime(r.group(1), '%Y-%m-%dT%H:%M')

    #raise ValueError, u'"%s" - string is not RFC 2822 timestamp' % s
    return datetime.now()


#print parse_time(u'2014-06-24T16:11:28+02:00')
#exit(1)



class RSSHandler(SAXContentHandler):
    # RSS
    TAG_ITEM = u'item'
    TAG_GUID = u'guid'
    TAG_LINK = u'link'
    TAG_TITLE = u'title'
    TAG_DATE = u'pubDate'
    TAG_DESC = u'description'

    # грязный хак для ATOM
    TAG_ATOM_ITEM = u'entry'
    TAG_ATOM_GUID = u'id'
    TAG_ATOM_DATE = u'updated'
    TAG_ATOM_DESC = u'summary'

    FLD_GUID = 0
    FLD_LINK = 1
    FLD_TITLE = 2
    FLD_DATE = 3
    FLD_DESC = 4

    rss_item = namedtuple('rss_item', (TAG_GUID, TAG_LINK, TAG_TITLE, TAG_DATE, TAG_DESC))

    FIELDMAP = {TAG_GUID:TAG_GUID, TAG_ATOM_GUID:TAG_GUID,
        TAG_LINK:TAG_LINK, TAG_TITLE:TAG_TITLE, TAG_DATE:TAG_DATE, TAG_ATOM_DATE:TAG_DATE,
        TAG_DESC:TAG_DESC, TAG_ATOM_DESC:TAG_DESC}
    FIELDS = {TAG_GUID:FLD_GUID, TAG_LINK:FLD_LINK, TAG_TITLE:FLD_TITLE,
        TAG_DATE:FLD_DATE, TAG_DESC:FLD_DESC}
    TEXT_FIELDS = {FLD_GUID:True, FLD_LINK:True, FLD_TITLE:True, FLD_DATE:False, FLD_DESC:True}

    def __init__(self):
        SAXContentHandler.__init__(self)

        self.isItem = False
        self.curField = None

        self.curItem = None

    def reset_cur_item(self):
        self.curItem = [u''] * len(self.rss_item._fields)

    def startElement(self, name, attrs):
        if name == self.TAG_ITEM or name == self.TAG_ATOM_ITEM:
            self.isItem = True
            self.reset_cur_item()
        elif self.isItem:
            if name in self.FIELDMAP:
                name = self.FIELDMAP[name]
                if name in self.FIELDS:
                    self.curField = self.FIELDS[name]
            else:
                self.curField = None

    def endElement(self, name):
        if name == self.TAG_ITEM or name == self.TAG_ATOM_ITEM:
            self.isItem = False

            # текстовые поля чистим от лишних пробелов в начале и в конце
            for fi in self.TEXT_FIELDS:
                if self.TEXT_FIELDS[fi]:
                    self.curItem[fi] = self.curItem[fi].strip()

            # грязный хак для ixbt.com и прочих кривых
            if not self.curItem[self.FLD_GUID]:
                self.curItem[self.FLD_GUID] = self.curItem[self.FLD_LINK]

            self.flush_item(self.rss_item(*self.curItem))

    def skippedEntity(self, name):
        print(u'- %s -' % name)

    def characters(self, content):
       if (self.isItem) and (self.curField != None):
            if self.TEXT_FIELDS[self.curField]:
                # содержимое текстовых полей добавляем к текущему
                # содержимому без изменения -
                # оно обрабатывается в endElement
                # и снаружи вызовов RSSHandler
                self.curItem[self.curField] += content
            else:
                content = content.strip()
                if content:
                    if self.curField == self.FLD_DATE:
                        #print content
                        content = parse_time(content)

                    self.curItem[self.curField] = content

    def flush_item(self, item):
        raise NotImplementedError(u'RSSHandler.flush_item()')

#
# test
#
if __name__ == '__main__':
    import urllib.request
    from xml.sax import make_parser

    class TestHandler(RSSHandler):
        def resolveEntity(self, publicId, systemId):
            pass #print publicId, systemId
            return u''
        def skippedEntity(self, name):
            pass #print u'- %s -' % name
        def unparsedEntityDecl(self, name, publicId, systemId, ndata):
            pass #print name, publicId, systemId, ndata
        def flush_item(self, item):
            #print('guid', item.guid)
            print('link', item.link)
        """def startElement(self, name, attrs):
            if name == u'item':
                print 'start of "%s"' % name, attrs.getNames()"""
        """def endElement(self, name):
            if name == u'item':
                print 'end of "%s"' % name"""
        def error(self, ex):
            print('error:', ex)

        def fatalError(self, ex):
            print('fatal:', ex)



    #url = 'http://ixbt.com/export/hardnews.rss'
    url = 'http://habrahabr.ru/rss/'
    #url = 'http://ru_d70.livejournal.com/data/rss'

    parser = make_parser()
    handler = TestHandler()
    parser.setContentHandler(handler)
    parser.setEntityResolver(handler)
    parser.setErrorHandler(handler)

    rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}) # дабы сайты не возбухали на робота
    f = urllib.request.urlopen(rq, timeout=10)
    """try:
        s = f.read().decode('utf-8')
        print(s)
    finally:
        f.close()"""
    parser.parse(f)
