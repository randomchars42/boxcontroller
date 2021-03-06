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
                self.__max_volume = self.get_config().get(
                        'Soundcontrol', 'max_volume',
                        default=100, variable_type="int")

        logger.debug('max volume is: {}'.format(str(self.__max_volume)))
        return self.__max_volume

    def set_volume(self, volume):
        self.__volume = int(volume)

    def set_max_volume(self, volume):
        logger.debug('setting max volume to {}'.format(str(volume)))
        volume = int(volume)
        self.__max_volume = volume
        self.get_path_max_volume().write_text(str(volume))
        if self.get_volume() > volume:
            self.change_volume(abs=volume)

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
        # if Master is stereo this will only capture the left line and we infer
        # that this also holds true for the right line
        result = re.match(re.compile(
            '\s+[a-zA-Z :]+\s+[0-9]+\s*\[(?P<volume>[0-9]+)%\]'),
            raw[5])
        if not result is None:
            vol = int(result.groupdict()['volume'])
        else:
            vol = self.get_max_volume()
        logger.debug('current volume: {}'.format(vol))
        return vol

    def change_volume(self, abs=None, direction=None, step=None):
        max = self.get_max_volume()
        if not abs is None:
            # set volume to X %
            abs = int(abs)
            if abs >= max:
                logger.debug('max volume reached ({}%)'.format(str(max)))
                result = self.amixer('set', 'Master', '{}%'.format(str(max)))
            elif abs <= 0:
                logger.debug('min volume reached')
                result = self.amixer('set', 'Master', '{}%'.format(str(0)))
            else:
                logger.debgu('setting volume to {}'.format(str(abs)))
                result = self.amixer('set', 'Master', '{}%'.format(str(abs)))
        else:
            # increase / decrease volume in steps of X %
            if not direction in ['+', '-']:
                logger.error('no such direction "{}"'.format(direction))
                return

            if step is None:
                step = self.get_step()
            step = int(step)

            vol = self.query_volume()

            if direction == '-' and vol - step <= 0:
                logger.debug('min volume reached')
                result = self.amixer('set', 'Master', '{}%'.format(str(0)))
            elif direction == '+' and vol + step >= max:
                logger.debug('max volume reached ({}%)'.format(str(max)))
                result = self.amixer('set', 'Master', '{}%'.format(str(max)))
            else:
                logger.debug('{}{} %'.format(str(direction), str(step)))
                result = self.amixer('set', 'Master', '{}%{}'.format(str(step),
                    str(direction)))

        if result is None:
            logger.error('could not change volume')
        self.set_volume(self.query_volume())
