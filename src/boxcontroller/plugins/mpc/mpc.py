#!/usr/bin/env python3

import subprocess
import logging
import sys
import re
import hashlib

from boxcontroller.plugin import Plugin
from . import statusmap

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Mpc(Plugin):

    def on_init(self):
        self.__statusmap = statusmap.StatusMap(self.get_config())
        self.register('play', self.play)
        self.register('toggle', lambda: self.simple_command('toggle')))
        self.register('stop', lambda: self.simple_command('stop')))
        self.register('next', lambda: self.simple_command('next')))
        self.register('previous', lambda: self.simple_command('previous'))
        self.register('volume', self.volume)
        self.register('toggle', self.test)

    def test(self):
        self.query_mpd_status()

    def get_statusmap(self):
        return self.__statusmap

    def get_empty_status(self):
        """Return an empty dict with all keys stored in the file.

        All those information can be gathered from mpc except the key and type
        which are stored in #CURRENT.
        """
        return {
                'key': '',
                'type': '',
                'status': '',
                'volume': '',
                'position': '',
                'time': '',
                'file': '',
                'name': '',
                'repeat': '',
                'random': '',
                'single': '',
                'consume': ''
                }.copy()

    def get_status(self, key, parameter = None):
        """Return the status for key.

        Positional arguments:
        key -- the key [string]
        parameter -- what to return, returns all if parameter == None [string]
        """
        if key == 'key':
            return self.get_key()
        return self.__status.get(status, key, parameter)

    def set_status(self, **kwargs)
        """Update the internal status (does not change the file)."""
        for key, value in kwargs.items():
            if not key in self.__status:
                raise KeyError('"{}" is not part of the status'.format(key))
            self.__status[key] = str(value)

    def get_key(self):
        """Get the current key, will be loaded from status map if needed."""
        if self.get_status()['key'] == '':
            self.load_current()
        return self.get_status()['key']

    def get_type(self):
        """Get the current type, will be loaded from status map if needed."""
        if self.get_status()['type'] == '':
            self.load_current()
        return self.get_status()['type']

    def load_current(self):
        """Get the key of the current / last played playlist or folder."""
        current = self.get_statusmap().get_current()
        if current is None:
            raise ValueError('#CURRENT not defined')
        self.get_status().update(current)

    def persist_current(self, key, type):
        """Set the key of the current / last played playlist or folder."""
        self.get_statusmap().set_current(key, type)

    def load_status(self):
        """Load the status of the currently / last played folder or list."""
        self.set_status(**self.get_statusmap().get(self.get_current_key()))

    def persist_status(self, status):
        """Write status to the status map."""
        self.get_statusmap().update(self.get_current_key(), **status)

    def mpc(self, *args, **kwargs):
        """Call mpc as a subprocess and return its output.

        Positional arguments:
        *args -- one string for each parameter part passed to mpc [string]
        **kwargs -- passed as arguments to subprocess.run()
        """
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

    def query_mpd_status(self):
        """Query the status (filename, position, name, volume, status)."""
        # get the status and remove the last character as it is a "\n"
        raw = self.mpc('status', '-f', '%file%@@%position%@@%name%').stdout[:-1]
        raw = raw.split('\n')

        status = {}

        if len(raw) == 1:
            # not playing
            # that's the only information we can get
            return status.update({'status': 'stopped'})

        # line 1 looks like
        # FILENAME@@POSITION@@NAME
        status['file'], status['position'], status['name'] = raw[0].split('@@')
        # line 2 looks like
        # [STATUS] #POSITION/MAX_POSITION TIME/MAX_TIME (PERCENT%)
        result = re.match(re.compile(
            '\[(?P<status>\w+)\]\s+#(?P<position>[0-9]+)/[0-9]+\s+' +
            '(?P<time>[0-9:]+)/[0-9:]+\s+\([0-9]+%\)'), raw[1])
        status.update(result.groupdict())
        # line 3 looks like
        # volume:VOLUME%   repeat: off random: off single: off consume: off
        result = re.match(re.compile(
            'volume:\s*(?P<volume>[0-9]+)%\s+repeat:\s*(?P<repeat>[a-z]+)\s+' +
            'random:\s*(?P<random>[a-z]+)\s+single:\s*(?P<single>[a-z]+)\s+' +
            'consume:\s*(?P<consume>[a-z]+)'), raw[2])
        status.update(result.groupdict())
        return status

    def apply_mpd_status(self, key, status):
        """Tries to set mpd to the same status as saved in the statusmap.

        Positional arguments:
        key -- the key aka playlist / folder name
        status -- the status dict with at least key and type
        """
        if not set(['key', 'type']).issubset(status):
            raise ValueError('more status information needed')

        # clear playlist
        self.mpc('clear')

        # load files
        if status['type'] == 'playlist':
            self.mpc('load', key)
        else:
            self.mpc('add', key)

        # set some finer details of playback
        for key, state in status.items:
            if key in ['key', 'type', 'position', 'time', 'status']:
                # those are used to load a queue or play which needs to be done
                # beforehand and afterwards respectively
                continue
            self.mpc(key, state)

        # jump to position playing
        if 'position' in status:
            self.mpc('play', status['position'])
            self.mpc('toggle')

        if 'time' in status:
            self.mpc('seek', status['time'])

    def check_mpd_queue_is_current_list(self):
        """Check if mpd's queue is the list we expect to be looking at."""

        if self.get_type() == 'playlist':
            # get the queue
            queue = self.mpc('playlist').stdout.strip()
            # get the contents of the playlist
            assumed_list = self.mpc('playlist', self.get_key()).stdout.strip()
        else:
            # get the queue but show filenames
            queue = self.mpc('playlist', '-f', '%file%').stdout.strip()
            # find files in the specified folder
            assumed_list = self.mpc(
                    'search', 'filename', self.get_key()).stdout.strip()

        # considered comparing hashes but comparing the strings might be just as
        # fast
        #queue_hasher = hashlib.md5()
        #queue_hasher.update(queue)
        #queue_hash = queue_hasher.hexdigest()

        #list_hasher = hashlib.md5()
        #list_hasher.update(assumed_list)
        #list_hash = list_hasher.hexdigest()

        return queue == assumed_list

    # TODO: move status to statusmap

    def check_status(self):
        if self.get_key() is None:
            # no key known - so nothing can be stored
            self.communicate('Don\'t know what to do. Please, load a playlist.',
                    'error')
            return

        if not self.check_mpd_queue_is_current_list():
            # the current playlist differs from what we would expect by looking
            # at the statusmap
            # maybe someone has changed it from the outside (e.g., another mpd
            # client) in the meantime
            self.communicate('Don\'t know what to do. Please, load a playlist.',
                    'error')
            return

    def update_status(self):
        status = self.query_status()

        if status['status'] == 'stopped':
            # cannot store something meaningful
            return

        # persist the status
        self.set_status(status)

    def play(self, *args, **kwargs):
        result = self.mpc('play')

    def simple_command(self, do):
        """Wrapper around the more simple functions (toggle, stop, etc.)."""
        self.check_status()
        self.mpc(do)
        self.update_status()

    def volume(self, direction=None, step=None):
        self.check_status()
        if not direction in ['+', '-']:
            logger.error('no such action "{}"'.format(action))
            return
        if step is None:
            step = self.get_config().get('MPC', 'volume_step', default="5",
                    variable_type="str")
        result = self.mpc('volume', direction+step)
