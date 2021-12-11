#!/usr/bin/env python3

import signal
import sys
import logging
import logging.config
import pkgutil
import pkg_resources
import argparse

from pathlib import Path

from .log import log
from . import config as cfg
from . import commands as cmd

logger = logging.getLogger(__name__)

class BoxController:
    def __init__(self, config):
        self._plugins = {}
        self._config = config
        self._commands = cmd.Commands()

        self._path_plugins = Path(pkg_resources.resource_filename(__name__,
            'plugins'))
        self._path_plugins_user = Path(config.get('Paths', 'plugins'))

        self.load_plugins()

    def load_commands(self):
        """Trigger a (re-)load of the commands."""
        logger.info('loading commands')
        self._commands.load()
        logger.info('commands loadded')

    def load_plugins(self):
        """Triggers a (re-)scan of the plugin diretories.

        Will load all plugins into BoxController._plugins.

        May be used to "hotplug" new plugins.
        """
        self._plugins['main'] = self
        self._load_plugins(self._path_plugins)
        self._load_plugins(self._path_plugins_user.expanduser().resolve())

    def _load_plugins(self, path):
        logger.info('loading plugins from {}'.format(path))

        for loader, name, pkg in pkgutil.iter_modules([str(path)]):
            logger.debug(name)
            package = loader.find_module(name).load_module(name)
            loader.find_module(name).exec_module(package)
            class_name = name[0].upper() + name[1:]
            if class_name in self._plugins:
                logger.warning('overwriting plugin {}'.format(class_name))
            self._plugins[class_name] = getattr(package, class_name)()

        logger.info('plugins loaded from {}'.format(path))

    def get_plugins(self):
        return self._plugins

    def get_plugin(self, name):
        if not name in self._plugins:
            raise KeyError('No such plugin.')
        return self._plugins[name]

    def call_command(self, raw_command):
        try:
            (plugin, rest) = raw_command.split('.', 1)
        except ValueError:
            logger.error('Malformed command: "{}"'.format(raw_command))
            return
        command, *params = [item for item in rest.split(' ') if item != '']
        self.__plugins[plugin].call(command, *params)

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
