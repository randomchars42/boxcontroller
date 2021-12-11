#!/usr/bin/env python3

import logging

from boxcontroller.plugin import Plugin

logger = logging.getLogger(__name__)

class Hello(Plugin):
    def __init__(self):
        logger.info('loaded Hello')
        print("Hello! :)")
