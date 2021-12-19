#!/usr/bin/env python3

import logging
import multiprocessing
import time

#from . import plugin
from . import listenerplugin

logger = logging.getLogger(__name__)

#class ProcessPlugin(plugin.Plugin):
class ProcessPlugin(listenerplugin.ListenerPlugin):

    def __init__(self, *args, **kwargs):
        #plugin.Plugin.__init__(self, *args, **kwargs)
        listenerplugin.ListenerPlugin.__init__(self, *args, **kwargs)
        self.register('start_processes', self.on_start_processes)
        self.register('stop_processes', self.on_stop_processes)

    def get_process(self):
        return self.__process

    def on_init(self):
        return

    def on_start_processes(self, to_plugins, from_plugins):
        logger.debug('starting {}:'.format(self.get_name()))
        self.__process = multiprocessing.Process(
            name=self.get_name(),
            target=ProcessPlugin.run,
            args=(to_plugins, from_plugins)
        )
        self.get_process().start()

    def on_stop_processes(self):
        self.get_process().terminate()
        self.get_process().join()

    def run(to_plugins, from_plugins):
        do = ['play', 'next', 'stop']
        i = 0
        while True:
            #next_signal = to_plugins.get()
            #if next_signal is None:
            #    # poison pill means shutdown
            #    logger.debug('{}: Exiting'.format(
            #        multiprocessing.current_process().name))
            #    to_plugins.task_done()
            #    break
            while i < len(do):
                print('{}: {}'.format(
                        multiprocessing.current_process().name, do[i]))
                from_plugins.put(do[i])
                i += 1
                time.sleep(1)
            #to_plugins.task_done()
