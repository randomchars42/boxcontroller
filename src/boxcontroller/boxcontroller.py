#!/usr/bin/env python3

import signal
import sys
import logging
import logging.config
import pkgutil
from importlib import import_module
import pkg_resources
import argparse
import multiprocessing

from pathlib import Path

from .log import log
from . import config as cfg
from . import eventmap as evt
from . import publisher

logger = logging.getLogger(__name__)

class BoxController(publisher.Publisher):
    def __init__(self, config):
        self._plugins = {}
        self._config = config
        self._event_map = evt.EventMap(config)
        self.__processes = {}
        self.__to_plugins = multiprocessing.JoinableQueue()
        self.__from_plugins = multiprocessing.Queue()

        self._path_plugins = Path(pkg_resources.resource_filename(__name__,
            'plugins'))
        self._path_plugins_user = Path(config.get('Paths', 'plugins'))

        self.load_plugins()
        self.load_event_map()

    def load_event_map(self):
        """Trigger a (re-)load of the event mappings."""
        logger.info('loading events')
        self._event_map.load()
        logger.info('events loaded')

    def load_plugins(self):
        """Triggers a (re-)scan of the plugin diretories.

        Will load all plugins into BoxController._plugins.

        May be used to "hotplug" new plugins.
        """
        # unregister all listeners or else each will reciever the event
        # multiple times in case of one or more reloads
        #super(publisher.Publisher, self)._reset()
        super()._reset()
        self._plugins['main'] = self
        self._load_plugins(self._path_plugins)
        self._load_plugins(self._path_plugins_user.expanduser().resolve())
        self.dispatch('init')

    def _load_plugins(self, path):
        """Gather all packages under path as plugins.

        Positional arguments:
        path -- the path to scan for modules [string|Path]
        """
        logger.info('loading plugins from {}'.format(path))

        sys.path.append(str(path))
        for file in path.glob('*'):
            if file.name == '__pycache__' or not file.is_dir():
                continue
            name = file.name
            package = import_module('{}.{}'.format(name, name))
            classname = name[0].upper() + name[1:]
            self._plugins[classname] = getattr(package, classname)(
                    name=classname, main=self, to_plugins=self.__to_plugins,
                    from_plugins=self.__from_plugins)

        logger.info('plugins loaded from {}'.format(path))

    def get_plugins(self):
        """Return a dict of references to all plugins."""
        return self._plugins

    def get_plugin(self, name):
        """Return a reference to the requested plugin.

        Positional arguments:
        name -- the plugin name [string]
        """
        if not name in self._plugins:
            raise KeyError('No such plugin.')
        return self.get_plugins()[name]

    def get_config(self):
        """Return a reference to the config."""
        return self._config

    def process_input(self, string):
        """The main way to process input from peripherals.

        The input is used as a key to look up which event to trigger.

        Positional arguments:
        string - the input to map to an event [string]
        """
        logger.debug('recieved input: "{}"'.format(string))
        try:
            event, data = self._event_map.get(string)
        except KeyError:
            return

        self.dispatch(event, *data['positional'], **data['keyword'])

    def define_event(self, key, event, *args, **kwargs):
        """Update, add or delete the mapping of an event.

        Positional arguments:
        key -- the key [string]
        event -- name of the event [string], pass [None] to remove entry
        *args -- positional data [string], leave empty to remove entry
        **params -- keyworded data [string: string], leave empty to remove entry
        """
        self._event_map.update(key, event, *args, **kwargs)

    def get_processes(self):
        """Return the dict of ProcessPlugin processes that have registered."""
        return self.__processes

    def register_process(self, name, reference):
        """Interface for ProcessPlugins to register themselves.

        Positional arguments:
        name -- the name of the process [string]
        reference -- reference to the process object [multiprocess.Process]
        """
        self.get_processes()[name] = reference

    def run(self):
        """Start a process for each ProcessPlugin and listen to their input.

        Modified after: https://pymotw.com/3/multiprocessing/communication.html
        """
        logger.debug('running process plugins')
        for name, process in self.get_processes().items():
            logger.debug('starting process "{}"'.format(name))
            process.start()
        logger.debug('started all process plugins')
        i = 0
        while i < 3:
            logger.debug('awaiting signals')
            input_string = self.__from_plugins.get()
            print(input_string)
            i += 1
        self.stop()

    def stop(self):
        """Stop all ProcessPlugins."""
        for name, process in self.get_processes().items():
            logger.debug('terminating process "{}"'.format(name))
            process.terminate()
            process.join()


def main():
    """Run the application.

    Configure logging and read parameters.
    """
    config = cfg.Config()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--verbosity',
        help='increase verbosity',
        action='count',
        default=0)

    args = parser.parse_args()

    verbosity = ['ERROR', 'WARNING', 'INFO', 'DEBUG']
    log.config['handlers']['console']['level'] = verbosity[args.verbosity]
    log.config['loggers']['__main__']['level'] = verbosity[args.verbosity]
    log.config['loggers']['boxcontroller']['level'] = verbosity[args.verbosity]

    logging.config.dictConfig(log.config)

    boxcontroller = BoxController(config)
    #boxcontroller.process_input('yourself')
    #boxcontroller.process_input('joke')
    #boxcontroller.define_event('3213', 'play', file='v.mp3', param='value')
    #boxcontroller.process_input('toggle')
    #boxcontroller.process_input('volume_inc')
    #boxcontroller.process_input('volume_inc')
    #boxcontroller.process_input('volume_inc')
    #import time
    #time.sleep(3)
    #boxcontroller.process_input('volume_dec')
    #boxcontroller.process_input('volume_dec')
    #boxcontroller.process_input('volume_dec')
    boxcontroller.run()

def signal_handler(signal_num, frame):
    """Log signal and call sys.exit(0).

    Positional arguments:
    signal_num -- unused
    frame -- unused
    """
    logger.error('recieved signal ' + str(signal_num))
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except Exception as error:
        logger.error(error, exc_info=True)
