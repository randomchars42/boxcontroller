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
        except NameError, AttributeError as e:
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
        if len(self.get_subscribers(event)) == 0:
            logger.debug('trying to dispatch "{}", no one\'s listening'.format(
                event))
        for subscriber, callback in self.get_subscribers(event).items():
            logger.debug('dispatching "{}" for "{}"'.format(event, subscriber))
            callback(*args, **kwargs)

    def _reset(self):
        self._events = {}

    def register_busy_bee(self, name):
        """Some plugins may declare the box's state as not idle.

        Actions such as shutdown after X minutes of idle time will be inhibited.

        Positional arguments:
        name -- name of the plugin [string]
        """
        # register busy bee but mark as not busy at the moment
        self.get_busy_bees()[name] = False

    def get_busy_bees(self):
        """Return a dict holding busy bees which may inhibit idle time."""
        try:
            return self.__busy_bees
        except AttributeError:
            self.__busy_bees = {}
            return self.__busy_bees

    def am_i_idle(self):
        """Am I idle (True) or are there any busy bees inhibitting idle time?"""
        logger.debug('am I idle?')
        if not True in self.get_busy_bees().values():
            logger.debug('I am idle.')
            self.dispatch('idle')
        else:
            logger.debug('someone\'s busy.')
            self.dispatch('busy')

    def mark_busy_bee_as_busy(self, name, busy):
        """Mark a plugin as busy or idle.

        Positional arguments:
        name -- name of the plugin [string]

        Keyword arguments:
        busy -- busy (True) or not (False) [boolean]
        """
        self.get_busy_bees()[name] = busy
        self.am_i_idle()
