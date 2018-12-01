from twisted.web import resource

import json

from .TokenResource import TokenResource


class AdlerManagerTokenResource(TokenResource):
    """
    TokenResource used for AdlerManager
    """
    HEADER = 'Authorization'

    def __init__(self, site_manager):
        """
        @param site_manager: The object managing state for all sites.
        @type  site_manager: L{adlermanager.SiteManager}
        """
        TokenResource.__init__(self, tokens=site_manager.tokens)

        self.site_manager = site_manager

    def preprocess_header(self, header):
        return header.split(' ')[-1]

    def processToken(self, token_data, request):
        """
        Pass Alerts along if Authorization Header matched.

        @param token_data: The object associated with the passed token.
        @type  L{adlermanager.SiteManager}

        @param request: The request object associated to this request.
        @type  L{twisted.web.http.Request}
        """

        try:
            request_body = request.content.read().decode('utf-8')
            alert_data = json.loads(request_body)
        except:
            return False

        site = token_data

        site.process_alerts(alert_data)
        return True
