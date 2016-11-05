
from klein import Klein
from twisted.web.static import Data

class ListsManagementSite(object):
    app = Klein()

    @app.route("/")
    def root(self, request):
        return Data(
            "Hello! A list management website: {}".format(self)
            .encode("utf-8"),
            "text/plain"
        )
