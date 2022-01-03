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

        pins = kwargs['main'].get_config().get('InputGPIOD',
                'pins_long_press', default='')
        self.__long_press_pins = [int(pin) for pin in pins.split(',')]

        self.__long_press = kwargs['main'].get_config().get('InputGPIOD',
                'long_press', default=3, variable_type='int')

        if self.__chip is None or len(self.__pins) == 0:
            logger.error('No chip or pins defined')
            return

    def get_chip(self):
        return self.__chip

    def get_pins(self):
        return self.__pins

    def get_long_press_pins(self):
        return self.__long_press_pins

    def get_long_press_duration(self):
        return self.__long_press

    def on_pressed(self, pin):
        logger.debug('GPIO {} pressed'.format(pin))
        self.queue_put('GPIO_{}_P'.format(str(pin)))

    def on_long_pressed(self, pin):
        logger.debug('GPIO {} pressed for {}'.format(pin,
            self.get_long_press_duration()))
        self.queue_put('GPIO_{}_L'.format(str(pin)))

    def run(self):
        monitor = GPIODMonitor(self.__chip)
        for gpio_pin in self.get_pins():
            monitor.register(gpio_pin,
                on_pressed=lambda pin,time: self.on_pressed(pin))
        for gpio_pin in self.get_long_press_pins():
            monitor.register(gpio_pin,
                lambda pin,time: self.on_pressed(pin),
                self.get_long_press_duration)
        logger.debug('listening to pins')
        monitor.run()


