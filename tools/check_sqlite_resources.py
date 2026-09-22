"""Run tests with explicit SQLite ownership checks (including Python <3.13)."""
import sqlite3
import sys
import traceback
import unittest
from unittest.mock import patch

connections = []
original_connect = sqlite3.connect


class TrackedConnection(sqlite3.Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.closed = False
        self.origin = ''.join(traceback.format_stack(limit=6))
        connections.append(self)

    def close(self):
        super().close()
        self.closed = True


def connect(*args, **kwargs):
    kwargs['factory'] = TrackedConnection
    return original_connect(*args, **kwargs)


if __name__ == '__main__':
    with patch('sqlite3.connect', connect):
        result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('tests'))
    leaked = [connection for connection in connections if not connection.closed]
    for connection in leaked:
        print('UNCLOSED SQLITE CONNECTION\n' + connection.origin, file=sys.stderr)
    print(f'SQLite ownership: {len(connections)} opened, {len(leaked)} unclosed')
    sys.exit(0 if result.wasSuccessful() and not leaked else 1)
