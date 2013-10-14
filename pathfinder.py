#!/usr/bin/python

import sys
import time

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
        self.immediate_debugging = False

        self._start_time = time.time()

        # Did we find a path yet?
        self.found = False

        self.check_endpoints_sane()

        if hasattr(self, 'path'):
            raise RuntimeError, \
                  "cannot reuse %s instance" % self.__class__.__name__

        self.path = VMPoolPath(self.initial_state, self.final_state)
        self.path.compare_endpoints()

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
        migrations = self.run()
        self._end_time = time.time()

        if migrations is None:
            return None

        self.path.set_migration_sequence(migrations)
        cost = reduce(lambda acc, mig: acc + mig.cost(), migrations, 0)
        self.path.set_cost(cost)

        return self.path

    def time_elapsed(self):
        return self._end_time - self._start_time

    def debug(self, level, message):
        if level >= self._debug_level:
            if self.immediate_debugging:
                print message
            self._debug += message + "\n"

    def _get_vm_highlights(self, vms_to_migrate, locked_vms):
        vm_highlights = { }
        for vm_name in vms_to_migrate:
            vm_highlights[vm_name] = ['yellow']
        for vm_name in locked_vms:
            color = 'red' if vm_name in vms_to_migrate else 'magenta'
            vm_highlights[vm_name] = [color]
        return vm_highlights

    def get_debug(self):
        return self._debug

    def debug_state(self, current_state, vms_to_migrate, locked_vms,
                    extra_vm_highlights={}, vmhost_highlights={}):
        vm_highlights = self._get_vm_highlights(vms_to_migrate, locked_vms)
        vm_highlights.update(extra_vm_highlights)
        self.debug(2, current_state.ascii_meters(
                10, 80, indent='  ',
                highlight_vms=vm_highlights,
                highlight_vmhosts=vmhost_highlights))

        self.debug(2, "  vms_to_migrate: %s" % ", ".join(vms_to_migrate.keys()))
        self.debug(2, "  locked_vms: %s" % ", ".join(locked_vms.keys()))
