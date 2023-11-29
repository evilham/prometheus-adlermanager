import functools

from .conch_helpers import SSHSimpleProtocol

from .Config import Config


class AdlerManagerSSHProtocol(SSHSimpleProtocol):
    sites_manager = None

    def __init__(self, user):
        """
        Create an instance of AdlerManagerSSHProtocol.
        """
        SSHSimpleProtocol.__init__(self, user)

        # TODO: Do stuff like getting user sites, showing alert warnings, etc.

    def do_add_token(self, token_id):
        """
        TODO: think better API (Identify site?)

        Add and generate a token. Usage: add_token TOKEN_ID

          - TOKEN_ID:
              Will be used to differentiate tokens. May be shown on the site.
        """
        person_id = self.user.username

        # Everything is bytes, we have to go back to unicode before
        try:
            token_id = token_id.decode("utf-8")
            person = person.decode("utf-8")
            person_id = person_id.decode("utf-8")
        except:
            self.terminal.write("Could not decode your arguments.")
            self.terminal.nextLine()
            return

        token = self.sites_manager.add_token(
            token_id,
        )
        self.terminal.write("Your new Token is: {}".format(token))
        self.terminal.nextLine()

    @functools.lru_cache()  # we don't need to re-read every time
    def motd(self):
        # TODO: Use data location?
        return open("motd.txt").read()
