"""
This type stub file was generated by pyright.
"""

from typing import Union

from zope.interface import implementer

from attr import attrs
from hyperlink import DecodedURL
from tubes.itube import IFount

from ._imessage import IHTTPHeaders, IHTTPRequest
from ._message import MessageState

"""
HTTP request API.
"""
__all__ = ()

@implementer(IHTTPRequest)
@attrs(frozen=True)
class FrozenHTTPRequest:
    """
    Immutable HTTP request.
    """

    method: str = ...
    uri: DecodedURL = ...
    headers: IHTTPHeaders = ...
    _body: Union[bytes, IFount] = ...
    _state: MessageState = ...
    def bodyAsFount(self) -> IFount: ...
    async def bodyAsBytes(self) -> bytes: ...
