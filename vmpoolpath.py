#!/usr/bin/python

from vm import VM
from vmhost import VMhost

class VMPoolPath:
    """
    This class represents an ordered sequence of VM shutdowns,
    migrations, and provisions, between two VM pool states.  The VM
    shutdowns always happen first, followed by the migrations, then
    finally the provisions last.
    """

    def __init__(self, initial_state, final_state):
        self.vms_to_shutdown = [ ]
        self.vms_to_provision = [ ]
        self.path = [ ]
        self.cost = 0

    def set_vms_to_shutdown(self, vms_to_shutdown):
        self.vms_to_shutdown = vms_to_shutdown

    def set_post_shutdown_state(self, state):
        self.post_shutdown_state = state

    def set_pre_provision_state(self, state):
        self.pre_provision_state = state

    def set_vms_to_provision(self, vms_to_provision):
        self.vms_to_provision = vms_to_provision

    def set_migration_sequence(self, seq):
        self.migration_sequence = seq

    def set_cost(self, cost):
        self.cost = cost

    def report(self):
        print "Short path found with %d migrations and cost %d:" % \
            (len(self.migration_sequence), self.cost)
        if self.vms_to_shutdown:
            print "- First shut down VMs: %s" % ", ".join(self.vms_to_shutdown)

        current_state = self.post_shutdown_state
        print "  Start: ", current_state
        current_state.show_ascii_meters(10, 80, indent='  ')
        # for state in self.path[1:]:
        #     prev = self.previous[state]
        #     from_state = self.cache[prev]
        #     (vm, to_host, cost) = self.route[state]
        #     from_host = from_state.vm2vmhost[vm]
        #     print "%s: %s -> %s  cost %d" % (vm, from_host, to_host, cost)
        for migration in self.migration_sequence:
            print "! %s: %s -> %s  cost %d" % \
                (migration.vm, migration.from_host,
                 migration.to_host, migration.cost())
            current_state = current_state.migrate(migration.vm.name,
                                                  migration.to_host.name)
            current_state.show_ascii_meters(10, 80, indent='  ')
        print "  End:   ", self.pre_provision_state

        if self.vms_to_provision:
            provisions = [ "%s on %s" % (vm, vmhost) \
                               for vm, vmhost in self.vms_to_provision ]
            print "+ Finally provision VMs: %s" % ", ".join(provisions)
