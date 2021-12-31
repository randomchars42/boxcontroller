#!/usr/bin/env python3

import pkg_resources
import subprocess
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
        self._audio_current = None
        self.register('finished_loading', lambda: self.play_sound('ready'))
        self.register('before_shutdown', lambda: self.play_sound('shutdown'))
        self.register('error', lambda: self.play_sound('error'))
        self._path_sounds = Path(self.get_config().get('Soundeffect',
                'path',
                default=pkg_resources.resource_filename(__name__, 'sounds')))

    def play_sound(self, sound):
        sound = self.get_config().get('Soundeffect', sound, default=None)
        if sound is None:
            logger.error('no such sound configured: "{}"'.format(str(sound)))
            return
        # check if an audio process has been created and has not returned yet
        if not self._audio_current or not self._audio_current.poll() == None:
            self._audio_current = subprocess.Popen(["/usr/bin/aplay", self._path_sounds / sound])
