#!/usr/bin/env python3

import subprocess
import threading
import time
import logging
import sys
import re
#import hashlib

from boxcontroller.listenerplugin import ListenerPlugin
from . import statusmap

logger = logging.getLogger('boxcontroller.plugin.' + __name__)

class Mpc(ListenerPlugin):

    def on_init(self):
        self.__statusmap = statusmap.StatusMap(self.get_config())
        # register only mpd_play initially so we do not block the other commands
        # the other listeners (toggle, next, ...) will be registered by
        # Mpc.play().
        # If another plugin will be started that plays back media and needs
        # exclusive input from these signals it will register with its
        # play-function and unregister our other listeners (toggle, next, ...)
        self.register('mpd_play', self.play, True)
        self.register('terminate', self.on_terminate)

        # this plugin may inhibit shutdown etc. if it marks itself as busy
        self.register_as_busy_bee()

        # a lock to prevent the main thread and the watching thread to update
        # the status simultaneously
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        # a chronicler to watch and record MPD's status
        interval = self.get_config().get('MPC', 'polling_interval', default=5,
                variable_type='int')
        self.chronicler = threading.Thread(target=self.watch_status,
                args=(self.stop_event,interval,))
        self.chronicler.start()

        logger.debug('checking if mpd is already playing')
        self.__last_status_update = 0
        if not self.check_status():
            return
        # we know what's on the list
        status = self.query_mpd_status()
        if status['status'] == 'playing':
            # and it's playing
            logger.debug('MPD\'s already a\'playing')
            # so seize control over the buttons
            self.seize_control()
            # and store the status
            self.update_status()
            # be busy
            self.mark_as_busy(True)

    def on_terminate(self):
        """Send stop signal to thread watching MPD and wait for it to finish."""
        self.stop_event.set()
        self.chronicler.join()

    def get_statusmap(self):
        return self.__statusmap

    def get_status(self, key, parameter = None):
        """Return the status for key.

        Positional arguments:
        key -- the key [string]
        parameter -- what to return, returns all if parameter == None [string]
        """
        return self.get_statusmap().get(key, parameter)

    def set_status(self, key, soft=True, **status):
        """Update the status for the given key.

        Positional arguments:
        key -- the key [string]

        Keyword arguments:
        soft -- do not yet write to disc
        **status -- keywords
        """
        logger.debug('updating status for key: "{}" ({})'.format(key, ','.join(
            ['"{}": "{}"'.format(kw,v) for kw, v in status.items()])))
        self.get_statusmap().update(key, soft=soft, **status)

    def get_current_key(self):
        """Get the key of the current / last played playlist or folder."""
        logger.debug('returning current key ({})'.format(
            self.get_statusmap().get_current_key()))
        return self.get_statusmap().get_current_key()

    def set_current_key(self, key):
        """Set the key of the current / last played playlist or folder."""
        logger.debug('setting current key to {}'.format(key))
        self.get_statusmap().set_current_key(key)

    def key_marks_playlist(self, key):
        """Return if the key marks a playlist (ends wit .m3u) or a folder.

        Positional arguments:
        key -- the key
        """
        playlist = key[-3:] == 'm3u'
        logger.debug('key "{}" is {}a playlist'.format(key,
            ('' if playlist else 'not ')))
        return playlist

    def mpc(self, *args, **kwargs):
        """Call mpc as a subprocess and return its output.

        Positional arguments:
        *args -- one string for each parameter part passed to mpc [string]
        **kwargs -- passed as arguments to subprocess.run()
        """
        call = ['mpc']

        if len(args) > 0:
            call += args

        logger.debug('calling mpc with: {}'.format(','.join(
            [item for item in call])))

        if sys.version_info[1] >= 7:
            # capture output is new and in this case required with python >= 3.7
            result = subprocess.run(call, capture_output=True,
                    encoding="utf-8", **kwargs)
        else:
            result = subprocess.run(call, encoding="utf-8", **kwargs,
                    stdout=subprocess.PIPE)

        raw = result.stdout
        if result.returncode != 0 or raw[:9] == 'mpd error':
            # error
            logger.error('error calling mpc: "{}"'.format(raw.strip()))
            return None
        return raw

    def query_mpd_status(self):
        """Query the status (filename, position, name, volume, status)."""
        logger.debug('querying mpd status')
        # get the status
        raw = self.mpc('status', '-f', '%file%@@%position%@@%name%')[:-1]

        status = {}

        if raw is None:
            # error
            logger.debug('mpd error')
            return status

        # remove the last character as it is a "\n" and split the lines
        raw = raw.split('\n')

        if len(raw) == 1:
            # not playing
            # that's the only information we can get
            logger.debug('mpd stopped')
            status.update({'status': 'stopped'})
            return status

        # line 1 looks like
        # FILENAME@@POSITION@@NAME
        status['file'], status['position'], status['name'] = raw[0].split('@@')
        # line 2 looks like
        # [STATUS] #POSITION/MAX_POSITION TIME/MAX_TIME (PERCENT%)
        result = re.match(re.compile(
            '\[(?P<status>\w+)\]\s+#(?P<position>[0-9]+)/[0-9]+\s+' +
            '(?P<time>[0-9:]+)/[0-9:]+\s+\([0-9]+%\)'), raw[1])
        if not result is None:
            status.update(result.groupdict())
        else:
            logger.debug('did not recognize line: "{}"'.format(raw[1]))
        # line 3 looks like
        # volume:VOLUME%   repeat: off random: off single: off consume: off
        result = re.match(re.compile(
            'volume:\s*(?P<volume>[na/0-9]+)%\s+repeat:\s*(?P<repeat>[a-z]+)\s+' +
            'random:\s*(?P<random>[a-z]+)\s+single:\s*(?P<single>[a-z]+)\s+' +
            'consume:\s*(?P<consume>[a-z]+)'), raw[2])
        if not result is None:
            status.update(result.groupdict())
        else:
            logger.debug('did not recognize line: "{}"'.format(raw[2]))
        logger.debug('mpd status: {}'.format(','.join(
            ['"{}": "{}"'.format(kw,v) for kw, v in status.items()])))
        return status

    def apply_mpd_status(self, key, status):
        """Tries to set mpd to the same status as saved in the statusmap.

        Positional arguments:
        key -- the key aka playlist / folder name
        status -- the status dict with at least key and type

        Returns True / False on success / failure
        """
        if status is None:
            logger.info('no status given')
            status = {}
            #return False

        logger.debug('applying key "{}" with status: {}'.format(key, ','.join(
            ['"{}": "{}"'.format(kw,v) for kw, v in status.items()])))

        # clear playlist
        self.mpc('clear')

        # load files
        if self.key_marks_playlist(key):
            logger.debug('loading playlist')
            result = self.mpc('load', key[:-4])
        else:
            logger.debug('loading folder')
            result = self.mpc('add', key)

        if result is None:
            # some error occured during loading
            logger.error('some error occured while loading the playlist.')
            return False

        # set some finer details of playback
        for keyword, state in status.items():
            if keyword in ['file', 'name', 'position', 'time', 'status']:
                # those are used to load a queue or play which needs to be done
                # beforehand and afterwards respectively
                continue
            result = self.mpc(keyword, state)
            if result is None:
                logger.error('error setting "{}" to "{}"'.format(keyword, state))

        # jump to position playing
        if 'position' in status:
            logger.debug('jumping to position in playlist')
            result = self.mpc('play', status['position'])
            if result is None:
                logger.debug('could not jump to position playlist')
            self.mpc('toggle')

        if 'time' in status:
            logger.debug('seeking position in track')
            result = self.mpc('seek', status['time'])
            if result is None:
                logger.debug('could not jump to position in track')
        return True

    def check_mpd_queue_is_current_list(self):
        """Check if mpd's queue is the list we expect to be looking at."""
        logger.debug('comparing playlists')

        current_key = self.get_current_key()
        if current_key is None:
            logger.debug('No current key set')
            return False

        if self.key_marks_playlist(current_key):
            # get the queue
            queue = self.mpc('playlist').strip()
            # get the contents of the playlist
            assumed_list = self.mpc('playlist',
                    current_key[:-4]).strip()
        else:
            # get the queue but show filenames
            queue = self.mpc('playlist', '-f', '%file%').strip()
            # find files in the specified folder
            assumed_list = self.mpc(
                    'search', 'filename', current_key).strip()

        #print('Queue:')
        #print(queue)
        #print('\nList')
        #print(assumed_list)

        # considered comparing hashes but comparing the strings might be just as
        # fast
        #queue_hasher = hashlib.md5()
        #queue_hasher.update(queue)
        #queue_hash = queue_hasher.hexdigest()

        #list_hasher = hashlib.md5()
        #list_hasher.update(assumed_list)
        #list_hash = list_hasher.hexdigest()

        return queue == assumed_list

    def check_status(self):
        logger.debug('checking status')
        key = self.get_current_key()
        if key is None:
            # no key known - so nothing can be stored
            # we don't know what's currently playing and do not have the means
            # to figure it out because MPD does not store if it's playing a
            # a playlist or the contents of one or multiple folders
            logger.debug('no current key')
            #self.communicate('Don\'t know what to do. Please, load a playlist.',
            #        'error')
            return False
        logger.debug('current key: "{}"'.format(key))

        if not self.check_mpd_queue_is_current_list():
            # the current playlist differs from what we would expect by looking
            # at the statusmap
            # maybe someone has changed it from the outside (e.g., another mpd
            # client) in the meantime
            #self.communicate('Don\'t know what to do. Please, load a playlist.',
            #        'error')
            logger.debug('not in expected playlist')
            return False
        logger.debug('loaded playlist is expected playlist')
        return True

    def update_status(self):
        """Update status in statusmap."""
        self.lock.acquire()
        logger.debug('updating status')

        if time.time() - self.__last_status_update <= 5:
            logger.debug('too early')
            return

        if not self.check_status():
            self.__last_status_update = time.time()
            self.lock.release()
            return
        status = self.query_mpd_status()

        #if status['status'] == 'stopped':
        #    # cannot store anything meaningful
        #    logger.debug('cancel status update, not playing')
        #    return
        if status['status'] == 'playing':
            self.mark_as_busy(True)
        else:
            self.mark_as_busy(False)

        # persist the status
        key = self.get_current_key()
        if key is None:
            logger.debug('cancel status update, no current key')
            self.lock.release()
            self.__last_status_update = time.time()
            return
        self.set_status(key, soft=False, **status)
        self.__last_status_update = time.time()
        self.lock.release()

    def watch_status(self, stop_event, interval):
        """Poll MPD's status every INTERVAL seconds.

        Positional arguments:
        stop_event -- stops the thread if set [threading.Event]
        interval -- interval between polls in seconds [int]
        """
        while not stop_event.wait(interval):
            self.update_status()

    def seize_control(self):
        """Seize control of control buttons' events."""
        logger.debug('seizing control over the buttons')
        self.register('toggle', lambda: self.simple_command('toggle'), True)
        self.register('stop', lambda: self.simple_command('stop'), True)
        self.register('next', lambda: self.simple_command('next'), True)
        self.register('previous', lambda: self.simple_command('prev'), True)
        #self.register('volume', self.volume)

    def play(self, *args, **kwargs):
        """Play the contents of the playlist / folder defined by KEY.

        Keyword arguments:
        key -- the key as used in EventMap and StatusMap [string]
        """
        logger.debug('play: {}'.format(kwargs['key']))

        # seize control!
        self.seize_control()

        status = self.query_mpd_status()

        if not status['status'] == 'stopped':
            # something is playing / paused
            if self.check_status():
                # we know what's playing
                if self.get_current_key == kwargs['key']:
                    # and it's the same as requested
                    # so we need not do anything
                    logger.debug('already playing')
                    return

        try:
            if not self.apply_mpd_status(kwargs['key'],
                    self.get_status(kwargs['key'])):
                return
            result = self.mpc('play')
            if result is None:
                raise ChildProcessError
            self.mark_as_busy(True)
        except (KeyError, ChildProcessError) as e:
            self.debug('error loading status: {}'.format(','.join(
                ['{},{}'.format(kw,v) for kw,v in kwargs.items()])))
            self.communicate('Could not load playlist.')
            return
        self.set_current_key(kwargs['key'])
        self.update_status()

        # mpd is now playing the desired list
        # watch it and store it's progresse every X seconds
        #self.chronicler.start()

    def simple_command(self, do):
        """Wrapper around the more simple functions (toggle, stop, etc.)."""
        logger.debug('simple command: {}'.format(do))
        self.mpc(do)
        self.update_status()

    def volume(self, direction=None, step=None):
        if not direction in ['+', '-']:
            logger.error('no such direction "{}"'.format(direction))
            return
        if step is None:
            step = self.get_config().get('MPC', 'volume_step', default="5",
                    variable_type="str")

        logger.debug('changing volume: {}{}'.format(direction, step))
        result = self.mpc('volume', '{}{}'.format(direction, step))
        if result is None:
            logger.error('could not change volume')
        if not self.check_status():
            return
