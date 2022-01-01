#!/usr/bin/env python3

import logging
import time
import threading

from boxcontroller.listenerplugin import ListenerPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Shutdowntimer(ListenerPlugin):
    """Request shutdown after X minutes of idle time."""

    def on_init(self):
        self.register('idle', self.on_idle)
        self.register('busy', self.on_stop)
        self.register('stop', self.on_stop)

        self.__idle_time = self.get_config().get('ShutdownTimer', 'idle_time',
                default=300, variable_type='int')
        self.__shutdown_at = None

        self.__thread = None
        self.__stop_event = threading.Event()

    def get_idle_time(self):
        return self.__idle_time

    def get_shutdown_time(self):
        return self.__shutdown_at

    def set_shutdown_time(self, time=None):
        self.__shutdown_at = time

    def get_thread(self, new=False):
        if new:
            self.__thread = threading.Thread(target=self.countdown,
                    args=(self.get_stop_event(),))
            return self.__thread
        return self.__thread

    def get_stop_event(self):
        return self.__stop_event

    def on_idle(self):
        """Start countdown"""
        if self.get_shutdown_time() is None:
            logger.debug('beginning countdown for shutdown in {} seconds'.format(
                self.get_idle_time()))
            self.set_shutdown_time(int(time.time()) + self.get_idle_time())

            self.get_stop_event().clear()
            thread = self.get_thread(new=True)
            thread.start()
        else:
            logger.debug('already idle')

    def on_stop(self):
        """Send stop signal to thread counting down."""
        logger.debug('stopping countdown for shutdown')
        if self.get_shutdown_time() is not None:
            self.get_stop_event().set()
            self.get_thread().join()
            self.set_shutdown_time()
        else:
           logger.debug('no countdown set')

    def countdown(self, stop_event):
        """Check if it's time to shutdown

        Positional arguments:
        stop_event -- stops the thread if set [threading.Event]
        """
        shutdown = False
        while not stop_event.wait(5):
            if int(time.time()) >= self.get_shutdown_time():
                logger.debug('shutdown timer expired')
                shutdown = True
                self.get_stop_event().set()
                break
        logger.debug('stopped countdown')
        if shutdown:
            print('shudtdown')
