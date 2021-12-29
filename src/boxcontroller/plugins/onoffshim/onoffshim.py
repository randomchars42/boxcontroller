#!/usr/bin/env python3

from gpiodmonitor.gpiodmonitor import GPIODMonitor
import time
import gpiod
import logging

from boxcontroller.processplugin import ProcessPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Onoffshim(ProcessPlugin):
    """Plugin for waiting for GPIO input using libgpiod.

    """

    def __init__(self, *args, **kwargs):
        ProcessPlugin.__init__(self, *args, **kwargs)
        self.__chip = kwargs['main'].get_config().get('OnOffShim',
                'chip', default=None, variable_type='int')
        self.__pin = {}
        self.__pin['shutdown'] = kwargs['main'].get_config().get('OnOffShim',
                'pin_shutdown', default=4, variable_type='int')
        self.__pin['listen'] = kwargs['main'].get_config().get('OnOffShim',
                'pin_listen', default=17, variable_type='int')
        self.__time_pressed = 0
        if self.__chip is None or len(self.__pin) < 2:
            logger.error('No chip or pins defined')
            return

    def get_chip(self):
        return self.__chip

    def get_pin(self, type):
        return self.__pin[type]

    def on_pressed(self, pin):
        logger.debug('GPIO {} pressed'.format(pin))
        self.__time_pressed = time.time()

    def on_released(self, pin):
        logger.debug('GPIO {} released'.format(pin))
        diff = int(time.time() - self.__time_pressed)
        logger.debug('GPIO {} held for {} seconds'.format(pin, diff))
        if diff > 1:
            logger.debug('triggering shutdown')
            logger.debug('pulling down shutdown pin')
            # pull down the pin so the button can trigger next boot
            with gpiod.Chip(self.get_chip()) as chip:
                lines = chip.get_lines([self.get_pin('shutdown')])
                lines.request(consumer='boxcontroller.plugins.onoffshim',
                        type=gpiod.LINE_REQ_DIR_OUT)
                lines.set_values([0])
            self.queue_put('shutdown')

    def run(self):
        monitor = GPIODMonitor(self.get_chip())
        monitor.register(self.get_pin('listen'),
            on_pressed = lambda pin: self.on_pressed(pin),
            on_released = lambda pin: self.on_released(pin))
        logger.debug('listening to shutdown pin')
        monitor.run()


