#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" rssmailerlogger.py

    Copyright 2013-2019 mc6312

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


import logging, logging.handlers
from traceback import format_exception, format_exception_only


def log_exception_info(env, nfo, msg = None):
    if nfo[0] is SystemExit:
        return # ибо нефиг, это штатная ситуация, а не ошибка

    if not msg:
        msg = u'Error occured'

    env.logger.error(u'* %s' % msg)

    def write_log(dumps, logproc):
        for dblk in dumps:
            for dstr in dblk.splitlines():
                logproc(dstr)

    #logger.info(u'cfgDebug=%s' % str(cfgDebug))

    if env.settLogDebug:
        #print format_exception(nfo[0], nfo[1], nfo[2])
        write_log(format_exception(nfo[0], nfo[1], nfo[2]), lambda s: env.logger.debug(s))
        env.logger.debug(u'* end exception message')
    else:
        write_log(format_exception_only(nfo[0], nfo[1]), lambda s: env.logger.error(s))


def init_logger(env):
    logger = logging.getLogger()

    logFormatStr = u'rssmailer.%(module)s: %(levelname)s - %(message)s'

    if env.settLogToSyslog:
        loghdr = logging.handlers.SysLogHandler('/dev/log', logging.handlers.SysLogHandler.LOG_USER)
        loghdr.setFormatter(logging.Formatter(logFormatStr))
        logger.addHandler(loghdr)

    # file logger
    loghdr = logging.FileHandler(env.logFileName)
    loghdr.setFormatter(logging.Formatter(u'%(asctime)s  ' + logFormatStr))
    logger.addHandler(loghdr)

    logger.setLevel(logging.DEBUG if env.settLogDebug else logging.INFO)

    return logger

#
# test
#
if __name__ == '__main__':
    import sys
    from rssmailerconfig import RSSMailerEnvironment
    env = RSSMailerEnvironment()
    env.process_command_line([None, '--debug'])
    env.load_settings()

    env.logger.debug('moo')
    env.logger.error('test')
    try:
        raise ValueError('test exception')
    except:
        log_exception_info(env, sys.exc_info())
