from io import BytesIO
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterator,
    Optional,
    Tuple,
    Union,
    cast,
)

from zope.interface import implementer

from twisted.application import strports
from twisted.application.internet import StreamServerEndpointService
from twisted.conch import avatar, interfaces as conchinterfaces, manhole_ssh, recvline
from twisted.conch.checkers import (
    IAuthorizedKeysDB,
    SSHPublicKeyChecker,
    readAuthorizedKeyFile,
)
from twisted.conch.insults import insults
from twisted.conch.manhole_tap import chainedProtocolFactory
from twisted.conch.ssh import keys, session
from twisted.cred import portal
from twisted.internet import defer
from twisted.internet.error import ProcessTerminated
from twisted.python import failure, filepath


class SSHSimpleProtocol(recvline.HistoricRecvLine):
    terminal: insults.ServerProtocol
    keyHandlers: Dict[bytes, Callable[[], None]]
    interactive: bool = True

    _command_lineReceived: Optional[Callable[[bytes], None]] = None
    _command_inputEnded: Optional[Callable[[bytes], None]] = None

    def __init__(self, user: "SSHSimpleAvatar", interactive: bool = True) -> None:
        recvline.HistoricRecvLine.__init__(self)
        self.user = user
        self.interactive = interactive
        self.ps = (b"", b"")

    def terminal_write(self, msg: Union[bytes, str]) -> None:
        """
        Write data to the remote terminal.

        We use this method to work around awkward typing in t.c.insults.
        """
        return self.terminal.write(msg)  # type: ignore

    def initializeScreen(self) -> None:
        """
        Initialise terminal in InsertMode, without clearing the screen.

        This overrides the definition in twisted.conch.recvline.RecvLine:
        https://github.com/twisted/twisted/blob/7697871b4d89c78c8764c6be42372fc68299714e/src/twisted/conch/recvline.py#L385
        """
        self.terminal_write(self.ps[self.pn])
        self.setInsertMode()

    def connectionMade(self) -> None:
        recvline.HistoricRecvLine.connectionMade(self)
        if not self.interactive:
            return
        # CTRL_D
        self.keyHandlers[b"\x04"] = self.handle_EOF
        # CTRL_BACKSLASH
        self.keyHandlers[b"\x1c"] = self.handle_QUIT

        self.terminal_write(self.motd())
        self.terminal.nextLine()

        self.showPrompt()

    def handle_EOF(self) -> None:
        if self._command_inputEnded is not None:
            self._command_inputEnded(b"".join(self.lineBuffer))  # type: ignore
        if self.lineBuffer:  # type: ignore
            self.terminal_write(b"\a")
        else:
            self.exitWithCode(0)

    def handle_QUIT(self) -> None:
        self.terminal.loseConnection()

    def showPrompt(self) -> None:
        if self.interactive:
            self.terminal_write(">>> ")

    def _getCommand(
        self, cmd: bytes
    ) -> Optional[Callable[..., Union[None, Coroutine[Any, Any, None]]]]:
        """
        Get the method that would be run by 'cmd' if appliable.

        The convention is that a cmd command translates to a do_cmd method.
        """
        try:
            cmd_str = cmd.decode("utf-8")
            return getattr(self, "do_" + cmd_str, None)
        except Exception:
            return None

    async def runCommand(self, cmd: bytes, *args: bytes) -> None:
        """
        Run the requested command or print 'No such command'.
        """
        func = self._getCommand(cmd)
        if func:
            try:
                res = func(*args)
                if res is not None:
                    await defer.ensureDeferred(res)
                if not self.interactive:
                    self.exitWithCode(0)
            except Exception as ex:
                self.terminal_write("Error: {}".format(ex))
                self.terminal.nextLine()
                if not self.interactive:
                    self.exitWithCode(2)
        else:
            self.terminal_write(b"No such command: " + cmd)
            self.terminal.nextLine()
            if not self.interactive:
                self.exitWithCode(1)

    async def runLine(self, line: bytes) -> None:
        line_parts = line.strip().split()
        if line_parts:
            cmd, *args = line_parts
            return await self.runCommand(cmd, *args)

    async def _lineReceived(self, line: bytes) -> None:
        await self.runLine(line)
        self.showPrompt()

    def lineReceived(self, line: bytes) -> None:
        if self._command_lineReceived is None:
            _ = defer.ensureDeferred(self._lineReceived(line))
        else:
            self._command_lineReceived(line)

    def get_user_input(self, eom: bytes = b"") -> defer.Deferred[bytes]:
        d = defer.Deferred[bytes]()
        data = BytesIO()

        def _ui_lineReceived(line: bytes) -> None:
            if eom and line != eom:
                data.write(line)
                data.write(b"\n")
            else:
                _ui_inputEnded(line)

        def _ui_inputEnded(line: bytes) -> None:
            if line and line != eom:
                data.write(line)
                data.write(b"\n")
            self._command_lineReceived, self._command_inputEnded = None, None
            d.callback(data.getvalue())

        self._command_lineReceived, self._command_inputEnded = (
            _ui_lineReceived,
            _ui_inputEnded,
        )
        return d

    def exitWithCode(self, code: int) -> None:
        cast(session.SSHSessionProcessProtocol, self.terminal.transport).processEnded(
            failure.Failure(ProcessTerminated(code, None, None))
        )

    def do_help(self, cmd: bytes = b"") -> None:
        """
        Get help on a command. Usage: help [command]
        """
        if cmd:
            func = self._getCommand(cmd)
            if func:
                self.terminal_write(
                    getattr(func, "__doc__", b"No help for '" + cmd + b"'")
                )
            else:
                self.terminal_write(b"No such command: " + cmd)
        else:
            self.terminal_write("Available commands:")
            self.terminal.nextLine()
            self.terminal.nextLine()
            for c in (attr[3:] for attr in dir(self) if attr.startswith("do_")):
                self.terminal_write(c)
                self.terminal.nextLine()
        self.terminal.nextLine()

    def do_whoami(self) -> None:
        """
        Prints your username. Usage: whoami
        """
        self.terminal_write(self.user.username)
        self.terminal.nextLine()

    def do_clear(self) -> None:
        """
        Clears the screen. Usage: clear
        """
        self.terminal.reset()

    def do_exit(self) -> None:
        """
        Exit session. Usage: exit
        """
        self.exitWithCode(0)

    def motd(self) -> str:
        return ""


@implementer(conchinterfaces.ISession)
class SSHSimpleAvatar(avatar.ConchUser):
    serverProtocol: Optional[insults.ServerProtocol] = None

    def __init__(self, username: bytes, proto: SSHSimpleProtocol):
        avatar.ConchUser.__init__(self)

        self.username = username
        self.proto = proto
        self.channelLookup.update({b"session": session.SSHSession})  # type: ignore

    def openShell(self, protocol: session.SSHSessionProcessProtocol) -> None:
        self.serverProtocol = insults.ServerProtocol(self.proto, self)
        self.serverProtocol.makeConnection(protocol)  # type: ignore
        protocol.makeConnection(  # type: ignore
            session.wrapProtocol(self.serverProtocol)  # type: ignore
        )

    def getPty(self, terminal, windowSize, attrs) -> None:  # type: ignore
        return None

    def execCommand(
        self, protocol: session.SSHSessionProcessProtocol, line: bytes
    ) -> None:
        self.serverProtocol = insults.ServerProtocol(
            self.proto, self, interactive=False
        )
        self.serverProtocol.makeConnection(protocol)  # type: ignore
        protocol.makeConnection(  # type: ignore
            session.wrapProtocol(self.serverProtocol)  # type: ignore
        )
        _ = defer.ensureDeferred(
            cast(
                SSHSimpleProtocol, self.serverProtocol.terminalProtocol  # type: ignore
            ).runLine(line)
        )

    def windowChanged(self, dimensions: Tuple[int, int, int, int]):  # type: ignore
        """This gets triggered when user changes terminal dimensions.

        Args:
            dimensions (Tuple[int, int, int, int]): Probably height, width and "0, 0"
        """
        pass

    def eofReceived(self) -> None:
        """
        Called when the other side has indicated no more data will be sent.
        """
        if self.serverProtocol is not None:
            ssh_sp = cast(
                SSHSimpleProtocol, self.serverProtocol.terminalProtocol  # type: ignore
            )
            ssh_sp.handle_EOF()

    def closed(self) -> None:
        """
        Called when the session is closed.
        """
        pass


@implementer(portal.IRealm)
class SSHSimpleRealm:
    """
    SSH simple realm that uses a given protocol for any valid users.

    You may want to customise the way that protocol works, realm and avatar
    are not necessarily of interest here.

    @ivar proto: The passed protocol class that will be used for avatar.
    """

    def __init__(self, proto: SSHSimpleProtocol):
        """
        Initialise a new L{SSHSimpleRealm} with proto as a protocol class.

        @param proto: a protocol class that will be used for any avatars.
        """
        self.proto = proto

    def requestAvatar(
        self,
        avatarId: Union[bytes, Tuple[()]],
        mind: object,
        *interfaces: portal._InterfaceItself,  # type: ignore
    ) -> Union[
        defer.Deferred[portal._requestResult], portal._requestResult  # type: ignore
    ]:
        """
        Return a L{SSHSimpleAvatar} that uses ``self.proto`` as protocol.

        @see: L{portal.IRealm}
        """
        if conchinterfaces.IConchUser in interfaces:
            avatar = SSHSimpleAvatar(cast(bytes, avatarId), self.proto)
            return interfaces[0], avatar, lambda: None
        else:
            raise Exception("No supported interfaces found.")


@implementer(IAuthorizedKeysDB)
class SSHKeyDirectory(object):
    """
    Provides SSH public keys based on a simple directory structure.

    For a user ``USER`` following files are returned if they exist:
      - ``$USER/*.key``
      - ``$USER.key``
    These paths are relative to L{SSHKeyDirectory.baseDir}

    @ivar baseDir: the base directory for key lookup.
    """

    def __init__(
        self,
        baseDir: filepath.FilePath[str],
        parseKey: Any = keys.Key.fromString,  # type: ignore
    ) -> None:
        """
        Initialises a new L{SSHKeyDirectory}.

        @param base_dir: the base directory for key lookup.
        @param parseKey: L{callable}
        """
        self.baseDir = baseDir
        self.parseKey = parseKey

    def getAuthorizedKeys(self, username: bytes) -> Iterator[keys.Key]:
        keyFile = self.baseDir.child(username + b".key")
        keyDir = self.baseDir.child(username)

        if keyFile.isfile():
            for key in readAuthorizedKeyFile(keyFile.open(), self.parseKey):
                yield key

        if keyDir.isdir():
            for f in keyDir.globChildren("*.key"):
                for key in readAuthorizedKeyFile(f.open(), self.parseKey):
                    yield key


def conch_helper(
    endpoint: str,
    proto: Optional[SSHSimpleProtocol] = None,
    namespace: Dict[str, str] = dict(),
    keyDir: Optional[str] = None,
    keySize: int = 4096,
) -> StreamServerEndpointService:
    """
    Return a L{SSHKeyDirectory} based SSH service with the given parameters.

    Authorized keys are read as per L{SSHKeyDirectory} with ``baseDir`` being
    ``keyDir/users``.

    @param endpoint: endpoint for the SSH service
    @param namespace: the manhole namespace
    @param keyDir: directory that holds server/server.key file and
        users directory, which is used as ``baseDir`` in L{SSHKeyDirectory}
    @see: L{SSHKeyDirectory}
    """
    if keyDir is None:
        from twisted.python._appdirs import getDataDirectory

        keyDir = getDataDirectory()

    ssh_keys_dir = filepath.FilePath(keyDir)
    ssh_keys_dir.child("server").makedirs(True)
    ssh_keys_dir.child("users").makedirs(True)

    checker = SSHPublicKeyChecker(
        SSHKeyDirectory(ssh_keys_dir.child("users"))  # type: ignore
    )

    if proto is None:
        sshRealm = manhole_ssh.TerminalRealm()
        sshRealm.chainedProtocolFactory = chainedProtocolFactory(  # type: ignore
            namespace
        )
    else:
        sshRealm = SSHSimpleRealm(proto)  # type: ignore
    sshPortal = portal.Portal(sshRealm, [checker])  # type: ignore

    sshKeyPath = ssh_keys_dir.child("server").child("server.key")
    sshKey = keys._getPersistentRSAKey(sshKeyPath, keySize)  # type: ignore

    sshFactory = manhole_ssh.ConchFactory(sshPortal)
    sshFactory.publicKeys[b"ssh-rsa"] = sshKey  # type: ignore
    sshFactory.privateKeys[b"ssh-rsa"] = sshKey  # type: ignore

    sshService = strports.service(endpoint, sshFactory)  # type: ignore
    return sshService
