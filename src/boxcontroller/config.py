#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import configparser
import pkg_resources

logger = logging.getLogger(__name__)

class Config():
    """Representation of the configuration.

    Configuration can be set in two different ways:
    * APPLICATION_PATH/settings/config.ini (application's defaults)
    * ~/.config/boxcontroller/config.ini
    * script params
    Where the latter configurations override the former configurations.
    """

    def __init__(self):
        """Initialise variables and load config from file(s).
        """
        self._reset()

    def load(self):
        config = configparser.ConfigParser(interpolation=None)
        # load from APPLICATION_PATH/settings/config.ini
        path = Path(pkg_resources.resource_filename(__name__,
            'settings/config.ini'))
        config = self._load(config, path)
        # load from ~/.config/boxcontroller
        path = Path.home() / '.config/boxcontroller/config.ini'
        path = path.expanduser().resolve()
        self.__config = self._load(config, path)

    def _reset(self):
        """Reset variables."""
        self.__config = {}
        self.load()

    def _load(self, config, path):
        """Load config from file.

        Positional arguments:
        config -- configparser.ConfigParser()
        path -- Path to load config from
        """
        try:
            with open(path, 'r') as configfile:
                config.read_file(configfile)
        except FileNotFoundError:
            logger.debug('could not open config file at ' + str(path))
        else:
            logger.debug('loaded config from: ' + str(path))
        return config

    def get(self, *args, default=None, variable_type=None):
        """Return the specified configuration or default.

        Positional arguments:
        *args -- string(s), section / key to get

        Keyword arguments:
        default -- the default to return
        variable_type -- string, the type ("int", "float" or "boolean")
        """
        if variable_type == 'int':
            return self.__config.getint(*args, fallback=default)
        elif variable_type == 'float':
            return self.__config.getfloat(*args, fallback=default)
        elif variable_type == 'boolean':
            return self.__config.getboolean(*args, fallback=default)
        else:
            return self.__config.get(*args, fallback=default)

    def set(self, section, field, value):
        """Set a config value manually.

        Positional arguments:
        section -- string the section
        field -- string the key
        value -- string the value to set
        """
        try:
            self.__config[section][field] = value
        except KeyError:
            logger.debug('could not set config value for "'+ str(section) +
                '.' + str(field) + '" to "' + value + '"')
