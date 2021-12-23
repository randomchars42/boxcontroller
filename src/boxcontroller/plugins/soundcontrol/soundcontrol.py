#!/usr/bin/env python3

import subprocess
import logging
import sys
import re
from pathlib import Path

from boxcontroller.listenerplugin import ListenerPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Soundcontrol(ListenerPlugin):

    def on_init(self):
        self.register('vol_step', self.change_volume, True)
        self.register('vol_max', self.set_max_volume, True)
        self.__volume = 0
        self.__max_volume = None
        self.__step = self.get_config().get('Soundcontrol',
                'step', default=5, variable_type='int')
        self.__path_max_volume = Path(
                self.get_config().get('Paths', 'user_config'),
                self.get_config().get('Soundcontrol', 'path_max_volume',
                    default='max_volume')).expanduser().resolve()
        logger.debug('current volume: {}'.format(str(self.query_volume())))
        logger.debug('max volume: {}'.format(str(self.get_max_volume())))
        self.set_max_volume(50)
        self.change_volume(step='60', direction='+')

    def get_volume(self):
        return self.__volume

    def get_max_volume(self):
        if self.__max_volume is None:
            try:
                logger.debug('reading max volume from file "{}"'.format(
                    self.get_path_max_volume()))
                self.__max_volume = int(
                        self.get_path_max_volume().read_text().strip())
                return self.__max_volume
            except OSError:
                logger.debug('could not open file {}'.format(
                    self.get_path_max_volume()))
                self.__max_volume = 100

        logger.debug('max volume is: {}'.format(str(self.__max_volume)))
        return self.__max_volume

    def set_volume(self, volume):
        self.__volume = int(volume)

    def set_max_volume(self, volume):
        logger.debug('setting max volume to {}'.format(str(volume)))
        self.__max_volume = volume
        self.get_path_max_volume().write_text(str(volume))

    def get_path_max_volume(self):
        return self.__path_max_volume

    def get_step(self):
        return self.__step

    def amixer(self, *args, **kwargs):
        """Call amixer as a subprocess and return its output.

        Positional arguments:
        *args -- one string for each parameter part passed to mpc [string]
        **kwargs -- passed as arguments to subprocess.run()
        """
        call = ['amixer']

        if len(args) > 0:
            call += args

        logger.debug('calling amixer with: {}'.format(','.join(
            [item for item in call])))

        if sys.version_info[1] >= 7:
            # capture output is new and in this case required with python >= 3.7
            result = subprocess.run(call, capture_output=True,
                    encoding="utf-8", **kwargs)
        else:
            result = subprocess.run(call, encoding="utf-8", **kwargs,
                    stdout=subprocess.PIPE)

        raw = result.stdout
        if result.returncode != 0:
            # error
            logger.error('error calling amixer: "{}"'.format(raw.strip()))
            return None
        return raw

    def query_volume(self):
        raw = self.amixer('get', 'Master').split('\n')
        result = re.match(re.compile(
            '\s+[a-zA-Z:]+\s+Playback\s+[0-9]+\s*\[(?P<volume>[0-9]+)%\]'),
            raw[4])
        if not result is None:
            return int(result.groupdict()['volume'])

    def change_volume(self, direction=None, step=None):
        if not direction in ['+', '-']:
            logger.error('no such direction "{}"'.format(direction))
            return

        if step is None:
            step = self.get_step()
        step = int(step)

        logger.debug('changing volume: {}%{}'.format(step, direction))

        max = self.get_max_volume()
        vol = self.query_volume()

        if vol >= max or (direction == '+' and vol + step >= max):
            logger.debug('max volume reached ({}%)'.format(str(max)))
            result = self.amixer('set', 'Master', '{}%'.format(str(max)))
        elif direction == '-' and vol - step <= 0:
            logger.debug('min volume reached')
            result = self.amixer('set', 'Master', '{}%'.format(str(0)))
        else:
            result = self.amixer('set', 'Master', '{}%{}'.format(step, direction))

        if result is None:
            logger.error('could not change volume')
        self.set_volume(self.query_volume())
