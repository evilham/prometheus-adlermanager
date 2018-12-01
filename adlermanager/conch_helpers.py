from twisted.cred import portal
from twisted.conch.manhole_tap import chainedProtocolFactory
from twisted.conch import interfaces as conchinterfaces
from twisted.conch import manhole_ssh, recvline, avatar
from twisted.conch.ssh import keys, session
from twisted.conch.insults import insults
from twisted.conch.checkers import IAuthorizedKeysDB, SSHPublicKeyChecker
from twisted.conch.checkers import readAuthorizedKeyFile

from twisted.python import filepath

from zope.interface import implementer

from twisted.application import service, strports


class SSHSimpleProtocol(recvline.HistoricRecvLine):
    def __init__(self, user):
        recvline.HistoricRecvLine.__init__(self)
        self.user = user
        self.ps = (b'', b'')

    def connectionMade(self):
        recvline.HistoricRecvLine.connectionMade(self)
        # CTRL_D
        self.keyHandlers[b'\x04'] = self.handle_EOF
        # CTRL_BACKSLASH
        self.keyHandlers[b'\x1c'] = self.handle_QUIT

        self.terminal.write(self.motd())
        self.terminal.nextLine()

        self.showPrompt()

    def handle_EOF(self):
        if self.lineBuffer:
            self.terminal.write(b'\a')
        else:
            self.handle_QUIT()

    def handle_QUIT(self):
        self.terminal.loseConnection()

    def showPrompt(self):
        self.terminal.write(">>> ")

    def _getCommand(self, cmd):
        """
        Get the method that would be run by 'cmd' if appliable.

        The convention is that a cmd command translates to a do_cmd method.
        """
        try:
            cmd_str = cmd.decode('utf-8')
            return getattr(self, 'do_' + cmd_str, None)
        except:
            return None

    def lineReceived(self, line):
        line = line.strip().split()
        if line:
            cmd, *args = line
            func = self._getCommand(cmd)
            if func:
                try:
                    func(*args)
                except Exception as ex:
                    self.terminal.write("Error: {}".format(ex))
            else:
                self.terminal.write(b'No such command: ' + cmd)
                self.terminal.nextLine()
        self.showPrompt()


    def do_help(self, cmd=''):
        """
        Get help on a command. Usage: help command
        """
        if cmd:
            func = self._getCommand(cmd)
            if func:
                self.terminal.write(func.__doc__)
            else:
                self.terminal.write('No such command: {}'.format(cmd))
        else:
            self.terminal.write('Available commands:')
            self.terminal.nextLine()
            self.terminal.nextLine()
            for cmd in (attr[3:]
                        for attr in dir(self)
                        if attr.startswith('do_')):
                self.terminal.write(cmd)
                self.terminal.nextLine()
        self.terminal.nextLine()

    def do_whoami(self):
        """
        Prints your username. Usage: whoami
        """
        self.terminal.write(self.user.username)
        self.terminal.nextLine()

    def do_clear(self):
        """
        Clears the screen. Usage: clear
        """
        self.terminal.reset()

    def do_exit(self):
        """
        Exit session. Usage: exit
        """
        self.handle_QUIT()

    def motd(self):
        return ''


@implementer(conchinterfaces.ISession)
class SSHSimpleAvatar(avatar.ConchUser):
    def __init__(self, username, proto):
        avatar.ConchUser.__init__(self)

        self.username = username
        self.proto = proto
        self.channelLookup.update({b'session': session.SSHSession})

    def openShell(self, protocol):
        serverProtocol = insults.ServerProtocol(self.proto, self)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))

    def getPty(self, terminal, windowSize, attrs):
        return None

    def execCommand(self, protocol, cmd):
        pass

    def closed(self):
        pass


@implementer(portal.IRealm)
class SSHSimpleRealm:
    """
    SSH simple realm that uses a given protocol for any valid users.

    You may want to customise the way that protocol works, realm and avatar
    are not necessarily of interest here.

    @ivar proto: The passed protocol class that will be used for avatar.
    """

    def __init__(self, proto):
        """
        Initialise a new L{SSHSimpleRealm} with proto as a protocol class.

        @param proto: a protocol class that will be used for any avatars.
        """
        self.proto = proto

    def requestAvatar(self, avatarId, mind, *interfaces):
        """
        Return a L{SSHSimpleAvatar} that uses ``self.proto`` as protocol.

        @see: L{portal.IRealm}
        """
        if conchinterfaces.IConchUser in interfaces:
            avatar = SSHSimpleAvatar(avatarId, self.proto)
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
    def __init__(self, baseDir, parseKey=keys.Key.fromString):
        """
        Initialises a new L{SSHKeyDirectory}.

        @param base_dir: the base directory for key lookup.
        @param parseKey: L{callable}
        """
        self.baseDir = baseDir
        self.parseKey = parseKey

    def getAuthorizedKeys(self, username):
        userKeys = []
        keyFile = self.baseDir.child(username + b'.key')
        keyDir = self.baseDir.child(username)
        print(keyFile, keyDir)

        if keyFile.isfile():
            for key in readAuthorizedKeyFile(keyFile.open(), self.parseKey):
                yield key

        if keyDir.isdir():
            for f in keyDir.globChildren('*.key'):
                for key in readAuthorizedKeyFile(f.open(), self.parseKey):
                    yield key


def conch_helper(endpoint, proto=None, namespace=dict(),
                 keyDir=None, keySize=4096):
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

    keyDir = filepath.FilePath(keyDir)
    keyDir.child('server').makedirs(True)
    keyDir.child('users').makedirs(True)

    checker = SSHPublicKeyChecker(SSHKeyDirectory(keyDir.child('users')))

    if proto is None:
        sshRealm = manhole_ssh.TerminalRealm()
        sshRealm.chainedProtocolFactory = chainedProtocolFactory(namespace)
    else:
        sshRealm = SSHSimpleRealm(proto)
    sshPortal = portal.Portal(sshRealm, [checker])


    sshKeyPath = keyDir.child('server').child('server.key')
    sshKey = keys._getPersistentRSAKey(sshKeyPath, keySize)

    sshFactory = manhole_ssh.ConchFactory(sshPortal)
    sshFactory.publicKeys[b'ssh-rsa'] = sshKey
    sshFactory.privateKeys[b'ssh-rsa'] = sshKey

    sshService = strports.service(endpoint, sshFactory)
    return sshService
