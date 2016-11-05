
"""
tap plugin for txlists
"""

from twisted.application.service import ServiceMaker

Txlists = ServiceMaker(
    "Lists",
    "txlists.tap",
    "mailing list interface",
    "txlists"
)
