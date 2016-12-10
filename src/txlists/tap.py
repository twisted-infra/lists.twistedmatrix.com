
import os
from twisted.python.usage import Options as UsageOptions

class Options(UsageOptions, object):
    ""

def makeService(options):
    from twisted.application.internet import StreamServerEndpointService
    from twisted.internet.endpoints import serverFromString
    from twisted.internet import reactor
    from twisted.web.server import Site
    from twisted.logger import Logger

    log = Logger()

    from txlists.app import ListsManagementSite

    from twisted.application.service import MultiService, Service

    multiService = MultiService()

    class DeferredStartupService(Service, object):
        def startService(self):
            super(DeferredStartupService, self).startService()
            log.info("requesting service startup")
            (ListsManagementSite.makeManagementSite(reactor)
             .addCallback(dbReady))
    DeferredStartupService().setServiceParent(multiService)

    def dbReady(listsManagementSite):
        log.info("list management site ready {lms}", lms=listsManagementSite)
        resource = listsManagementSite.app.resource()
        StreamServerEndpointService(
            serverFromString(reactor, "{}:/certificates:tcp:8443".format(
                "txsni" if os.environ.get("NO_RENEW") else "le"
            )),
            Site(resource)
        ).setServiceParent(multiService)

    return multiService
