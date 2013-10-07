#!/usr/bin/python

from vmpoolpath import VMPoolPath

class VMPoolPathFinder:
    """This abstract class enables storage of the state data used
    during the discovery of the path inside an instance.  This makes
    the code thread-safe, allowing discovery of multiple paths in
    parallel (one instance of this class for each).  It also makes the
    code a bit cleaner (albeit slightly more complex) through not
    having to pass several state variables around.

    N.B. Instances should not be reused for multiple runs."""

    def __init__(self, initial_state, final_state):
        self.initial_state = initial_state
        self.final_state = final_state

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
            print "start state sane:", self.initial_state
        except VMPoolStateSanityError, e:
            sys.stderr.write("start state not sane: %s\n" % e)
            sys.exit(1)

        try:
            self.final_state.check_sane()
            print "end state sane:  ", self.final_state
        except VMPoolStateSanityError, e:
            sys.stderr.write("end state not sane: %s\n" % e)
            sys.exit(1)

    def find_path(self):
        self.check_endpoints_sane()
        self.compare_endpoints()

        if hasattr(self, 'path'):
            raise RuntimeError, \
                  "cannot reuse %s instance" % self.__class__.__name__

        self.path = VMPoolPath(self.initial_state, self.final_state)
        self.state_post_initial_shutdowns = self.do_initial_shutdowns()
        self.state_pre_final_provisions   = self.reverse_final_provisions()
        self.path.set_post_shutdown_state(self.state_post_initial_shutdowns)
        self.path.set_pre_provision_state(self.state_pre_final_provisions)

        migrations, cost = self.run()
        if migrations is None:
            return None

        self.path.set_migration_sequence(migrations)
        self.path.set_cost(cost)

        return self.path

    def compare_endpoints(self):
        """Figure out which VMs need to be shutdown first, which need
        to be migrated next, and finally which need to be provisioned
        at the end."""
        self.vms_to_shutdown = { }
        self.vms_to_migrate  = { }
        for start_vm in self.initial_state.vms():
            if start_vm not in self.final_state.vms():
                self.vms_to_shutdown[start_vm] = True
            else:
                from_host = self.initial_state.vm2vmhost[start_vm]
                to_host   = self.final_state.vm2vmhost[start_vm]
                if from_host != to_host:
                    self.vms_to_migrate[start_vm] = True

        self.vms_to_provision = { }
        for end_vm in self.final_state.vms():
            if end_vm not in self.initial_state.vms():
                self.vms_to_provision[end_vm] = self.final_state.vm2vmhost[end_vm]

    def do_initial_shutdowns(self):
        """Returns the pool state which results after doing all
        initial shutdowns.  Notice that the shutdowns can be done in
        any order, or in parallel."""
        cur = self.initial_state
        if len(self.vms_to_shutdown) > 0:
            for vm in self.vms_to_shutdown:
                cur = cur.shutdown_vm(vm)
        return cur

    def reverse_final_provisions(self):
        """Returns the pool state prior to performing the final set of
        provisioning actions.  Notice that these can be done in any
        order, or in parallel."""
        cur = self.final_state
        if len(self.vms_to_provision) > 0:
            for vm, vmhost in self.vms_to_provision.items():
                # Not a typo - we're going backwards here:
                cur = cur.shutdown_vm(vm)
        return cur

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
