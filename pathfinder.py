#!/usr/bin/python

import re
import sys
import time
import traceback

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
        self._stack_depth_at_run = len(traceback.extract_stack()) + 1
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

    def debug(self, level, message, indent=None):
        if level <= self._debug_level:
            if indent is None:
                indent = self._indent()
            #print "indent[%s]" % indent
            if indent != "":
                message = re.subn('^', indent, message, 0, re.MULTILINE)[0]
            #message = "[%s]" % message
            if self.immediate_debugging:
                print message
            self._debug += message + "\n"
        # if time.time() - self._start_time > 1.0:
        #     print self._debug,
        #     self._debug = ''

    def _indent(self):
        # Determine stack depth from run() method
        stack = traceback.extract_stack()
        stack = stack[self._stack_depth_at_run:]

        # Pop debug routines off traceback
        while stack and __file__.startswith(stack[-1][0]):
            stack.pop()

        # print("".join(traceback.format_list(stack)))
        # print len(stack)

        # Indent by stack depth, excluding this method's caller so
        # that we start with no indentation.
        return "  " * (len(stack) - 1)

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
        meters = current_state.ascii_meters(
            10, 80, indent='',
            highlight_vms=vm_highlights,
            highlight_vmhosts=vmhost_highlights
            ).rstrip()
        self.debug(2, meters, indent='')
