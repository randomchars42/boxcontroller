#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import pkg_resources

logger = logging.getLogger(__name__)

class KeyMap():
    """Textual representation of simple data where a database would be too much.

    Information is stored in a plain utf-8 textfile like this:
    KEY|DATUM1|KEYWORD2=DATUM2|KEYWORD3=DATUM3|...

    The default delimiter is "|" but can be changed in the config.

    Information is looked up by key.
    """

    def __init__(self, config):
        """Initialise variables and load map from file(s)."""
        self.__config = config
        self.__delimiter = config.get('Mapping', 'delimiter', default='|')

    def reset(self):
        """Reset variables."""
        self.__map = {}

    def get_delimiter(self):
        return self.__delimiter

    def get_config(self):
        return self.__config

    def get_map(self):
        return self.__map

    def load(self, path):
        """Load map from file.

        Positional arguments:
        path -- Path to load the map from
        """
        mapping = {}
        try:
            with open(path, 'r') as map:
                lines = map.readlines()
            for line in lines:
                line = line.strip()
                try:
                    key, data = self._process_map(line)
                    mapping[key] = data
                except ValueError:
                    logger.error('malformed: "{}"'.format(line))
                    continue
        except FileNotFoundError:
            logger.debug('could not open file at ' + str(path))
        else:
            logger.debug('loaded map: "{}"'.format(str(path)))
        self.__map.update(mapping)

    def _process_map(self, raw_map):
        """Process a mapping line.

        Mapping lines are formatted like this:
        KEY|DATUM1|KEYWORD2=DATUM2|KEYWORD3=DATUM3|...

        Positional arguments:
        raw_map -- the raw map to parse [string]
        """
        if raw_map == '':
            raise ValueError('empty mapping given')

        key, *rest = raw_map.split(self.get_delimiter())

        data = {'positional': [], 'keyword': {}}

        for raw in rest:
            raw = raw.strip()
            pieces = raw.split('=', 1)
            if len(pieces) == 1:
                data['positional'].append(pieces[0])
            else:
                data['keyword'][pieces[0]] = pieces[1]

        return (key, data)

    def get(self, key):
        """Return the entry mapped to the key or None.

        Positional arguments:
        key -- the key [string]
        """
        try:
            return self._get_map()[key]
        except KeyError:
            logger.error('no entry for key: "{}"'.format(key))
            return None

    def _to_map_line(self, key, args, kwargs):
        """Convert params to a map line.

        Positional arguments:
        key -- the key [string]
        args -- positional data [string]
        kwargs -- keyworded data [string: string]
        """
        # TODO add some checking
        flattend_kwargs = ['{}={}'.format(key, value)
                for (key, value) in kwargs.items()]
        return self.get_delimiter().join([key, *args, *flattend_kwargs])

    def update(self, path, mapkey, *args, **kwargs):
        """Update, add or delete an entry.

        Positional arguments:
        path -- the path of the file [string]
        mapkey -- the key [string]
        *args -- positional data [string], leave empty to remove entry
        **params -- keyworded data [string: string], leave empty to remove entry
        """
        logger.debug('updating keymap at "{}" for key "{}" with: {},{}'.format(
            path, mapkey, ','.join(args), ','.join(
                ['{}={}'.format(kw,v) for kw,v in kwargs.items()])))
        try:
            with open(path, 'r') as map:
                lines = map.readlines()
        except FileNotFoundError:
            logger.debug('could not open file at ' + str(path))
            lines = []

        key_length = len(mapkey)
        done = False

        for i, line in enumerate(lines):
            if line[:key_length + 1] == mapkey + self.get_delimiter():
                # the key is already mapped
                # make sure we don't accidentally catch a longer key by adding
                # the required delimiter to the end of the key
                if len(args) > 0 or len(kwargs) > 0:
                    # update the mapping
                    print(i)
                    print(lines[i])
                    lines[i] = self._to_map_line(mapkey, args, kwargs) + '\n'
                    print(lines[i])
                    logger.debug('updated entry for key "{}"'.format(mapkey))
                else:
                    # remove the mapping
                    lines.pop(i)
                    logger.debug('removed entry for key "{}"'.format(mapkey))
                done = True
                break

        if not done and (len(args) > 0 or len(kwargs) > 0):
            # there was no mapping so append it
            lines.append(self._to_map_line(mapkey, args, kwargs) + '\n')
            logger.info('added entry for key "{}"'.format(mapkey))

        path = Path(path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True,exist_ok=True)

        with open(path, 'w') as map:
            map.write(''.join(lines))
            logger.debug('updated map: "{}"'.format(path))

        self.reset()

    def remove(self, path, key):
        """Remove entry with key.

        Positional arguments:
        path -- the path of the file [string]
        key -- the key of the data to remove
        """
        self.update(path, key)
