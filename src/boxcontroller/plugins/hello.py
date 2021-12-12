#!/usr/bin/env python3

import logging

from boxcontroller.plugin import Plugin

logger = logging.getLogger(__name__)

class Hello(Plugin):

    def on_plugins_loaded(self):
        self._smile = ':)'
        self._register('smile', self.smile)

    def smile(self, at=''):
        if at == 'joke':
            print(':D')
        else:
            print(self._smile)
