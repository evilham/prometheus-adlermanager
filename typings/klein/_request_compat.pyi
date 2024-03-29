"""
This type stub file was generated by pyright.
"""

from zope.interface import implementer

from attr import attrs
from hyperlink import DecodedURL
from tubes.itube import IFount
from twisted.web.iweb import IRequest

from ._headers import IHTTPHeaders
from ._message import MessageState
from ._request import IHTTPRequest

"""
Support for interoperability with L{twisted.web.iweb.IRequest}.
"""
__all__ = ()
noneIO = ...

@implementer(IHTTPRequest)
@attrs(frozen=True)
class HTTPRequestWrappingIRequest:
    """
    HTTP request.

    This is an L{IHTTPRequest} implementation that wraps an L{IRequest} object.
    """

    _request: IRequest = ...
    _state: MessageState = ...
    @property
    def method(self) -> str: ...
    @property
    def uri(self) -> DecodedURL: ...
    @property
    def headers(self) -> IHTTPHeaders: ...
    def bodyAsFount(self) -> IFount: ...
    async def bodyAsBytes(self) -> bytes: ...
