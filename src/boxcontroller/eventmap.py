#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import pkg_resources

logger = logging.getLogger(__name__)

class EventMap():
    """Representation of the two event map files.

    Events are mapped in two different files:
    * APPLICATION_PATH/settings/eventmap (application's defaults)
    * ~/.config/boxcontroller/eventmap
    Whereas events from the latter file override events from the former.

    Events are specified one per line.
    For the general form see Commands.process_map().
    """

    def __init__(self):
        """Initialise variables and load map from file(s)."""
        self._path_user_map = Path.home() / '.config/boxcontroller/eventmap'
        self._path_user_map = self._path_user_map.expanduser().resolve()
        self._reset()

    def _reset(self):
        """Reset variables."""
        self.__map = {}
        self.load()

    def load(self):
        """(Re-)read the mapping files.

        Can be used to insert new mappings into the running system.
        """
        # load from APPLICATION_PATH/settings/events
        path = Path(pkg_resources.resource_filename(__name__,
            'settings/eventmap'))
        self.__map = self._load(path)
        # load from ~/.config/boxcontroller
        self.__map.update(self._load(self._path_user_map))

    def _load(self, path):
        """Load event map from file.

        Each line should look like:
        KEY EVENTNAME PARAM1=VALUE1 PARAM2=VALUE2 ...

        Positional arguments:
        path -- Path to load event map from
        """
        mapping = {}
        try:
            with open(path, 'r') as event_map:
                lines = event_map.readlines()
            for line in lines:
                try:
                    key, event, params = self._process_map(line)
                    mapping[key] = {
                            'name': event,
                            'params': params
                            }
                except ValueError:
                    logger.error('malformed: "{}"'.format(line))
                    continue
        except FileNotFoundError:
            logger.debug('could not open file at ' + str(path))
        else:
            logger.debug('loaded eventmap from: ' + str(path))
        return mapping

    def _process_map(self, raw_map):
        """Process a mapping line.

        Mapping lines are formatted like this:
        KEY EVENT

        Positional arguments:
        raw_map -- the raw map to parse [string]
        """
        if raw_map == '':
            raise ValueError('empty mapping given')

        (key, rest) = raw_map.strip().split(' ', 1)
        return (key, *self._process_event(rest))

    def _process_event(self, raw_event):
        """Process the string representation of an event.

        EVENTs are represented like this:
        EVENTNAME PARAM1=VALUE1 PARAM2=VALUE2 ...

        Positional arguments:
        raw_event -- the raw event to parse [string]
        """
        raw_event = raw_event.strip().split(' ')
        parameters = {}
        event, *params = [item for item in raw_event if item != '']
        for param in params:
            name, value = param.split("=", 1)
            parameters[name] = value
        return (event, parameters)

    def get(self, key):
        """Return the event mapped to the key or None.

        Positional arguments:
        key -- the key [string]
        """
        try:
            return self.__map[key]
        except KeyError:
            logger.error('no event for key: "{}"'.format(key))
            return None

    def _to_map_line(self, key, event, **params):
        """Convert params to an event map line.

        Positional arguements:
        key -- the key that gets input [string]
        event -- name of the event [string] or remove with [None]
        **params -- additional parameters
        """
        # TODO add some checking
        param_string = ' '.join(
                ['{}={}'.format(key, value) for (key, value) in params.items()])
        return '{} {} {}'.format(key, event, param_string)

    def update(self, key, event, **params):
        """Update, add or delete the mapping of an event.

        Positional arguements:
        key -- the key that gets input [string]
        event -- name of the event [string] or remove with [None]
        **params -- additional parameters
        """
        try:
            with open(self._path_user_map, 'r') as event_map:
                lines = event_map.readlines()
        except FileNotFoundError:
            logger.debug('could not open file at ' + str(self._path_user_map))
            lines = []

        key_length = len(key)
        done = False

        for i, line in enumerate(lines):
            if line[:key_length + 1] == key + ' ':
                # the key is already mapped
                # make sure we don't accidentally catch a longer key by adding
                # the required blank to the end of the key
                if event is not None:
                    # update the mapping
                    lines[i] = self._to_map_line(key, event, **params)
                    done = True
                    logger.info('update event for key "{}"'.format(key))
                else:
                    # remove the mapping
                    lines[i].pop(i)
                    done = True
                    logger.info('update event for key "{}"'.format(key))
                break

        if not done and not event is None:
            # there was no mapping so append it
            lines.append(self._to_map_line(key, event, **params))
            logger.info('added event for key "{}"'.format(key))

        with open(self._path_user_map, 'w') as event_map:
            event_map.write('\n'.join(lines))
            logger.debug('updated event map ("{}")'.format(self._path_user_map))

        self._reset()
