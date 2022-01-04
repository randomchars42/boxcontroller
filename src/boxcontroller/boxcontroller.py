#!/usr/bin/env python3

import signal
import sys
import os
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
from .eventapi import EventAPI

logger = logging.getLogger(__name__)

class BoxController(EventAPI):
    def __init__(self, config):
        self._plugins = {}
        self._config = config
        self.__processes = {}
        self.__to_plugins = multiprocessing.JoinableQueue()
        self.__from_plugins = multiprocessing.Queue()
        self.__stop_signal = False
        self.__shutdown_flag = False

        self._path_plugins = Path(pkg_resources.resource_filename(__name__,
                'plugins'))
        self._path_plugins_user = Path(
                config.get('Paths', 'user_config'),
                config.get('Paths', 'plugins'))
        path_eventmap = Path(
                config.get('Paths', 'user_config'),
                config.get('Paths', 'eventmap'))

        self.setup(Path(config.get('Paths', 'user_config')))

        self._event_map = evt.EventMap(config)
        self.load_plugins()
        self.register_listener('shutdown', 'main', callback=self.on_shutdown)
        self.load_event_map()

    def get_stop_signal(self):
        return self.__stop_signal

    def get_shutdown_flag(self):
        return self.__shutdown_flag

    def set_shutdown_flag(self, set_to=True):
        self.__shutdown_flag = set_to

    def setup(self, *args):
        """Make sure paths to config, plugins etc. are accessible."""
        logger.debug('checking paths')
        for path in args:
            target = path.expanduser().resolve()

            if not target.is_dir():
                target = target.parent

            if target.exists():
                logger.debug('path "{}" exists'.format(str(target)))
            else:
                logger.debug('path "{}" does not exist'.format(str(target)))
                try:
                    target.mkdir(parents=True, exist_ok=True)
                except OSError:
                    logger.error('could not create path "{}"'.format(str(target)))

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
        self._dispatch('init')

    def _load_plugins(self, path):
        """Gather all packages under path as plugins.

        Positional arguments:
        path -- the path to scan for modules [string|Path]
        """
        logger.info('loading plugins from {}'.format(path))

        blacklist = self.get_config().get('Plugins', 'blacklist', default='')
        blacklist = [item.lower() for item in blacklist.split(',')]

        sys.path.append(str(path))
        for file in path.glob('*'):
            if file.name == '__pycache__' or not file.is_dir():
                continue

            name = file.name

            if name.lower() in blacklist:
                logger.debug('blacklisted plugin: {}'.format(name))
                continue

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
        self._dispatch('finished_loading')
        logger.debug('waiting for signals')

        self.am_i_idle()

        while not self.get_stop_signal():
            try:
                input_string = self.__from_plugins.get(False)
                self.process_input(input_string)
            except Empty:
                pass

        # stop all process plugins
        for name, process in self.get_processes().items():
            logger.debug('terminating process "{}"'.format(name))
            process.terminate()
            process.join()

        self.shutdown()


    def terminate(self):
        """Stop all ProcessPlugins and ListenerPlugins."""
        # signal to all Plugins running in the main thread
        self._dispatch('terminate')
        # stop all ProcessPlugins with their processes
        self.__stop_signal = True

    def on_shutdown(self):
        """Prepare for shutdown."""
        logger.debug('beginning shutdown routine')
        # wait for all processes to stop
        self.terminate()

        self._dispatch('before_shutdown')
        self.set_shutdown_flag(True)

    def shutdown(self):
        """Actual shutdown procedure called after all processes have stopped."""

        if not self.get_shutdown_flag():
            logger.debug('Shutdown flag not set.')
            return

        if not self.get_stop_signal():
            logger.error('Processes have not been told to stop yet.')
            return

        time = self.get_config().get('System', 'shutdown_time',
                default=1, variable_type='int')
        os.system('shutdown -P {}'.format(str(time)))


def main():
    """Run the application.

    Configure logging and read parameters.
    """
    config = cfg.Config()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--options',
        help='arbitrary configuration(s) as could be found in the ini-file \n' +
            'formatted like SECTION1.option1=val1@@' +
            'SECTION2.option4=val2@@... \n' +
            'e.g., Soundcontrol.max_volume=60@@' +
            'InputUSBRFID.device=/dev/event0 \n' +
            '"@@" serves as a separator',
        action='store',
        default='',
        type=str)
    parser.add_argument(
        '-d', '--user_config',
        help='the directory where your config.ini, eventmap, etc. is stored',
        action='store',
        type=str,
        default="")
    parser.add_argument(
        '-v', '--verbosity',
        help='increase verbosity',
        action='count',
        default=0)

    args = parser.parse_args()

    if not args.options == '':
        for option in args.options.split('@@'):
            try:
                section, rest = option.split('.', 1)
                option, value = rest.split('=', 1)
                cfg.set(section, option, value)
            except:
                logger.error('did not understand option "{}"'.format(option))

    if not args.user_config == '':
        cfg.set('Paths', 'user_config', args.user_config)

    verbosity = ['ERROR', 'WARNING', 'INFO', 'DEBUG']
    log.config['handlers']['console']['level'] = verbosity[args.verbosity]
    log.config['loggers']['__main__']['level'] = verbosity[args.verbosity]
    log.config['loggers']['boxcontroller']['level'] = verbosity[args.verbosity]

    logging.config.dictConfig(log.config)

    boxcontroller = BoxController(config)

    signal.signal(signal.SIGINT, lambda signal_num, frame: signal_handler(
        signal_num, frame, boxcontroller))
    boxcontroller.run()

def signal_handler(signal_num, frame, boxcontroller):
    """Log signal and call sys.exit(0).

    Positional arguments:
    signal_num -- unused
    frame -- unused
    boxcontroller -- BoxController object to stop
    """
    logger.info('recieved signal ' + str(signal_num))
    boxcontroller.terminate()
    #sys.exit(0)

if __name__ == '__main__':

    try:
        main()
    except Exception as error:
        logger.error(error, exc_info=True)
