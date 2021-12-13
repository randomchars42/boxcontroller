#!/usr/bin/env python3

import logging

logger = logging.getLogger(__name__)

class Plugin:
    """Base class for plugins"""

    def __init__(self, *args, **kwargs):
        """Initialise variables and register to "plugins_loaded".

        Try not to overwrite this method. Use on_plugins_loaded instead for
        initialisation of variables.

        If you must, do not forget to call this constructor:
        super(Plugin, self).__init__(*args, **kwargs)
        """
        self.__publisher = kwargs['publisher']
        self.__config = kwargs['config']
        self.__name = kwargs['name']
        self.register('on_init', self.on_init)

    def get_name(self):
        return self.__name

    def get_config(self):
        return self.__config

    def get_publisher(self):
        return self.__publisher

    def register(self, event, callback):
        """Register to an event.

        Positional arguments:
        event -- the event to register to [string]
        callback -- the function / lambda to call
        """
        self.get_publisher().register(event, self.get_name(), callback)

    def unregister(self, event):
        """Unregister from an event.

        Positional arguments:
        event -- the event to register to [string]
        """
        self.get_publisher().unregister(event, self.get_name())

    def on_init(self):
        raise NotImplementedError('you missed your chance to initialise ' +
                'and register events')
