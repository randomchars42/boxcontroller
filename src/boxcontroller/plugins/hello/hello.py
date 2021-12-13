#!/usr/bin/env python3

import logging

from boxcontroller.plugin import Plugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Hello(Plugin):
    """Example plugin.

    Initialises on on_plugins_loaded().
    """

    def on_plugins_loaded(self):
        self._smile = self.get_config().get('Hello', 'smile')
        self.register('smile', self.smile)

    def smile(self, at=''):
        if at == 'joke':
            logger.debug(':D')
        else:
            logger.debug(self._smile)
