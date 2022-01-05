#!/usr/bin/env python3

from evdev import InputDevice, ecodes
from select import select
import time
import logging

from boxcontroller.processplugin import ProcessPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Inputusbrfid(ProcessPlugin):
    """Plugin for waiting for text input and sending it to BoxController.

    """

    def __init__(self, *args, **kwargs):
        ProcessPlugin.__init__(self, *args, **kwargs)
        self.__device_path = kwargs['main'].get_config().get('InputUSBRFID',
                'device', default=None)
        if self.__device_path is None:
            logger.error('No device defined')
            return

    def run(self):
        logger.debug('running')
        self.__keys = "X^1234567890XXXXqwertzuiopXXXXasdfghjklXXXXXyxcvbnmXXXXXXXXXXXXXXXXXXXXXXX"
        self.__device = InputDevice(self.__device_path)

        while True:
            time.sleep(0.2)
            card_id = self.read_card()
            self.queue_put(card_id.strip())

        #with open( "/dev/input/event21", "rb" ) as input_handle:
        #    while 1:
        #      data = input_handle.read(24)
        #      print(struct.unpack('4IHHI', data))
        #      ###### PRINT FORMAL = ( Time Stamp_INT , 0 , Time Stamp_DEC , 0 ,
        #      ######   type , code ( key pressed ) , value (press/release) )

    def get_device(self):
        return self.__device

    def get_key(self, code):
        return self.__keys[code]

    def read_card(self):
        string = ''
        key = ''
        while key != 'KEY_ENTER' and not self.get_interrupt_signal():
            select([self.get_device()], [], [])
            for event in self.get_device().read():
                if event.type == 1 and event.value == 1:
                    string += self.get_key(event.code)
                    key = ecodes.KEY[event.code]
        return string[:-1]
