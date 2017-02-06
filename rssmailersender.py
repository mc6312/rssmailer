#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" rssmailersender.py

    Copyright 2013-2016 mc6312.livejournal.com

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

from smtplib import SMTP, SMTPException
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from datetime import datetime
from os.path import isfile, basename
from os import stat

from rssmailerconfig import *


def send_message(env, subject, textbody, htmlbody, attachfiles=[]):
    """Отправляет письмо по адресам, указанным в настройках env
    (см. rssmailerconfig).
    subject     - строка с заголовком письма
    textbody    - plain text - содержимое письма (м.б. None)
    htmlbody    - HTML - содержимое письма (м.б. None)
    attachfiles - список имен файлов, которые следует приложить к письму
    Возвращает булевское значение с результатом отправки."""

    env.logger.debug(u'preparing to send email')
    #
    # создаем сообщение в формате MIME
    #
    msg = MIMEMultipart()
    msg.set_charset(env.mailCharset)
    msg['Subject'] = subject
    msg['From'] = env.mailFrom
    msg['To'] = u', '.join(env.mailTo)
    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

    if textbody:
        msg.attach(MIMEText(textbody.encode(env.mailCharset, 'replace'), 'plain', env.mailCharset))

    if htmlbody:
        msg.attach(MIMEText(htmlbody.encode(env.mailCharset, 'replace'), 'html', env.mailCharset))

    for attachfname in attachfiles:
        if not isfile(attachfname):
            env.logger.warning(u'can not attach missing file "%s"' % attachfname)
            continue

        if stat(attachfname).st_size == 0:
            env.logger.warning(u'can not attach empty file "%s"' % attachfname)
            continue

        with open(attachfname, 'rb') as fp:
            fd = fp.read()

        payload = MIMEApplication(fd)
        payload['Content-Disposition'] = 'attachment; filename="%s"' % basename(attachfname)
        msg.attach(payload)

    #
    # отправляем
    #
    try:
        env.logger.debug(u'trying to send email over %s' % env.mailHost)
        smtp = SMTP(env.mailHost)#, None, None, 1)

        smtp.set_debuglevel(0)

        #smtp.connect()
        if env.mailTLS:
            env.logger.debug(u'trying to start TLS')
            smtp.starttls()

        if env.mailPassword:
            env.logger.debug(u'authentication')
            smtp.login(env.mailLogin, env.mailPassword)

        env.logger.debug(u'sending email from %s to %s' % (env.mailFrom, env.mailTo))
        smtp.sendmail(env.mailFrom, env.mailTo, msg.as_string())

        smtp.quit()
        env.logger.debug(u'email sent')
        return True

    except SMTPException as ex:
        env.logger.error(u'SMTP error: %s' % str(ex))
        return False

#
# test
#
if __name__ == '__main__':
    env = RSSMailerEnvironment()
    env.process_command_line([None, '--debug'])#sys.argv)
    env.load_settings()
    print(send_message(env, u'Test', u'test жепь ебрило text', None, ['README']))
