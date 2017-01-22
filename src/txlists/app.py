
import json
import os

import html5lib
from email.utils import parsedate_tz, mktime_tz, parseaddr
from email.parser import Parser
import mailbox

import datetime

from twisted.web.template import tags, slot
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python.filepath import FilePath
from twisted.internet.task import cooperate
from twisted.logger import Logger

from klein import Klein, Plating
from klein.storage.sql import authorizer_for, open_session_store, tables
from klein._session import requirer

import treq

from sqlalchemy import Column, String, Integer
from sqlalchemy.sql.functions import max as Max
from sqlalchemy.sql.expression import Select
from sqlalchemy import desc

import attr

page = Plating(
    defaults={
        "title": "hello!"
    },
    tags=tags.html(
        tags.title("Twisted List Manager - ", slot("title")),
        tags.body(
            slot(Plating.CONTENT)
        )
    )
)

import hashlib, hmac

def mgverify(api_key, token, timestamp, signature):
    hmac_digest = hmac.new(key=api_key,
                           msg='{}{}'.format(timestamp, token),
                           digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(unicode(signature), unicode(hmac_digest))

def normalizeDate(string):
    """
    Convert a date stamp found in an email into a UTC timestamp.
    """
    data = parsedate_tz(string)
    if data is None:
        return None
    else:
        return mktime_tz(data)


archives = FilePath("/legacy-mailman-archive")

globalIngestionList = {
    # map list-name to cooperator task
}

def extractPathInfo(fp):
    """
    
    """
    strumber = fp.basename().split(".")[0]
    number = int(strumber)
    content = html5lib.parse(fp.getContent(),
                             namespaceHTMLElements=False)
    [date] = content.findall("./body/i")
    sender = content.find("./body/a").text.replace(" at ", "@").strip()
    return number, sender, normalizeDate(date.text)



@inlineCallbacks
def enbatch(batchProcessor, sequence, size=100):
    """
    
    """
    batch = []
    count = 0
    for element in sequence:
        batch.append(element)
        if len(batch) >= size:
            count += 1
            yield batchProcessor(count, batch)
            batch = []
    count += 1
    if batch:
        yield batchProcessor(count, batch)



@attr.s
class IngestionTask(object):
    """
    
    """
    _archiveDir = attr.ib()
    _dataStore = attr.ib()
    _messageTable = attr.ib()
    _currentStatus = attr.ib(default=attr.Factory(list))
    _currentErrors = attr.ib(default=attr.Factory(list))
    _log = Logger()

    def statusify(self, anStatus, error=False):
        """
        
        """
        l = self._currentStatus if not error else self._currentErrors
        l.append(anStatus)
        if len(l) > 10:
            l.pop(0)

    def report(self):
        """
        
        """
        return u"\n".join(self._currentStatus + [u""] + self._currentErrors)


    def go(self):
        """
        
        """
        def setErrorStatus(failure):
            self.statusify(failure.getTraceback().decode("charmap"), True)
            self._log.failure('doing batch work', failure)
        def oneMappingBatch(count, paths):
            @self._dataStore.sql
            @inlineCallbacks
            def do(txn):
                for path in paths:
                    counter, sender, received = extractPathInfo(path)
                    yield txn.execute(
                        self._messageTable.insert().values(
                            list=self._archiveDir.basename(),
                            counter=counter,
                            sender=sender,
                            received=received,
                        )
                    )
                self.statusify(u'mapped {} message counter batches'
                               .format(count))
            return do.addErrback(setErrorStatus)

        def oneContentsBatch(count, messages):
            @self._dataStore.sql
            @inlineCallbacks
            def do(txn):
                self._log.info("starting message batch")
                for message in messages:
                    m = self._messageTable
                    self._log.info("message: {m}", m=message['subject'])
                    rowcount = (yield (yield txn.execute(
                        m.update(
                            (m.c.list == self._archiveDir.asTextMode()
                             .basename()) &
                            (m.c.sender == parseaddr(message['From'])[1]
                             .decode('charmap')) &
                            (m.c.received == normalizeDate(message['Date']))
                        ).values(
                            # xxx py3: no as_bytes on py2.
                            contents=message.as_string().decode('charmap'),
                            id=message['message-id'].decode('charmap'),
                            subject=message['subject'].decode('charmap'),
                        )
                    )).rowcount)
                    self._log.info("message: {m} updated {n} rows",
                                   m=message['subject'], n=rowcount)
                self.statusify(u'loaded {} message batches'.format(count))
            return do.addErrback(setErrorStatus)

        def justKeepIngesting():
            yield enbatch(
                oneMappingBatch,
                (
                    eachPath for eachPath in self._archiveDir.walk()
                    if (
                            len(eachPath.basename().split(".")) == 2
                            and eachPath.basename().endswith(".html")
                            and eachPath.basename().startswith("0")
                    )
                )
            )
            self.statusify(u'mapping done!')
            mbox = self._archiveDir.basename() + '.mbox'
            yield enbatch(
                oneContentsBatch,
                mailbox.mbox(self._archiveDir.sibling(mbox).child(mbox).path)
            )
            self.statusify(u'loaded everything!')
        self._task = cooperate(justKeepIngesting())


@attr.s
class ArchiveMessage(object):
    """
    A message loaded from an archive.
    """
    _messageRow = attr.ib()

    def subject(self):
        """
        The subject of the message; unicode.
        """
        return self._messageRow['subject']

    def body(self):
        """
        Extract a simple text part; unicode.
        """
        message = Parser().parsestr(self._messageRow["contents"]
                                    .encode("charmap"))
        for part in message.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True).decode(
                    part.get_content_charset()
                )
                break
        else:
            body = u'no body found'
        return body


@attr.s
class MessageIngestor(object):
    _dataStore = attr.ib()
    _messageTable = attr.ib()
    _replyTable = attr.ib()

    def someMessagesForList(self, listID):
        @self._dataStore.sql
        @inlineCallbacks
        def query(txn):
            m = self._messageTable
            resultProxy = yield txn.execute(m.select(m.c.list == listID)
                                            .limit(10))
            returnValue((yield resultProxy.fetchall()))
        return query

    def monthsForList(self, listID):
        @self._dataStore.sql
        @inlineCallbacks
        def monthsQuery(txn):
            m = self._messageTable
            l = m.c.list == listID
            monthsMessagesRows = []
            startTime = (
                yield (yield txn.execute(Select([Max(m.c.received)], l)))
                .fetchall()
            )[0][0]
            # start at the end month, go backwards
            thisDateTime = datetime.datetime.utcfromtimestamp(startTime)
            for ignored in range(400):
                thisTimestamp = (
                    thisDateTime - datetime.datetime.utcfromtimestamp(0)
                ).total_seconds()
                expr = Select(m.c, l & (m.c.received <= thisTimestamp))
                expr = expr.order_by(desc(m.c.received))
                expr = expr.limit(1)
                oneNextMessages = (yield (yield txn.execute(
                    expr
                )).fetchall())
                if oneNextMessages:
                    monthsMessagesRows.append(oneNextMessages[0])
                else:
                    break
                thisDateTime = (
                    datetime.datetime.utcfromtimestamp(
                        oneNextMessages[-1].received
                    ).replace(day=1, hour=0, minute=0, second=0)
                    - datetime.timedelta(seconds=1)
                )
            returnValue(monthsMessagesRows)
        return monthsQuery

    def oneMessage(self, listID, messageCounter):
        @self._dataStore.sql
        @inlineCallbacks
        def query(txn):
            m = self._messageTable
            result = (yield
                      (yield txn.execute(
                          m.select((m.c.list == listID) &
                                   (m.c.counter == messageCounter))))
                      .fetchall())[0]
            returnValue(ArchiveMessage(result))
        return query


    def ingestSomeMessages(self, listID):
        listDir = archives.child(listID)
        if listDir.isdir():
            if listID not in globalIngestionList:
                task = IngestionTask(listDir, self._dataStore,
                                     self._messageTable)
                globalIngestionList[listID] = task
                task.go()
            return globalIngestionList[listID].report()
        else:
            return u'nope not a list'


@authorizer_for(MessageIngestor,
                tables(
                    message=[
                        Column("list", String(), index=True),
                        Column("id", String(), index=True),
                        Column("sender", String(), index=True),
                        Column("subject", String(), index=True),
                        # vvv previously "date_timestamp" vvv
                        Column("received", Integer(), index=True),
                        Column("counter", Integer(), index=True),
                        Column("contents", String()),
                    ],
                    reply=[
                        Column("parent", String(), index=True),
                        Column("child", String(), index=True),
                    ],
                ))
def authorize_ingestor(metadata, datastore, session_store, transaction,
                       session):
    return MessageIngestor(datastore,
                           metadata.tables['message'],
                           metadata.tables['reply'])

@Plating.widget(
    tags=tags.transparent(
        tags.td(
            tags.a(href=["/list/", slot("listID"),
                         "/message/", slot("messageCounter")])(
                             slot("subject")
                         )
        ),
        tags.td(
            slot("date")
        )
    )
)
def oneMessageLink(messageRow):
    return {
        "listID": messageRow["list"],
        "messageCounter": messageRow["counter"],
        "subject": messageRow["subject"] or u"(no subject)",
        "date": unicode(datetime.datetime.utcfromtimestamp(
            messageRow["received"])
        ),
    }

class ListsManagementSite(object):
    app = Klein()

    @classmethod
    @inlineCallbacks
    def makeManagementSite(cls, reactor):
        procurer = yield open_session_store(
            reactor,
            "sqlite:////database/sessions3.sqlite",
            [authorize_ingestor.authorizer]
        )
        returnValue(cls(procurer))

    def __init__(self, procurer):
        self.procurer = procurer

    @requirer
    def authorized(self):
        return self.procurer

    @page.routed(app.route("/"),
                 tags.h1("Hello, world!"))
    def root(self, request):
        return {
            "title": "Front Page"
        }

    @app.route("/mailgun/webhook", methods=["POST"])
    @inlineCallbacks
    def webhook(self, request):
        content = json.loads(request.content.read())
        url = content['message-url']
        signature = content['signature']
        timestamp = content['timestamp']
        token = content['token']
        if not mgverify(os.environ['MAILGUN_API_KEY'], token, timestamp,
                        signature):
            request.setResponseCode(401)
            returnValue(b'unauthorized')
        # we need to get access to the data store, but the API-driven HTTP
        # client here is not going to authenticate via a header _or_ a cookie.
        # There should probably be a different public API for this.
        request.requestHeaders.setRawHeaders(
            b"X-Auth-Token", [b"synthetic-mailgun-token"]
        )
        session = yield self.procurer.procure_session(request)
        ingestor = yield session.authorize(MessageIngestor)[MessageIngestor]
        response = yield treq.get(url.encode("ascii"),
                                  {"Accept": "message/rfc2822"},
                                  auth=("api", os.environ['MAILGUN_API_KEY']))
        body = yield treq.content(response)
        body = json.loads(body)
        ingestor.ingestMessage(body["body-mime"])
        returnValue(b"OK")



    @authorized(
        page.routed(app.route("/ingest/<listID>"),
                    [tags.h1("Loading..."),
                     tags.div(tags.pre(slot("ingested")))]),
        ingestor=MessageIngestor,
    )
    def ingest(self, request, listID, ingestor):
        """
        Ingest messages for a given mailing list.
        """
        return {
            "ingested": ingestor.ingestSomeMessages(listID)
        }

    @authorized(
        page.routed(app.route("/list/<listID>/archive/"),
                    [tags.h1("List: ", slot("listID")),
                     tags.table()(
                         tags.tr(render="months:list")(slot("item"))
                     )]),
        # XXX "ingestor" is probably a bad name if it does everything
        ingestor=MessageIngestor,
    )
    @inlineCallbacks
    def archiveIndex(self, request, listID, ingestor):
        returnValue({
            "listID": listID,
            "months": [oneMessageLink.widget(row) for row in
                       (yield ingestor.monthsForList(listID))]
        })


    @authorized(
        page.routed(app.route("/list/<listID>/message/<messageCounter>"),
                    [tags.h1("List: ", slot("listID")),
                     tags.h2("Subject: ", slot("subject")),
                     tags.pre(
                         style="white-space: pre-wrap; max-width: 90em;"
                     )(slot("messageText"))]),
        ingestor=MessageIngestor,
    )
    @inlineCallbacks
    def messageView(self, request, listID, messageCounter, ingestor):
        """
        Route to render a single message.
        """
        message = yield ingestor.oneMessage(listID, messageCounter)
        if message is None:
            returnValue(None)
        returnValue({
            "listID": listID,
            "subject": message.subject(),
            "messageText": message.body(),
        })
