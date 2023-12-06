"""
This type stub file was generated by pyright.
"""

from typing import TYPE_CHECKING, Sequence, Tuple, Union

from twisted.python.failure import Failure
from twisted.web.iweb import IRequest
from twisted.web.resource import Resource

from ._app import Klein, KleinRenderable

if TYPE_CHECKING: ...

def ensure_utf8_bytes(v: Union[str, bytes]) -> bytes:
    """
    Coerces a value which is either a C{str} or C{bytes} to a C{bytes}.
    If ``v`` is a C{str} object it is encoded as utf-8.
    """
    ...

class _StandInResource:
    """
    A standin for a Resource.

    This is a sentinel value for L{KleinResource}, to say that we are rendering
    a L{Resource}, which may close the connection itself later.
    """

    ...

StandInResource = ...

class URLDecodeError(Exception):
    """
    Raised if one or more string parts of the URL could not be decoded.
    """

    __slots__ = ...
    def __init__(self, errors: Sequence[Tuple[str, Failure]]) -> None:
        """
        @param errors: Sequence of decoding errors, expressed as tuples
            of names and an associated failure.
        """
        ...
    def __repr__(self) -> str: ...

def extractURLparts(request: IRequest) -> Tuple[str, str, int, str, str]:
    """
    Extracts and decodes URI parts from C{request}.

    All strings must be UTF8-decodable.

    @param request: A Twisted Web request.

    @raise URLDecodeError: If one of the parts could not be decoded as UTF-8.

    @return: L{tuple} of the URL scheme, the server name, the server port, the
        path info and the script name.
    """
    ...

class KleinResource(Resource):
    """
    A ``Resource`` that can do URL routing.
    """

    isLeaf = ...
    def __init__(self, app: Klein) -> None: ...
    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def render(self, request: IRequest) -> KleinRenderable: ...
