"""
This type stub file was generated by pyright.
"""

from typing import Any, Optional, Union

from attr import attrs
from tubes.itube import IFount

"""
HTTP message API.
"""
__all__ = ()
InternalBody = Union[bytes, IFount]

@attrs(frozen=False)
class MessageState:
    """
    Internal mutable state for HTTP message implementations in L{klein}.
    """

    cachedBody: Optional[bytes] = ...
    fountExhausted: bool = ...

def validateBody(instance: Any, attribute: Any, body: InternalBody) -> None:
    """
    Validator for L{InternalBody}.
    """
    ...

def bodyAsFount(body: InternalBody, state: MessageState) -> IFount:
    """
    Return a fount for a given L{InternalBody}.
    """
    ...

async def bodyAsBytes(body: InternalBody, state: MessageState) -> bytes:
    """
    Return bytes for a given L{InternalBody}.
    """
    ...
