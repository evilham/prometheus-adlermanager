from twisted.web import server, resource
from twisted.internet import defer
from twisted.web._responses import *


class TokenResource(resource.Resource):
    """
    A simple Header based Auth-Token protected Resource.

    Subclass and replace HEADER, processToken and unauthorizedMessage
    as needed.

    @cvar HEADER: The header to get the token from.
    @ivar tokens: A mapping of valid tokens to any target objects.
    """
    HEADER = 'Auth-Token'

    def __init__(self, tokens=dict()):
        """
        @param tokens: The mapping of valid tokens to target objects.
        """
        resource.Resource.__init__(self)
        self.tokens = tokens

    def render(self, request):
        """
        See L{resource.Resource}.

        @see: L{resource.Resource.render}.
        """
        header = request.getHeader(self.HEADER)
        token_data = self.tokens.get(header, None)

        if token_data is None:
            request.setResponseCode(UNAUTHORIZED)
            page = self.unauthorizedPage()
            return page.render(request)

        self._processToken(token_data, request)
        return server.NOT_DONE_YET

    def processToken(self, token_data, request):
        """
        Process the token and write to request as needed.

        You are not allowed to call request.finish(), that will be handled
        by L{TokenResource._processToken}.

        You can return a L{defer.Deferred} which will be waited upon to
        finish the request.

        @param token_data: The object associated with the passed token.
        @param request: The request object associated to this request.
        """
        pass

    @defer.inlineCallbacks
    def _processToken(self, token_data, request):
        """
        Invoke L{TokenResource.processToken} and produce a 500 if it fails.

        @param token_data: The object associated with the passed token.
        @param request: The request object associated to this request.
        """
        try:
            success = yield defer.maybeDeferred(self.processToken,
                                                token_data,
                                                request)
        except Exception as ex:
            import traceback
            traceback.print_stack()
            success = False
        request.setResponseCode(OK if success else INTERNAL_SERVER_ERROR)
        request.finish()
        return success

    def unauthorizedPage(self):
        """
        Page to render when there is no valid token.
        This makes use of L{TokenResource.unauthorizedMessage} by default.
        """
        return resource.ErrorPage(UNAUTHORIZED,
                                  'Unauthorized',
                                  self.unauthorizedMessage())

    def unauthorizedMessage(self):
        """
        Message to show when there is no valid token.
        """
        return "Pass a valid token in the {} header.".format(self.HEADER)

    def getChild(self, name, request):
        """
        Use this child for everything but the explicitly overriden.

        @see: L{resource.Resource.getChild}
        """
        return self
