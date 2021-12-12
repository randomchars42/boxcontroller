#!/usr/bin/env bash

import logging

logger = logging.getLogger(__name__)

class Publisher:
    """Simple publisher base class."""

    def get_subscribers(self, event):
        try:
            return self._events[event]
        except KeyError:
            # event has not yet been added
            self._events[event] = {}
        except NameError:
            # dict has not yet been defined
            self._events = {event: {}}
        return self.get_subscribers(event)

    def register(self, event, who, callback=None):
        if callback == None:
            try:
                callback = getattr(who, 'update')
            except AttributeError:
                logger.error('could not get default callback on {}'.format(who))
                return
        self.get_subscribers(event)[who] = callback
        logger.debug('"{}" registered for event "{}"'.format(who, event))

    def unregister(self, event, who):
        del self.get_subscribers(event)[who]
        logger.debug('"{}" unregistered for event "{}"'.format(who, event))

    def dispatch(self, event, *args, **kwargs):
        for subscriber, callback in self.get_subscribers(event).items():
            logger.debug('dispatched "{}" for "{}"'.format(event, subscriber))
            callback(*args, **kwargs)

    def _reset(self):
        self._events = {}
