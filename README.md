# RSSMailer никакой версии

Раздается кому хошь под лицензией GPL v3.
Автор никому ничего не должен (кроме указанного в GPL) и всех видал в гробу.


## Что умеет

Скачивать RSS-ленты и отправлять содержимое в сокращённом виде на адрес
email, указанный в настройках.
Предполагается, что это поделие будет жить под аккаунтом простого юзера
в небольшой виртуалке (или контейнере, или даже отдельной мелкой железке)
и запускаться кроном.

Умеет простейшую SMTP-аутентификацию и TLS.
SSL на данный момент не поддерживается.


## Что хочет

- немного дискового пространства (для БД скачанных лент) и памяти
  (на 512 Мб полёт нормальный);
- Python 3.x (3.4.х или новее - на более старых не тестировалось, но
  может и заработать);
- GNU Wget
- Linux (всё равно какое, лишь бы с установленным питоном);
  повышенные права, иксы и т.п. не требуются;
  теоретически может заработать и под Windows/MacOS/*BSD, но это не
  проверялось и не гарантируется
- открытый на выход порт SMTP (и/или TLS, если оное включено в настройках).


## Как запускать

Запускать следует rssmailer.py (если оно в виде рассыпухи файлов), либо
rssmailer.pyz (если оно одним шматком).

### Параметры командной строки:

    download                - основной режим: скачать ленты, отправить почту
    list                    - показать список лент из файла настроек
    disable f1 [...fN]      - запретить скачивание лент с указанными номерами
    enable f1 [...fN]       - разрешить скачивание лент с указанными номерами
    add [url "title"]       - добавить одну или несколько лент:
                              указываются пары аргументов url "название"
    delete f1 [...fN]       - удалить из настроек ленты с указанными номерами
    sendmail <parameters>   - отправить письмо по адресу, указанному в настройках;
                              параметры: subject body [attach]
                              subject   - заголовок сообщения
                              body      - текст сообщения
                              attach    - список файлов, которые нужно
                                          приложить к сообщению (необязательный
                                          параметр)

    -s, --syslog            - дублировать вывод лога в syslog (без этого
                              лог выводится только в обычный файл)
    -d, --debug             - выводить в лог отладочные сообщения
    -l, --local-config      - если указано, все файлы и каталоги поделия
                              находятся в том же каталоге, где и rssmailer.py[z],
                              иначе (по умолчанию) данные хранятся в каталоге
                              ~/.rssmailer
    -m, --dont-send-mail    - не отправлять почту, только имитировать отправку

По команде download поделие прошерстит RSS-ленты (см. далее) и отправит
свежие новости по указанным в конфиге адресам, по письму на каждую ленту.
БД уже скачанных новостей лежат в подкаталоге feeds, по отдельному файлу
на каждую ленту.


## Список лент

Список лент хранится в файле feeds.cfg, формат файла аналогичен виндовым
ini'шникам и должен быть таким:

    [Название ленты 1]
    url=адрес ленты
    timeout=секунды
    skip=yes|no

    [Название ленты N]
    url=адрес ленты

Название ленты (оно же название секции списка лент) используется в качестве
заголовка отправляемого письма.

Параметр "skip" - необязательный, по умолчанию равен "no". Если этот параметр
указан и равен "yes", соотв. лента не скачивается.

Параметр "timeout" - необязательный, по умолчанию 10 секунд. Максимальное
время ожидания скачивания, дабы не ломиться бесконечно на внезапно сдохший
сайт.


## Файл настроек

Настройки хранятся в файле config.cfg.
Если не существует - при запуске rssmailer.py[z] создаётся "рыба" файла
настроек, после чего работа качалки завершается - изволь править конфиг.

### Образец файла настроек

    [settings]
    ; количество одновременных загрузок (если не указано - 10)
    downloads = 10

    ; отправлять ли письма об ошибках скачивания лент
    ; no/yes    - нет/да
    mail-errors = yes

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


ВНИМАНИЕ!
- Так как пароль от почтового аккаунта отправителя хранится в конфиге
  в открытом виде, советую завести для отправки отдельную мыльницу,
  не используемую больше ни для чего.
- Все сообщения об ошибках валятся в лог (см. описание параметра -s).
