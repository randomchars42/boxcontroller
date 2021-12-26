#!/usr/bin/env bash

import logging

logger = logging.getLogger(__name__)

class EventAPI:
    """Interface for plugins communication synchronously."""

    def get_subscribers(self, event):
        try:
            return self.get_events()[event]
        except KeyError:
            # event has not yet been added
            self.get_events()[event] = {}
        return self.get_subscribers(event)

    def get_events(self):
        try:
            return self._events
        except NameError:
            # dict has not yet been defined
            self._events = {}

    def register_listener(self, event, who, callback=None, exclusive=False):
        """Register listeners, one per name, might register as exclusive.

        Positional arguments:
        event -- the event to register to [string]
        who -- name of the module registering [string]

        Keyword arguments:
        callback -- the function / lambda to call [function]
        exclusive -- unregister other listeners to this event [boolean]
        """
        if callback == None:
            try:
                callback = getattr(who, 'update')
            except AttributeError:
                logger.error('could not get default callback on {}'.format(who))
                return
        if exclusive:
            self.get_events()[event] = {who: callback}
            logger.debug('"{}" registered for event "{}" (exclusive)'.format(
                who, event))
        else:
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
