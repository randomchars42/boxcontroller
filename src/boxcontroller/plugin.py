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
        self.__name = kwargs['name']

    def get_name(self):
        return self.__name
