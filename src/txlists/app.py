
import html5lib
from email.utils import parsedate_tz, mktime_tz#, parseaddr

from twisted.web.template import tags, slot
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python.filepath import FilePath
from twisted.internet.task import cooperate

from klein import Klein, Plating
from klein.storage.sql import authorizer_for, open_session_store, tables
from klein._session import requirer

from sqlalchemy import Column, String, Integer
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

def normalizeDate(string):
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
    return number, sender, date


@attr.s
class IngestionTask(object):
    """
    
    """
    _archiveDir = attr.ib()
    _dataStore = attr.ib()
    _messageTable = attr.ib()
    _currentStatus = attr.ib(default=u'')

    def report(self):
        """
        
        """
        return self._currentStatus

    def ingestOneBatch(self, paths):
        """
        
        """
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
        return do

    def go(self):
        """
        
        """
        def justKeepIngesting():
            batchSize = 100
            thisBatch = []
            for idx, eachPath in enumerate(self._archiveDir.walk()):
                if (
                        len(eachPath.basename().split(".")) == 2
                        and eachPath.basename().endswith(".html")
                ):
                    thisBatch.append(eachPath)
                    if len(thisBatch) >= batchSize:
                        yield self.ingestOneBatch(thisBatch)
                        thisBatch = []
                        self._currentStatus = (
                            u'ingested {} batches'.format(idx)
                        )
            self._currentStatus = u'DONE!'
        self._task = cooperate(justKeepIngesting())


@attr.s
class MessageIngestor(object):
    _dataStore = attr.ib()
    _messageTable = attr.ib()
    _replyTable = attr.ib()

    def ingestSomeMessages(self, listID):
        listDir = archives.child(listID)
        if listDir.isdir():
            if listID not in globalIngestionList:
                task = IngestionTask(listDir, self._dataStore,
                                     self._messageTable)
                globalIngestionList[listID] = task
                task.go()
            return globalIngestionList.report()
        else:
            return u'nope not a list'


@authorizer_for(MessageIngestor,
                tables(
                    message=[
                        Column("list", String(), index=True),
                        Column("id", String(), index=True),
                        Column("sender", String(), index=True),
                        # vvv previously "date_timestamp" vvv
                        Column("received", String(), index=True),
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


class ListsManagementSite(object):
    app = Klein()

    @classmethod
    @inlineCallbacks
    def makeManagementSite(cls, reactor):
        procurer = yield open_session_store(
            reactor,
            "sqlite:////database/sessions2.sqlite",
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


    @authorized(
        page.routed(app.route("/ingest/<listID>"),
                    [tags.h1("Loading..."),
                     tags.div(slot("ingested"))]),
        ingestor=MessageIngestor,
    )
    def ingest(self, request, listID, ingestor):
        """
        Ingest messages for a given mailing list.
        """
        return {
            "ingested": ingestor.ingestSomeMessages(listID)
        }
