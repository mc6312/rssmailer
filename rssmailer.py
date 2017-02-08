#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" rssmailer.py

    Copyright 2013-2017 mc6312

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>."""


RELEASE = '20170208-4'
APP_TITLE = 'RSSMailer'
APP_RELEASE = u'%s v%s' % (APP_TITLE, RELEASE)

import os.path, sys

from rssmailerconfig import *
from rssmailerfeeds import *
from rssmailersender import *
from rssmailerlogger import log_exception_info
from logging import shutdown as logging_shutdown


MAX_DESCRIPTION_CHARS = 512

def html_document(body):
    return u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=utf-8">
<style>
body { margin:10pt 2em 10pt 2em; background-color:#fff; font:10pt sans-serif }
h1, h2, h3 { width:100%; margin:0; font-weight:bold }
h3 { font-size: 105% }
h2 { font-size: 110% }
h1 { font-size: 115% }
div.nblk { margin-bottom:1em }
div.hdr { width:100% }
div.date { /*width:10%;*/ font-size:13pt; white-space: nowrap; display:inline }
div.link { /*width:90%;*/ font-size:13pt; display:inline }
div.desc { text-align:justify }
span.mark { border:1pt solid #fff; width:1ch }
</style>
<body>
""" + body + u'\n</body></html>'


def feed_to_html(feed):
    """Форматирование rssmailfeeds.RSSFeed.items в HTML"""

    msgbody = [u'<h2>%s</h2>\n' % feed.title]

    for item in feed.items:
        fdesc = HTMLText(u'<br>').to_text(item.description)
        if len(fdesc) > MAX_DESCRIPTION_CHARS:
            fdesc = fdesc[:MAX_DESCRIPTION_CHARS] + u'...'
        if not fdesc:
            fdesc = u'&nbsp;'

        if not item.pubDate:
            sdate = u'no date'
        else:
            sdate = u'%.2d.%.2d.%.4d %.2d:%.2d' % (item.pubDate.day,
                item.pubDate.month, item.pubDate.year,
                item.pubDate.hour, item.pubDate.minute)

        if not item.title:
            stitle = u'no title'
        else:
            stitle = item.title

        msgbody.append(u"""<div class="nblk"><div class="hdr"><div class="date">%s</div>
<div class="link"><a href="%s">%s</a></div></div>
<div class="desc">%s</div></div>""" % (sdate,
            item.link, stitle, fdesc))

    return html_document(u''.join(msgbody))


def download_feeds(env, feedSources):
    try:
        env.logger.info(u'* beginning downloads')

        feeds = load_feeds(env, feedSources)

        sendCount = 0

        if feeds:
            if env.settDontSendMail:
                ddir = os.path.join(os.path.dirname(os.path.abspath(__file__)), u'dbgout')
                if not os.path.isdir(ddir):
                    ddir = None
                emmode = u'simulation'
            else:
                ddir = None
                emmode = u'real'

            env.logger.info(u'sending emails (%s)' % emmode)

            dltime = time()
            try:
                for feed in feeds:
                    mbody = feed_to_html(feed)

                    msubj = u'%s%s (%d)%s' % (env.mailSubjectPrefix,
                                        feed.title, feed.newItems,
                                        env.mailSubjectSuffix)

                    if env.settDontSendMail:
                        if ddir:
                            with open(os.path.join(ddir, u'debug%.x.html' % hash(msubj)), 'w+', encoding=IOENCODING) as f:
                                f.write(mbody)

                        mailIsSent = False #!!! при фейковой отправке новость НЕ считаем прочитанной !!!
                    else:
                        mailIsSent = send_message(env, msubj, None, mbody)

                    if mailIsSent:
                        sendCount += 1
                        feed.save_guids()

            finally:
                dltime = time() - dltime

                if sendCount:
                    lmsg = u'mail transferring time is %d sec.' % dltime
                else:
                    lmsg = u'no mail sent'
                env.logger.info(lmsg)

        env.logger.info(u'* end downloads')

    except Exception as ex:
        log_exception_info(env, sys.exc_info(), str(ex))
        exit(1)

    return 0


def list_feeds(env, feedSources):
    if not feedSources:
        print('No feeds.')
        exit(1)

    COLS = 3

    nfeeds = len(feedSources)

    nrows = nfeeds // COLS

    if nfeeds % COLS:
        nrows += 1

    maxw = 0

    buf = []
    for ix, feed in enumerate(feedSources, 1):
        s = u'%3d|%s|%s' % (ix, 'Y' if feed.skip else 'N', feed.title)
        buf.append(s)

        w = len(s)
        if w > maxw:
            maxw = w

    print('|'.join(['No |S|Name%s' % (' ' * (maxw - 7))] * COLS))
    print('+'.join(['---+-+%s' % ('-' * (maxw - 3))] * COLS))

    ix = 0
    for row in range(nrows):
        print('   |'.join(map(lambda s: s.ljust(maxw, ' '), buf[ix:ix+COLS])))
        ix += COLS


def get_int_opts(opts, nmax):
    r = set()

    for o in opts:
        try:
            i = int(o)
        except ValueError:
            return (None, 'Parameter must be integer value')

        if i < 1 or i > nmax:
            return (None, 'Feed number out of range')
        r.add(i - 1)

    return (r, None)


def disable_feeds(env, feedSources, opts, flag):
    if not feedSources:
        print('No feeds. Nothing to disable')
        exit(1)

    nums, e = get_int_opts(opts, len(feedSources))
    if e:
        print(e)
        exit(1)

    for ix in nums:
        feedSources[ix].skip = flag

    feedSources.save(env)


def add_feeds(env, feedSources, opts):
    nfeeds = len(feedSources)

    def __add_feed(furl, ftitle):
        if feedSources.find_title(ftitle):
            return 0

        feedSources.append(RSSFeed(env, furl, ftitle, DOWNLOAD_TIMEOUT, False))
        return 1

    def __add_feeds():
        nopts = len(opts)
        nfeedadded = 0

        if nopts == 0:
            furl = input('Feed URL (empty line to cancel): ').strip()
            if not furl:
                return nfeedadded

        if nopts < 2:
            ftitle = input('Feed title (empty line to cancel): ').strip()
            if not ftitle:
                return nfeedadded

            nfeedadded += __add_feed(furl, ftitle)
        else:
            NPARAMS = 2
            ix = 0
            while nopts > 0:
                furl, ftitle = opts[ix:ix+NPARAMS]
                nopts -= NPARAMS

                nfeedadded += __add_feed(furl, ftitle)

            if nopts % NPARAMS:
                print('Invalid number of parameters (must be power of two)')

        return nfeedadded

    nfeedsadded = __add_feeds()

    if nfeedsadded:
        feedSources.save(env)

    print('%s feed(s) added' % ('no' if not nfeedadded else '%d' % nfeedsadded))


def delete_feeds(env, feedSources, opts):
    if not feedSources:
        print('No feeds. Nothing to delete')
        exit(1)

    nums, e = get_int_opts(opts, len(feedSources))
    #print(nums, e)
    if e:
        print(e)
        exit(1)

    for n in nums:
        feedSources[n].delete = True

    ix = 0
    ndel = 0
    while ix < len(feedSources):
        if feedSources[ix].delete:
            del feedSources[ix]
            ndel += 1
        else:
            ix += 1

    feedSources.save(env)

    print('%s feed(s) deleted' % ('no' if not ndel else '%d' % ndel))


def send_email(env, opts):
    nopts = len(opts)

    if nopts < 2:
        print('Required command line options is missing')
        return 1

    return(int(send_message(env, opts[0], opts[1], None, opts[2:])))


def main():
    env = RSSMailerEnvironment()
    #es = env.process_command_line([None, 'download', '--dont-send-mail', '--debug'])
    opts, es = env.process_command_line(sys.argv)
    if es:
        print(u'%s\n\n%s' % (APP_RELEASE, es))
        return 1

    try:
        env.load_settings()
    except Exception as ex:
        print(u'* Settings error: %s' % str(ex))
        return 1

    try:
        env.logger.info(APP_RELEASE)

        feedSources = RSSFeedSources()
        feedSources.load(env)

        if env.workMode == env.WORK_MODE_DOWNLOAD:
            download_feeds(env, feedSources)
        elif env.workMode == env.WORK_MODE_LIST:
            list_feeds(env, feedSources)
        elif env.workMode == env.WORK_MODE_DISABLE:
            disable_feeds(env, feedSources, opts, True)
        elif env.workMode == env.WORK_MODE_ENABLE:
            disable_feeds(env, feedSources, opts, False)
        elif env.workMode == env.WORK_MODE_ADD:
            add_feeds(env, feedSources, opts)
        elif env.workMode == env.WORK_MODE_DELETE:
            delete_feeds(env, feedSources, opts)
        elif env.workMode == env.WORK_MODE_SENDMAIL:
            return(send_email(env, opts))

        return 0

    finally:
        env.logger.info(u'%s exit' % APP_TITLE)
        logging_shutdown()


if __name__ == '__main__':
    exit(main())
