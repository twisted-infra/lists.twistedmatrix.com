
from twisted.web.template import tags, slot
from twisted.internet.defer import inlineCallbacks, returnValue

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


@attr.s
class MessageIngestor(object):
    _dataStore = attr.ib()
    _messageTable = attr.ib()
    _replyTable = attr.ib()

    def ingestSomeMessages(self):
        return u'messages: ingested'


@authorizer_for(MessageIngestor,
                tables(
                    message=[
                        Column("list", String(), index=True),
                        Column("id", String(), index=True),
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
    return MessageIngestor(datastore, metadata['message'], metadata['reply'])


class ListsManagementSite(object):
    app = Klein()

    @classmethod
    @inlineCallbacks
    def makeManagementSite(cls, reactor):
        procurer = yield open_session_store(reactor,
                                            "sqlite:///sessions.sqlite",
                                            [authorize_ingestor.authorizer])
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
        page.routed(app.route("/ingest"),
                    [tags.h1("Loading..."),
                     tags.div(slot("ingested"))]),
        ingestor=MessageIngestor,
    )
    def ingest(self, request, ingestor):
        """
        Ingest messages (temporary route).
        """
        return {
            "ingested": ingestor.ingestSomeMessages()
        }
