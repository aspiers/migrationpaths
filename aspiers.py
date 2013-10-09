#!/usr/bin/python

import copy
from types import *
from vmpoolstateerrors import VMPoolStateSanityError
from vmmigration import VMmigration
from pathfinder import VMPoolPathFinder
from vm import VM

class VMPoolAdamPathFinder(VMPoolPathFinder):
    """This class enables storage of the state data used during the
    discovery of the path inside an instance.  This makes the code
    thread-safe, allowing discovery of multiple paths in parallel (one
    instance of this class for each).  It also makes the code a bit
    cleaner (albeit slightly more complex) through not having to pass
    several state variables around.

    N.B. Instances should not be reused for multiple runs.
    """

    def run(self):
        return self._solve(self.state_post_initial_shutdowns,
                           self.vms_to_migrate)

    def _solve(self, current_state, vms_to_migrate):
        """Returns a list of sane migrations which transform the
        current state into the final state, or None if no path
        to the final state could be found.

        vms_to_migrate is a dict of names of all the VMs whose
        placement needs to change between the current state and the
        final state; it is an optimisation which allows us to
        calculate this incrementally rather than comparing all VMs
        each time we recursively invoke solve().
        """
        if self._solved(current_state, vms_to_migrate):
            return []

        print ". Looking for path from"
        print "       %s " % current_state
        print "    to %s"  % self.state_pre_final_provisions
        print "  vms_to_migrate: %s" % ", ".join(vms_to_migrate.keys())

        path = []
        while len(vms_to_migrate) > 0:
            print "-------------------------------------------------"
            vm_name = sorted(vms_to_migrate.keys())[0]
            from_host = current_state.get_vm_vmhost(vm_name)
            to_host = self.target_host(vm_name)
            migration = VMmigration(vm_name, from_host, to_host)
            path_segment, new_state, new_vms_to_migrate = \
                self._solve_to(current_state, migration, vms_to_migrate, {})
            if path_segment:
                path += path_segment
                vms_to_migrate = new_vms_to_migrate
                current_state = new_state
            else:
                raise RuntimeError, "oh dear"

        return path

    def _solved(self, current_state, vms_to_migrate):
        if current_state == self.state_pre_final_provisions:
            if len(vms_to_migrate) == 0:
                return True
            else:
                raise RuntimeError, "Reached final state and still had vms to move", vms_to_migrate
        elif len(vms_to_migrate) == 0:
            raise RuntimeError, "No vms left to move and not yet at final state"
        else:
            return False

    def _solve_to(self, current_state, migration, vms_to_migrate, locked_vms):
        """Finds a sequence of sane migrations from the
        current state ending with the given migration.

        Returns a (path, new_state) tuple:
        path -- the list of migrations from the current state ending
                with the given migration, or None if no such path is found
        new_state -- the new state reached by the given path, or None
        vms_to_migrate -- an updated version of vms taking into account
                          displaced VMs

        # FIXME: This still true?
        # The given VM should be included in the vms_to_migrate TODO
        # dict, and will stay there until we actually manage to migrate
        # it to its final destination, since we may need to perform
        # other displacement migrations first.

        Recursively calls _solve() (sometimes via _displace()).
        """
        print "\nsolve_to %s" % migration
        print "  from %s" % current_state
        print "  vms_to_migrate: %s" % ", ".join(vms_to_migrate.keys())
        print "  locked_vms: %s" % ", ".join(locked_vms.keys())
        path = [ migration ]
        vms_to_migrate = copy.copy(vms_to_migrate)
        vm_name = migration.vm.name
        if migration.to_host == self.target_host(vm_name):
            if vm_name in vms_to_migrate:
                del vms_to_migrate[vm_name]
        else:
            vms_to_migrate[vm_name] = True

        try:
            new_state = current_state.check_migration_sane(vm_name, migration.to_host)
            sane = True
        except VMPoolStateSanityError, exc:
            sane = False

        if sane:
            print "  + migration sane"
        else:
            print "  x can't migrate without first making way:"
            print "    %s" % exc
            print "    vms_to_migrate pre displacement: %s" % ", ".join(vms_to_migrate.keys())
            displacement_path, new_state, vms_to_migrate = \
                self._displace(current_state, migration, vms_to_migrate, locked_vms)
            if displacement_path is None:
                print "Couldn't make way for %s at %s\n" % (vm_name, current_state)
                return None, None, None
            path = displacement_path

        print "  vms_to_migrate: %s" % ", ".join(vms_to_migrate.keys())

        print "SEGMENT: %s\n" % ", ".join([ str(m) for m in path ])
        return path, new_state, vms_to_migrate

    def _displace(self, current_state, on_behalf_of, vms_to_migrate, locked_vms):
        """Allow the on_behalf_of migration to take place by
        displacing as many VMs as required away from the migration's
        destination host.  Any VMs whose name is in the locked_vms
        dict is excluded from displacement.

        Returns a (path, new_state, vms_to_migrate) tuple:
        path -- a list of sane migrations ending with on_behalf_of,
                or None if no such path is found
        new_state -- the new state reached by the given path, or None
        vms_to_migrate -- an updated version of vms taking into account
                          displaced VMs

        Recursively calls _solve_to() / _displace() as necessary.
        """
        usurper_name = on_behalf_of.vm.name
        print "  - displace from %s for %s" % (on_behalf_of.to_host, usurper_name)
        print "    vms_to_migrate: %s" % ", ".join(vms_to_migrate.keys())
        locked_for_displacement = copy.copy(locked_vms)
        locked_for_displacement[usurper_name] = True
        print "    + locked %s" % usurper_name

        candidates = \
            self._find_displacement_candidates(current_state, vms_to_migrate,
                                               on_behalf_of, locked_vms)
        for migration in candidates:
            (displacement_path, displaced_state, displaced_vms_to_migrate) = \
                self._solve_to(current_state, migration, vms_to_migrate,
                               locked_for_displacement)
            if displacement_path is None:
                continue
            
            # ok, so we can get this VM out of the way, but will it
            # actually help?
            displace_from_host = on_behalf_of.to_host
            try:
                displaced_state = \
                    displaced_state.check_migration_sane(usurper_name, displace_from_host)
                displacement_sufficient = True
            except VMPoolStateSanityError, exc:
                displacement_sufficient = False

            if displacement_sufficient:
                print "      + %s achieves effective displacement" % migration
                displacement_path.append(migration)
                return displacement_path, displaced_state, displaced_vms_to_migrate
            else:
                print "      + %s doesn't achieve effective displacement" % migration
                # keep on displacing
                return self._displace(displaced_state, migration,
                                      displaced_vms_to_migrate, locked_vms)

        return None, None, None

    def _find_displacement_candidates(self, current_state, vms_to_migrate,
                                      on_behalf_of, locked_vms):
        """Generator which provides migrations displacing VMs from the
        host targeted by the on_behalf_of migration.  The use of a
        generator means the candidates are provided lazily, so
        searching stops as soon as a suitable one is found.

        Migration candidates are sorted in descending priority as
        follows:

        1. migrating VMs which we need to move anyway, to their
           final destination
        2. migrating VMs which we need to move anyway, to a non-final
           destination
        3. migrating VMs which we wouldn't otherwise need to move
        
        This minimises the number of workloads which are potentially
        impacted, and hopefully helps minimise the number of
        required migrations too.
        """
        # We iterate searching for case 1, and queue up any instances
        # of cases 2 and 3 we find for later, in case we need them.
        case_two, case_three = [ ], [ ]

        displace_from_host = on_behalf_of.to_host

        for vm_name in current_state.vmhost2vms[displace_from_host]:
            if vm_name in locked_vms:
                print "|1  - %s is locked; not considering" % vm_name
                continue
            if vm_name in vms_to_migrate:
                to_host = self.target_host(vm_name)
                migration = VMmigration(vm_name, displace_from_host, to_host)
                if migration is on_behalf_of: 
                    raise RuntimeError, "shouldn't be considering %s which displacement is on behalf of" % on_behalf_of
                print "|1  ? consider required displacement %s" % migration
                case_two.append((vm_name, to_host))
                print "|1  + saved case 2: %s ! %s" % (vm_name, to_host)
                yield migration
            else:
                case_three.append(vm_name)
                print "|1  + saved case 3: %s" % vm_name

        # need to consider all the possible places we could displace these VMs to
        for to_host in current_state.vmhost_names():
            if to_host == displace_from_host:
                continue
            for vm_name, final_host in case_two:
                if to_host == final_host:
                    continue
                migration = VMmigration(vm_name, displace_from_host, to_host)
                print "|2  ? consider extra displacement: %s" % migration
                yield migration

        # need to consider all the possible places we could displace these VMs to
        for to_host in current_state.vmhost_names():
            if to_host == displace_from_host:
                continue
            for vm_name in case_three:
                migration = VMmigration(vm_name, displace_from_host, to_host)
                print "|3  ? consider extra displacement: %s" % migration
                yield migration

        print "| no more displacement candidates"

    def target_host(self, vm_name):
        return self.state_pre_final_provisions.get_vm_vmhost(vm_name)
