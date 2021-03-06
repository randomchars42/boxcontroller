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
        self.register('busy', self.stop_countdown)
        self.register('terminate', self.on_terminate)

        self.__idle_time = self.get_config().get('ShutdownTimer', 'idle_time',
                default=300, variable_type='int')
        self.__shutdown_at = None

        self.__thread = None
        self.__stop_event = threading.Event()

    def on_terminate(self):
        self.stop_countdown()
        self.unregister('idle')
        self.unregister('busy')

    def get_idle_time(self):
        return self.__idle_time

    def get_shutdown_time(self):
        return self.__shutdown_at

    def set_shutdown_time(self, shutdown_time=None):
        if shutdown_time is None:
            self.__shutdown_at = None
        elif self.get_shutdown_time() is not None:
            logger.error('cannot set shutdown time, already set')
            return

        #logger.debug('now: {}'.format(
        #    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        #logger.debug('shutdown: {}'.format(
        #    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(shutdown_time))))
        self.__shutdown_at = shutdown_time
        logger.debug('setting shutdown time to {}'.format(shutdown_time))

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
            self.set_shutdown_time(self.get_idle_time())

            self.get_stop_event().clear()
            thread = self.get_thread(new=True)
            thread.start()
            logger.debug('started thread')
        else:
            logger.debug('already idle')

    def stop_countdown(self):
        """Send stop signal to thread counting down."""
        logger.debug('stopping countdown for shutdown')
        if self.get_shutdown_time() is not None:
            self.get_stop_event().set()
            self.get_thread().join()
            self.set_shutdown_time()
            logger.debug('countdown stopped')
        else:
           logger.debug('no countdown set')

    def countdown(self, stop_event):
        """Check if it's time to shutdown

        Use a real countdown isntead of checking if we reached shutdown time
        for after boot the system time might be changed by ntpd and produce
        weird outcomes.

        Positional arguments:
        stop_event -- stops the thread if set [threading.Event]
        """
        shutdown = False
        while not stop_event.wait(5):
            self.__shutdown_at = self.get_shutdown_time() - 5
            if self.get_shutdown_time() <= 0:
                logger.debug('shutdown timer expired')
                shutdown = True
                self.get_stop_event().set()
                self.set_shutdown_time()
                break
        logger.debug('stopped countdown')
        if shutdown:
            self.send_to_input('shutdown')
