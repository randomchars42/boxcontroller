#!/usr/bin/env python3

import logging
from . import plugin

logger = logging.getLogger(__name__)

class ListenerPlugin(plugin.Plugin):
    """Base for plugins listening to events in the same thread / process."""

    def __init__(self, *args, **kwargs):
        """Initialise variables and register to "plugins_loaded".

        Try not to overwrite this method. Use on_plugins_loaded instead for
        initialisation of variables.

        If you must, do not forget to call this constructor:
        super(Plugin, self).__init__(*args, **kwargs)
        """
        plugin.Plugin.__init__(self, *args, **kwargs)
        self.__main = kwargs['main']
        self.register('init', self.on_init)

    def get_publisher(self):
        return self.get_main()

    def get_main(self):
        return self.__main

    def get_config(self):
        return self.get_main().get_config()

    def register(self, event, callback):
        """Register to an event.

        Positional arguments:
        event -- the event to register to [string]
        callback -- the function / lambda to call
        """
        self.get_publisher().register_listener(event, self.get_name(),
                callback)

    def unregister(self, event):
        """Unregister from an event.

        Positional arguments:
        event -- the event to register to [string]
        """
        self.get_publisher().unregister(event, self.get_name())

    def on_init(self):
        raise NotImplementedError('you missed your chance to initialise ' +
                'and register events')

    def communicate(self, message, type):
        """Communicate something to the user.

        Boxcontroller will choose appropriate means (playing a sound,
        displaying a message, ...)

        Positional arguments:
        message --  the message to relay [string]
        type -- type of message ("error"|"info") [string]
        """
        logger.info('{}: {}'.format(type, message))
