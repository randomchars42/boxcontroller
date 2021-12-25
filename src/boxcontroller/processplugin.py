#!/usr/bin/env python3

import logging
import multiprocessing

from . import plugin

logger = logging.getLogger(__name__)

class ProcessPlugin(plugin.Plugin, multiprocessing.Process):
    """Base class for plugins using their own process.

    Modified after: https://pymotw.com/3/multiprocessing/communication.html
    """

    def __init__(self, *args, **kwargs):
        """Register with main process to be started and store queues.

        If you need to overwrite this function don't forget to use:
        ProcessPlugin.__init__(self, *args, **kwargs)
        """
        plugin.Plugin.__init__(self, *args, **kwargs)
        multiprocessing.Process.__init__(self)
        kwargs['main'].register_process(self.get_name(), self)
        self.__to_plugins = kwargs['to_plugins']
        self.__from_plugins = kwargs['from_plugins']

    def queue_get(self):
        """Get messages off the queue."""
        return self.__to_plugins.get()

    def queue_put(self, input_string):
        """Put string messages onto the queue.

        Positional arguments:
        input_string -- the string that will become input for BoxController
        """
        return self.__from_plugins.put(input_string)

    def run(self):
        raise NotImplementedError('Overwrite this method to get your process ' +
                'running.')

    def __del__(self):
        logger.debug('{} is stopping'.format(self.get_name()))
