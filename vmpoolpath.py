#!/usr/bin/python

import os

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
        self.initial_state = initial_state
        self.final_state = final_state

        self.path = [ ]
        self.cost = 0

    def compare_endpoints(self):
        """Figure out which VMs need to be shutdown first, which need
        to be migrated next, and finally which need to be provisioned
        at the end.
        """
        self.vms_to_shutdown = { }
        self.vms_to_migrate  = { }
        for start_vm in self.initial_state.vm_names():
            if start_vm not in self.final_state.vm_names():
                self.vms_to_shutdown[start_vm] = True
            else:
                from_host = self.initial_state.vm2vmhost[start_vm]
                to_host   = self.final_state.vm2vmhost[start_vm]
                if from_host != to_host:
                    self.vms_to_migrate[start_vm] = True

        self.vms_to_provision = { }
        for end_vm in self.final_state.vm_names():
            if end_vm not in self.initial_state.vm_names():
                self.vms_to_provision[end_vm] = \
                    self.final_state.vm2vmhost[end_vm]

        self.state_post_initial_shutdowns = self.do_initial_shutdowns()
        self.state_pre_final_provisions = self.reverse_final_provisions()

    def do_initial_shutdowns(self):
        """Returns the pool state which results after doing all
        initial shutdowns.  Notice that the shutdowns can be done in
        any order, or in parallel.
        """
        cur = self.initial_state
        if len(self.vms_to_shutdown) > 0:
            for vm in self.vms_to_shutdown:
                cur = cur.shutdown_vm(vm)
        return cur

    def reverse_final_provisions(self):
        """Returns the pool state prior to performing the final set of
        provisioning actions.  Notice that these can be done in any
        order, or in parallel.
        """
        cur = self.final_state
        if len(self.vms_to_provision) > 0:
            for vm, vmhost in self.vms_to_provision.items():
                # Not a typo - we're going backwards here:
                cur = cur.shutdown_vm(vm)
        return cur

    def set_migration_sequence(self, seq):
        self.migration_sequence = seq

    def set_cost(self, cost):
        self.cost = cost

    def summary(self):
        return "Path found with %d migrations and cost %d" % \
            (len(self.migration_sequence), self.cost)

    def report(self):
        print self.summary()
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

    def dump(self, indent=''):
        s = ''
        s += "%sshutdown: %s\n" % \
            (indent, ", ".join(sorted(self.vms_to_shutdown)))
        for migration in self.migration_sequence:
            s += "%s! %s: %s -> %s  cost %d\n" % \
                (indent,
                 migration.vm, migration.from_host,
                 migration.to_host, migration.cost())
        s += "%sprovision: %s\n" % \
            (indent, ", ".join(sorted(self.vms_to_provision)))
        return s

    def __str__(self):
        return self.dump()

    def __eq__(self, other):
        if isinstance(other, VMPoolPath):
            return str(self) == str(other)
        return NotImplemented

    def next_screen(self, clear_screen):
        raw_input("\nPress Enter to continue > ")
        if clear_screen:
            os.system("clear")
        else:
            print "\n----------------------------------------------------\n"

    def get_highlights(self):
        highlights = {
            'shutdown' : {
                vm: ('white', 'on_red', ['bold']) \
                    for vm in self.vms_to_shutdown
                },
            'migrate' : {
                vm: tuple(['yellow']) \
                    for vm in self.vms_to_migrate
                },
            'provision' : {
                vm: ('white', 'on_green', ['bold']) \
                    for vm in self.vms_to_provision
                },
            }
        highlights['before'] = dict(highlights['shutdown'].items() +
                                    highlights['migrate'].items())
        highlights['after']  = dict(highlights['provision'].items() +
                                    highlights['migrate'].items())
        return highlights

    def animate(self, clear_screen):
        if clear_screen:
            os.system("clear")

        host_width = 10
        meter_width = 80

        highlights = self.get_highlights()

        print "\n"
        print "From:\n"
        print self.initial_state.ascii_meters(
            host_width, meter_width,
            highlight_vms = highlights['before'])
        print "to:\n"
        print self.final_state.ascii_meters(
            host_width, meter_width,
            highlight_vms = highlights['after'])

        print self.summary()

        if self.vms_to_shutdown:
            self.next_screen(clear_screen)

            print "Shutdown phase\n"
            print "Current state:\n"
            print self.initial_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['shutdown'])
            print "Target state:\n"
            print self.final_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['after'])
            print "First shut down VMs: %s" % \
                ", ".join(sorted(self.vms_to_shutdown))

            self.next_screen(clear_screen)

            print "Shutdown phase\n"
            print "Current state:\n"
            print self.state_post_initial_shutdowns.ascii_meters(
                host_width, meter_width)
            print "Target state:\n"
            print self.final_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['after'])
            print "Shutdown complete."

        current_state = self.state_post_initial_shutdowns
        for migration in self.migration_sequence:
            self.next_screen(clear_screen)

            print "Migration phase\n"
            print "Current state:\n"
            highlight = { migration.vm.name : ('yellow', 'on_cyan') }
            print current_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlight)
            print "Target state:\n"
            print self.final_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['after'])
            print "%s: %s -> %s  cost %d" % \
                (migration.vm.name, migration.from_host.name,
                 migration.to_host.name, migration.cost())

            self.next_screen(clear_screen)

            print "Migration phase\n"
            print "Current state:\n"
            current_state = current_state.migrate(migration.vm.name,
                                                  migration.to_host.name)
            print current_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlight)
            print "Target state:\n"
            print self.final_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['after'])
            print "Migration of %s to %s complete." % \
                (migration.vm.name, migration.to_host.name)

        if self.vms_to_provision:
            self.next_screen(clear_screen)

            print "Provisioning phase\n"
            print "Current state:\n"
            print current_state.ascii_meters(
                host_width, meter_width)
            print "Target state:\n"
            print self.final_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['after'])
            print "Finally provision VMs: %s" % \
                ", ".join(sorted(self.vms_to_provision))

            self.next_screen(clear_screen)

            print "Provisioning phase\n"
            print "Current state:\n"
            print self.final_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['provision'])
            print "Target state:\n"
            print self.final_state.ascii_meters(
                host_width, meter_width,
                highlight_vms = highlights['after'])
            print "Provisioning complete.\n"

        print self.summary()
