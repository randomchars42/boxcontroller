#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import pkg_resources

from . import keymap

logger = logging.getLogger(__name__)

class EventMap(keymap.KeyMap):
    """Representation of the two event map files.

    Events are mapped in two different files:
    * APPLICATION_PATH/settings/eventmap (application's defaults)
    * ~/.config/boxcontroller/eventmap
    Whereas events from the latter file override events from the former.

    Events are specified one per line.
    For the general form see Commands.process_map().
    """

    def __init__(self, config):
        """Initialise variables and load map from file(s)."""
        super().__init__(config)
        self.__path_user_map = Path(self.get_config().get('Paths', 'eventmap'))
        self.__path_user_map = self.__path_user_map.expanduser().resolve()
        self.reset()

    def reset(self):
        """Reset variables."""
        super().reset()
        self.load()

    def get_path_user_map(self):
        return self.__path_user_map

    def load(self):
        """(Re-)read the mapping files.

        Can be used to insert new mappings into the running system.
        """
        # load from APPLICATION_PATH/settings/events
        path = Path(pkg_resources.resource_filename(__name__,
            'settings/eventmap'))
        super().load(path)
        # load from ~/.config/boxcontroller
        super().load(self.get_path_user_map())

    def get(self, key):
        """Return the event mapped to the key or None.

        Positional arguments:
        key -- the key [string]

        Returns:
        (event [string], ['positional': [string], 'keyword': {string: string}]
        """
        try:
            data = self.get_map()[key]
            return (
                    data['positional'][0],
                    {
                        'positional': data['positional'][1:],
                        'keyword': data['keyword'].copy()
                    }
                    )
        except KeyError:
            logger.error('no event for key: "{}"'.format(key))
            raise KeyError

    def update(self, key, event, *args, **kwargs):
        """Update, add or delete the mapping of an event.

        Positional arguments:
        key -- the key [string]
        event -- name of the event [string], pass [None] to remove entry
        *args -- positional data [string], leave empty to remove entry
        **params -- keyworded data [string: string], leave empty to remove entry
        """
        if event is None:
            self.remove(key)
        args = [event, *args]
        super().update(self.get_path_user_map(), key, *args,
                **kwargs)

    def remove(self, key):
        """Remove entry with key.

        Positional arguments:
        path -- the path of the file [string]
        key -- the key of the data to remove
        """
        super().remove(self.get_path_user_map(), key)
