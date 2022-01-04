#!/usr/bin/env python3

import pkg_resources
import subprocess
import sys
from pathlib import Path
import logging

from boxcontroller.listenerplugin import ListenerPlugin

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Soundeffect(ListenerPlugin):
    """Example plugin.

    Initialises on on_plugins_loaded().
    """

    def on_init(self):
        # subprocess for playing sounds
        self.register('finished_loading', lambda: self.play_sound('ready'))
        self.register('before_shutdown', lambda: self.play_sound('shutdown'))
        self.register('error', lambda: self.play_sound('error'))
        self.register('feedback', lambda: self.play_sound('feedback'))
        self._path_sounds = Path(self.get_config().get('Soundeffect',
                'path',
                default=pkg_resources.resource_filename(__name__, 'sounds')))

    def play_sound(self, sound):
        sound = self.get_config().get('Soundeffect', sound, default=None)
        if sound is None:
            logger.error('no such sound configured: "{}"'.format(str(sound)))
            return
        call = ["/usr/bin/aplay", "-N", self._path_sounds / sound]
        if sys.version_info[1] >= 7:
            # capture output is new and in this case required with python >= 3.7
            result = subprocess.run(call, capture_output=True,
                    encoding="utf-8")
        else:
            result = subprocess.run(call, encoding="utf-8",
                    stdout=subprocess.PIPE)

        raw = result.stdout
        if result.returncode != 0:
            logger.error('could not play sound "{}"'.format(sound))
