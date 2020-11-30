from typing import List

from pandablocks.blocking import BlockingClient
from pandablocks.commands import Command, Get, Raw


class State:
    """
    A class for loading/saving PandA state from/to a text file

    The file format is a series of PandA-client command strings
    """

    def __init__(self, host: str):
        """
        Args:
            host (str): the IP address or DNS name of a PandA
        """
        self._host = host
        self._client = BlockingClient(host)
        self._client.connect()

    def __del__(self):
        self._client.close()

    def _send_get(self, command: str) -> List[str]:
        """
        Send 'command' to host, get the results and return them as a list of strings

        Args:
            command str: PandA command on which to perform 'get'
        """
        lines = self._client.send(Get(command))

        # send may return a single bytes or a list of bytes
        if isinstance(lines, bytes):
            result = [lines.decode()]
        else:
            result = [line.decode() for line in lines]
        return result

    def save(self) -> List[str]:
        """
        Create a sequence of commands that will set up a PandaA to mirror
        the current host's state.

        Returns:
            str: A sequence of PandA-client command strings
        """
        def save_table(table: str) -> None:
            assert table[-1] == "<", f"bad response to *CHANGES.TABLE: {table}"
            commands.append(table + "B")
            for line in self._send_get(table[:-1] + ".B"):
                commands.append(line)
            else:
                # TODO is a blank line required for empty table?
                commands.append('')

        def save_metatable(meta: str) -> None:
            commands.append(meta)
            for line in self._send_get(meta[:-1]):
                commands.append(line)
            else:
                commands.append('')

        def save_metadata(line: str) -> None:
            if line[-1] == '<':
                save_metatable(line)
            else:
                commands.append(line)

        # save the CONFIG state
        commands = self._send_get("*CHANGES.ATTR")
        commands += self._send_get("*CHANGES.CONFIG")
        # save individual tables
        tables = self._send_get("*CHANGES.TABLE")
        for table in tables:
            save_table(table)
        # save metadata which is a mix of values and tables
        metadata = self._send_get("*CHANGES.METADATA")
        for line in metadata:
            save_metadata(line)

        return commands

    def load(self, commands: List[str]):
        """
        Send a sequence of commands to host. Provide a sequence obtained from
        State.save() in order to restore a previous state.

        Args:
            commands (str): a series of PandA-client commmand strings
        """
        self._client.send(Raw(commands))
