#!/usr/bin/env python3

import logging
from pathlib import Path
import sys

from boxcontroller.plugin import Plugin
from boxcontroller.keymap import KeyMap

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class StatusMap(KeyMap):
    """Store status information for all configured folders and playlists.

    The folder / playlist name is used as key. The special key CURRENT is used
    to store the key of the currently / last played folder / playlist

    StatusMap is a special case of KeyMap as only the key and keyworded data
    gets stored.
    """

    status_keywords = ['position', 'time', 'file', 'name', 'repeat', 'random',
        'single', 'consume']

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
                return self.get_map()[key]['keyword'].copy()
            return self.get_map()[key]['keyword'][parameter]
        except KeyError:
            logger.error('no entry for key: "{}"'.format(key))
            return None

    def update(self, key, *args, soft = False, **status):
        """Update, add or delete a status.

        Updates the data for a given key incrementally, e.g.,

        stored data:
            - 'type': 'playlist'
            - 'position': '42'
            - 'time': '01:42'
            - 'volume': '50'

        given data:
            - 'time': '02:42'

        will result in:
            - 'type': 'playlist'
            - 'position': '42'
            - 'time': '02:42'
            - 'volume': '50'

        Positional arguments:
        key -- the key [string]
        *args -- positional arguments, if key is CURRENT the first will be used
                 to store as current key, the rest will be ignored
        soft -- update dict only, do not yet write to disc [boolean]
        **status -- keyworded data [string: string], leave empty to remove entry
        """
        logger.debug('updating (soft: {}) map for key "{}": {},{}'.format(soft,
            key, ','.join(args), ','.join(
                ['{}={}'.format(kw,v) for kw,v in status.items()])))
        map = self.get_map()

        if not key in map:
            map.update({key: {'positional': [''], 'keyword': {}}})

        if key == 'CURRENT':
            map['CURRENT']['positional'][0] = args[0]
        else:
            for keyword, state in status.items():
                if keyword in self.status_keywords:
                    map[key]['keyword'][keyword] = state
                else:
                    logger.debug('dropping unknown status keyword: "{}"'.format(
                        keyword))

        if not soft:
            super().update(str(self.get_path()), key, *map[key]['positional'],
                **map[key]['keyword'])

    def remove(self, key):
        """Remove entry with key.

        Positional arguments:
        path -- the path of the file [string]
        key -- the key of the data to remove
        """
        super().remove(self.get_path(), key)

    def get_current_key(self):
        """Return the special entry CURRENT."""
        try:
            return self.get_map()['CURRENT']['positional'][0]
        except KeyError:
            return None

    def set_current_key(self, key):
        """Use the CURRENT entry to store the key of the current configuration.

        Positional arguments:
        key -- the key [string]
        """
        self.update('CURRENT', key)
