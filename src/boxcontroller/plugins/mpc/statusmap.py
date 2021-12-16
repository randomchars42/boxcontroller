#!/usr/bin/env python3

import logging
from pathlib import Path
import sys

from boxcontroller.plugin import Plugin
from boxcontroller.keymap import KeyMap

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class StatusMap(KeyMap):
    """Store status information for all configured folders and playlists.

    The folder / playlist name is used as key. The special key #CURRENT is used
    to store the key of the currently / last played folder / playlist

    StatusMap is a special case of KeyMap as only the key and keyworded data
    gets stored.
    """

    def __init__(self, config):
        """Initialise variables and load map from file(s)."""
        super().__init__(config)
        self.__path = Path(self.get_config().get('MPC', 'path_status'))
        self.__path = self.__path.expanduser().resolve()
        self.reset()

    def reset(self):
        """Reset variables."""
        super().reset()
        self.load(self.get_path())

    def get_path(self):
        return self.__path

    def get(self, key, parameter = None):
        """Return the status for key.

        Positional arguments:
        key -- the key [string]
        parameter -- what to return, returns all if parameter == None [string]
        """
        try:
            if parameter is None:
                return self._get_map()[key]['positional']
            return self._get_map()[key]['positional'][parameter]
        except KeyError:
            logger.error('no entry for key: "{}"'.format(key))
            return None

    def update(self, key, soft = False, **status):
        """Update, add or delete a status.

        Updates the data for a given key incrementally, e.g.,

        stored data:
            - 'type': 'playlist'
            - 'position': '42'
            - 'time': '01:42'
            - 'volume': '50'

        given data:
            -'time': '02:42'

        will result in:
            - 'type': 'playlist'
            - 'position': '42'
            - 'time': '02:42'
            - 'volume': '50'

        Positional arguments:
        key -- the key [string]
        soft -- update dict only, do not yet write to disc [boolean]
        **status -- keyworded data [string: string], leave empty to remove entry
        """
        map = self._get_map()
        if not key in map:
            map()[key] = {'positional': {}}

        try:
            map()[key]['positional'].update(status)
        except KeyError:
            logger.error('Map with no further information (key: "{}")'.format(
                key))
            return

        if not soft:
            super().update(self.get_path(), key, **map[positional])

    def remove(self, key):
        """Remove entry with key.

        Positional arguments:
        path -- the path of the file [string]
        key -- the key of the data to remove
        """
        super().remove(self.get_path(), key)

    def get_current_key(self):
        """Return the special entry #CURRENT."""
        try:
            return self._get_map()['#CURRENT']['positional']['key']
        except KeyError:
            return None

    def set_current_key(self, key):
        """Use the #CURRENT entry to store the key of the current configuration.

        Positional arguments:
        key -- the key [string]
        """
        self.update('#CURRENT', key=key)
