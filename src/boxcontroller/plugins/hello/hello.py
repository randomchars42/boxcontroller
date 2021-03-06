#!/usr/bin/env python3

import logging

from boxcontroller.listenerplugin import ListenerPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Hello(ListenerPlugin):
    """Example plugin.

    Initialises on on_plugins_loaded().
    """

    def on_init(self):
        self._smile = self.get_config().get('Hello', 'smile')
        self.register('smile', self.smile)

    def smile(self, at=''):
        if at == 'joke':
            logger.debug(':D')
        else:
            logger.debug(self._smile)
