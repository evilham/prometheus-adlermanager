import json
from typing import TYPE_CHECKING, Any, Dict, List

from twisted.internet import reactor, task
from twisted.web._responses import BAD_REQUEST, OK
from twisted.web.server import Request

from .TokenResource import TokenResource

if TYPE_CHECKING:
    from .SitesManager import SiteManager, SitesManager


class AdlerManagerTokenResource(TokenResource):
    """
    TokenResource used for AdlerManager
    """

    HEADER = "Authorization"

    def __init__(self, sites_manager: "SitesManager"):
        """
        @param site_manager: The object managing state for all sites.
        @type  site_manager: L{adlermanager.SitesManager}
        """
        TokenResource.__init__(self, tokens=sites_manager.tokens)

    def preprocess_header(self, header: str) -> str:
        return header.split(" ")[-1]

    def processToken(self, token_data: "SiteManager", request: Request) -> int:
        """
        Pass Alerts along if Authorization Header matched.

        @param token_data: The object associated with the passed token.
        @type  L{adlermanager.SiteManager}

        @param request: The request object associated to this request.
        @type  L{twisted.web.http.Request}
        """

        try:
            request_body: bytes = request.content.read()  # type: ignore
            alert_data: List[Dict[str, Any]] = json.loads(request_body)
        except Exception:
            return BAD_REQUEST

        site = token_data

        task.deferLater(reactor, 0, site.process_alerts, alert_data)  # type: ignore
        return OK
