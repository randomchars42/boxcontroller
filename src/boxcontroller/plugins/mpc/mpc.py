#!/usr/bin/env python3

import subprocess
import logging
import sys

from boxcontroller.plugin import Plugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class MPC(Plugin):

    def on_plugins_loaded(self):
        logger.debug("MPD FTW!")
        self.register('toggle', self.toggle)
        self.register('play', self.play)
        self.register('pause', self.play)
        self.register('stop', self.play)
        self.register('next', self.next)
        self.register('previous', self.previous)
        self.register('volume', self.volume)

    def mpc(self, *args, **kwargs):
        call = ['mpc', '--host=melone', '--verbose']

        if len(args) > 0:
            call += args

        if sys.version_info[1] >= 7:
            # capture output is new and in this case required with python >= 3.7
            return subprocess.run(call, capture_output=True,
                    encoding="utf-8", **kwargs)
        else:
            return subprocess.run(call, encoding="utf-8", **kwargs,
                    stdout=subprocess.PIPE)

    def toggle(self):
        result = self.mpc('toggle')
        print(result.stdout)

    def play(self):
        result = self.mpc('play')
        print(result.stdout)

    def next(self):
        result = self.mpc('next')
        print(result.stdout)

    def previous(self):
        result = self.mpc('prev')
        print(result.stdout)

    def volume(self, direction=None, step=None):
        if not direction in ['+', '-']:
            logger.error('no such action "{}"'.format(action))
            return
        if step is None:
            step = self.get_config().get('MPC', 'volume_step', default="5",
                    variable_type="str")
        result = self.mpc('volume', direction+step)
