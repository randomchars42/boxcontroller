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

    def register(self, event, callback, exclusive=False):
        """Register to an event.

        Positional arguments:
        event -- the event to register to [string]
        callback -- the function / lambda to call [function]

        Keyword arguments:
        exclusive -- unregister other listeners to this event [boolean]
        """
        self.get_publisher().register_listener(event, self.get_name(),
                callback=callback, exclusive=exclusive)

    def unregister(self, event):
        """Unregister from an event.

        Positional arguments:
        event -- the event to register to [string]
        """
        self.get_publisher().unregister(event, self.get_name())

    def on_init(self):
        raise NotImplementedError('you missed your chance to initialise ' +
                'and register events')

    def send_to_input(self, input_string):
        """Send something to the main plugin for processing as input.

        Positional arguments:
        input_string -- the string to process
        """
        self.get_main().process_input(input_string)

    def register_as_busy_bee(self):
        """Mark this plugin as a busy bee potentially inhibitting shutdown, etc.
        """
        logger.debug('I\'m a busy bee')
        self.get_main().register_busy_bee(self.get_name())

    def mark_as_busy(self, busy=True):
        """Mark this plugin as busy and inhibit actions such as timed shutdown.

        To do this, the plugin must have registered as a busy bee beforehand.

        Keyword arguments:
        busy -- busy (True) or not (False) [boolean]
        """
        logger.debug('setting busy status to {}'.format(str(busy)))
        self.get_main().mark_busy_bee_as_busy(self.get_name(), busy)

    def communicate(self, message, type):
        """Communicate something to the user.

        Boxcontroller will choose appropriate means (playing a sound,
        displaying a message, ...)

        Positional arguments:
        message --  the message to relay [string]
        type -- type of message ("error"|"info") [string]
        """
        logger.info('{}: {}'.format(type, message))
