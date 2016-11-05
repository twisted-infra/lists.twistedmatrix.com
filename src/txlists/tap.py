

def makeService():
    from twisted.application.internet import StreamServerEndpointService
    from twisted.internet.endpoints import serverFromString
    from twisted.internet import reactor
    from twisted.web.server import Site

    from txlists.app import ListsManagementSite

    resource = ListsManagementSite().app.resource()

    return StreamServerEndpointService(
        serverFromString(reactor, "le:/certificates:tcp:8443"),
        Site(resource)
    )
