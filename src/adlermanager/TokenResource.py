from typing import Any, Dict, Generator, Union, cast

from twisted.internet import defer
from twisted.logger import Logger
from twisted.web import resource, server
from twisted.web._responses import INTERNAL_SERVER_ERROR, OK, UNAUTHORIZED
from twisted.web.server import Request

log = Logger()


class TokenResource(resource.Resource):
    """
    A simple Header based Auth-Token protected Resource.

    Subclass and replace HEADER, processToken and unauthorizedMessage
    as needed.

    @cvar HEADER: The header to get the token from.
    @ivar tokens: A mapping of valid tokens to any target objects.
    """

    HEADER = "Auth-Token"

    def __init__(self, tokens: Dict[str, Any] = dict()):
        """
        @param tokens: The mapping of valid tokens to target objects.
        """
        resource.Resource.__init__(self)
        self.tokens = tokens

    def render(self, request: Request) -> Union[bytes, int]:
        """
        See L{resource.Resource}.

        @see: L{resource.Resource.render}.
        """
        raw_header = request.getHeader(self.HEADER)
        if not raw_header:
            return self._unauthorized(request)
        header = self.preprocess_header(raw_header)
        token_data = self.tokens.get(header, None)

        if token_data is None:
            return self._unauthorized(request)

        self._processToken(token_data, request).addCallback(  # type: ignore
            lambda x: request.finish()
        )
        return server.NOT_DONE_YET

    def preprocess_header(self, header: str) -> str:
        return header

    def processToken(self, token_data: Any, request: Request) -> int:
        """
        Process the token and write to request as needed.

        You are not allowed to call request.finish(), that will be handled
        by L{TokenResource._processToken}.

        You can return a L{defer.Deferred} which will be waited upon to
        finish the request.

        @param token_data: The object associated with the passed token.
        @param request: The request object associated to this request.
        """
        return OK

    @defer.inlineCallbacks
    def _processToken(
        self, token_data: Any, request: Request
    ) -> Generator[defer.Deferred[int], None, None]:
        """
        Invoke L{TokenResource.processToken} and produce a 500 if it fails.

        @param token_data: The object associated with the passed token.
        @param request: The request object associated to this request.
        """
        try:
            res = yield defer.maybeDeferred(self.processToken, token_data, request)
            code: int = cast(int, res)
        except Exception:
            log.failure("Unknown error")

            code = INTERNAL_SERVER_ERROR
        request.setResponseCode(code)  # type: ignore
        defer.returnValue(code)

    def _unauthorized(self, request: Request) -> bytes:
        """
        Send a 401 Unauthorized response.

        @param request: The request object associated to this request.
        """
        request.setResponseCode(UNAUTHORIZED)  # type: ignore
        return self.unauthorizedPage().render(request)  # type: ignore

    def unauthorizedPage(self) -> resource.ErrorPage:
        """
        Page to render when there is no valid token.
        This makes use of L{TokenResource.unauthorizedMessage} by default.
        """
        return resource.ErrorPage(
            UNAUTHORIZED, "Unauthorized", self.unauthorizedMessage()
        )

    def unauthorizedMessage(self) -> str:
        """
        Message to show when there is no valid token.
        """
        return "Pass a valid token in the {} header.".format(self.HEADER)

    def getChild(self, name: str, request: Request) -> "TokenResource":
        """
        Use this child for everything but the explicitly overriden.

        @see: L{resource.Resource.getChild}
        """
        return self
