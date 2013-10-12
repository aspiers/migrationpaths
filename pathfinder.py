#!/usr/bin/python

import sys

from vmpoolstateerrors import VMPoolStateSanityError
from vmpoolpath import VMPoolPath

class VMPoolPathFinder:
    """This abstract class enables storage of the state data used
    during the discovery of the path inside an instance.  This makes
    the code thread-safe, allowing discovery of multiple paths in
    parallel (one instance of this class for each).  It also makes the
    code a bit cleaner (albeit slightly more complex) through not
    having to pass several state variables around.

    N.B. Instances should not be reused for multiple runs.
    """

    def __init__(self, initial_state, final_state, debug_level=2):
        self.initial_state = initial_state
        self.final_state = final_state

        self._debug = ''
        self._debug_level = debug_level

        self._state_cache = { }
        self.cache_state(initial_state)
        self.cache_state(final_state)

        # Did we find a path yet?
        self.found = False

        self.init()

    def init(self):
        pass # override this if required

    def check_endpoints_sane(self):
        try:
            self.initial_state.check_sane()
        except VMPoolStateSanityError, e:
            sys.stderr.write("start state not sane: %s\n" % e)
            sys.exit(1)

        try:
            self.final_state.check_sane()
        except VMPoolStateSanityError, e:
            sys.stderr.write("end state not sane: %s\n" % e)
            sys.exit(1)

    def find_path(self):
        self.check_endpoints_sane()

        if hasattr(self, 'path'):
            raise RuntimeError, \
                  "cannot reuse %s instance" % self.__class__.__name__

        self.path = VMPoolPath(self.initial_state, self.final_state)
        self.path.compare_endpoints()

        migrations = self.run()
        if migrations is None:
            return None

        self.path.set_migration_sequence(migrations)
        cost = reduce(lambda acc, mig: acc + mig.cost(), migrations, 0)
        self.path.set_cost(cost)

        return self.path

    # Cache objects by unique string.  This allows us to key
    # todo/done/distances/previous by unique string but still be able
    # to retrieve the corresponding object.  This is necessary because
    # multiple pool state objects can potentially represent the same
    # state.
    #
    # Note that this relies on the VMPoolState instances remaining
    # unchanged after caching.  This should be thread-safe since the
    # cache is per path finder run (per instance), within which state
    # instances are constructed during neighbour exploration and not
    # subsequently altered.

    def cache_state(self, state):
        if state.unique() not in self._state_cache:
            self._state_cache[state.unique()] = state

    def cache_lookup(self, state_string):
        return self._state_cache[state_string]
        #return self._state_cache.get(state_string, None)

    def debug(self, level, message):
        if level >= self._debug_level:
            self._debug += message + "\n"

    def get_debug(self):
        return self._debug
