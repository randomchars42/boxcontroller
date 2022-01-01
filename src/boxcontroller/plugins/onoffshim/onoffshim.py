#!/usr/bin/env python3

from gpiodmonitor.gpiodmonitor import GPIODMonitor
import time
import gpiod
import logging

from boxcontroller.processplugin import ProcessPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Onoffshim(ProcessPlugin):
    """Plugin for waiting for GPIO input and initiating shutdown.

    Shutdown using the Pimoroni OnOffShim is a two step process:
    - listening on a pin for a signal (default GPIO 17) and calling shutdown -P
      if the button is pressed
    - switching of the power supply to the raspberry pi by pulling down the
      poweroff pin (GPIO 4)
      this immediatly cuts the power supply so it cannot be done within this
      script
      put this into /usr/lib/systemd/system-shutdown/boxcontroller.shutdown:

        #! /bin/sh
        # https://newbedev.com/how-to-run-a-script-with-systemd-right-before-shutdown
        # https://github.com/pimoroni/clean-shutdown/blob/master/daemon/lib/systemd/system-shutdown/gpio-poweroff
        # $1 will be either "halt", "poweroff", "reboot" or "kexec"
        poweroff_pin=4
        case "$1" in
            poweroff)
                # with libgpiod2:
                /bin/sleep 0.5
                /bin/gpioset gpiochip0 $poweroff_pin=0
                # without libgpiod2:
                #/bin/echo $poweroff_pin > /sys/class/gpio/export
                #/bin/echo out > /sys/class/gpio/gpio$poweroff_pin/direction
                #/bin/echo 0 > /sys/class/gpio/gpio$poweroff_pin/value
                #/bin/sleep 0.5
                ;;
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
        if self.__chip is None or len(self.__pin) < 2:
            logger.error('No chip or pins defined')
            return

    def get_chip(self):
        return self.__chip

    def get_pin(self, type):
        return self.__pin[type]

    def on_pressed(self, pin):
        logger.debug('shutdown pin pressed'.format(pin))
        self.queue_put('shutdown')

    def run(self):
        monitor = GPIODMonitor(self.get_chip())
        monitor.register_long_press(self.get_pin('listen'),
            self.on_pressed,
            3)
        logger.debug('listening to shutdown pin')
        monitor.run()


