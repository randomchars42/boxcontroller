#!/usr/bin/env python3

from gpiodmonitor.gpiodmonitor import GPIODMonitor
import time
import logging

from boxcontroller.processplugin import ProcessPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Inputgpiod(ProcessPlugin):
    """Plugin for waiting for GPIO input using libgpiod.

    """

    def __init__(self, *args, **kwargs):
        ProcessPlugin.__init__(self, *args, **kwargs)
        self.__chip = kwargs['main'].get_config().get('InputGPIOD',
                'chip', default=None, variable_type='int')
        pins = kwargs['main'].get_config().get('InputGPIOD',
                'pins', default='')
        self.__pins = [int(pin) for pin in pins.split(',')]
        if self.__chip is None or len(self.__pins) == 0:
            logger.error('No chip or pins defined')
            return

    def get_chip(self):
        return self.__chip

    def get_pins(self):
        return self.__pins

    def on_pressed(self, pin):
        logger.debug('GPIO {} pressed'.format(pin))
        self.queue_put('GPIO_{}_P'.format(str(pin)))

    def on_released(self, pin):
        logger.debug('GPIO {} released'.format(pin))
        self.queue_put('GPIO_{}_R'.format(str(pin)))

    def run(self):
        monitor = GPIODMonitor(self.__chip)
        for pin in self.__pins:
            monitor.register(pin,
                on_pressed = lambda: self.on_pressed(pin),
                on_released = lambda: self.on_released(pin))
        logger.debug('listening to pins')
        monitor.run()


