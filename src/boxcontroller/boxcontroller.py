#!/usr/bin/env python3
import logging
import logging.config

from log import log

logger = logging.getLogger(__name__)

def main():
    logging.config.dictConfig(log.config)

if __name__ == '__main__':
    main()
