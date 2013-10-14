#!/usr/bin/python

import copy
from types import *

from vmpoolstateerrors import VMPoolStateSanityError
from vmmigration import VMmigration
from pathfinder import VMPoolPathFinder
from vm import VM
from vmhost import VMhost

class VMPoolAdamPathFinder(VMPoolPathFinder):
    """Recursive path finding algorithm based around the concept of a
    TODO list containing which VMs have not yet reached their final
    destination host.  The TODO list is iterated over until it is
    empty.  If a VM cannot be immediately migrated to its final
    destination host, other VMs on that host are displaced in order to
    accommodate it.  Displacement favours migrations already in the
    TODO list, to avoid accumulating unnecessary "migration debt".

    Displacement happens recursively in a manner which travels down
    the dependency tree (i.e. if migration B is required before
    migration is A possible, then A is B's parent in the tree), until
    we reach a leaf node migration which can be performed immediately.
    Then its ancestor migrations can be performed in reverse order
    by backtracking up the tree again.

    Each migration enacted will result in an update of the TODO list
    (passed around in a variable named ``vms_to_migrate`` or similar).

    We also need to lock VMs in place when exploring potential
    displacement paths, to exclude them from the list of candidates
    for displacement.  This helps break mutual dependency cycles
    (e.g. swapping a pair of VMs between different hosts when they
    cannot co-exist on the same host), which would otherwise cause
    infinitely deep recursion.

    Instances of this class should not be reused for multiple
    path-finding runs.
    """

    def run(self):
        self.debug(2, self.path.challenge_visualization(10, 80))
        return self._solve([],
                           self.path.state_post_initial_shutdowns,
                           self.path.vms_to_migrate)

    def _solve(self, path, current_state, vms_to_migrate):
        """Returns a list of sane migrations which transform the
        current state into the final state, or None if no path
        to the final state could be found.

        path is the path from the initial state to current_state,
        and is used purely for debugging.

        vms_to_migrate is a dict of names of all the VMs whose
        placement needs to change between the current state and the
        final state; it is an optimisation which allows us to
        calculate this incrementally rather than comparing all VMs
        each time we recursively invoke solve().
        """
        self.debug(1, "\n>> _solve")
        self.debug(1, repr(path))

        if self._solved(current_state, vms_to_migrate):
            return []

        final_state = self.path.state_pre_final_provisions

        for vm_name in sorted(vms_to_migrate.keys()):
            from_host = current_state.get_vm_vmhost(vm_name)
            to_host = self.target_host(vm_name)
            migration = VMmigration(vm_name, from_host, to_host)
            self.debug(2, "solve: %s" % migration)
            path_segment, new_state, new_vms_to_migrate, locked_vms = \
                self._solve_to(path, current_state, migration, vms_to_migrate, {})
            if path_segment:
                path_remainder = self._solve(path + path_segment, new_state,
                                             new_vms_to_migrate)
                if path_remainder is not None:
                    return path_segment + path_remainder

        return None

    def _solved(self, current_state, vms_to_migrate):
        if current_state == self.path.state_pre_final_provisions:
            if len(vms_to_migrate) == 0:
                return True
            else:
                print self.get_debug()
                raise RuntimeError(
                    "Reached final state and "
                    "still had vms to move: %s" % vms_to_migrate)
        elif len(vms_to_migrate) == 0:
            print self.get_debug()
            raise RuntimeError("No vms left to move "
                               "and not yet at final state")
        else:
            return False

    def _solve_to(self, path, current_state, migration,
                  vms_to_migrate, locked_vms):
        """Finds a sequence of sane migrations from the current state
        ending with the given migration.

        Returns a (path, new_state, vms_to_migrate, locked_vms) tuple:
        path
            the list of sane migrations from the current state ending
            with the given migration, or None if no such path is found
        new_state
            the new state reached by the given path, or None
        vms_to_migrate
            an updated copy of the provided vms_to_migrate dict, taking into
            account any VMs which have been migrated
        locked_vms
            an updated copy of the provided locked_vms dict, taking into
            account any VMs which have been migrated

        The given VM should be included in the vms_to_migrate TODO
        dict, and will stay there until we actually manage to migrate
        it to its final destination, since we may need to perform
        other displacement migrations first.

        Recursively calls _displace() when necessary.
        """
        self.debug(1, "\n>> solve_to %s" % migration)
        self.debug(1, repr(path))

        single, new_state, new_vms_to_migrate = \
            self._solve_single(path, current_state, migration,
                               vms_to_migrate, locked_vms)

        self.debug(1, "")
        if single is not None:
            self.debug(1, "<< solved without displacement")
            return single, new_state, new_vms_to_migrate, locked_vms

        self.debug(2, "can't migrate %s without first making way:" \
                       % migration.vm)
        self.debug(2, "%s" % new_state)
        self.debug(2, "vms_to_migrate pre displacement: %s" % \
                       ", ".join(vms_to_migrate.keys()))
        displacement_path, displaced_state, vms_to_migrate, locked_vms = \
            self._displace(path, current_state, migration,
                           vms_to_migrate, locked_vms)
        if displacement_path is None:
            self.debug(1, "<< Couldn't make way for %s at %s" % \
                           (migration.vm.name, current_state))
            return None, None, None, None

        self.debug(2, "_solve_to returning: [%s]\n" % \
                       ", ".join([ str(m) for m in displacement_path ]))
        self.debug(2, "vms_to_migrate: %s" % \
                       ", ".join(sorted(vms_to_migrate.keys())))
        return displacement_path, displaced_state, vms_to_migrate, locked_vms

    def _solve_single(self, path, current_state, migration,
                      vms_to_migrate, locked_vms):
        """Checks the given migration is sane, and returns the updated state.

        Returns a (path, new_state, vms_to_migrate) tuple:
        path
            a singleton list of the migration, or None
            if the migration is not sane
        new_state
            the new state reached by the given migration, or
            VMPoolStateSanityError if the migration is not sane
        vms_to_migrate
            an updated version of vms_to_migrate, or None
        """
        self.debug(1, "\n>> solve_single %s" % migration)
        self.debug(1, repr(path))

        vm_highlights = self._get_vm_highlights(vms_to_migrate, locked_vms)
        vm_highlights[migration.vm.name] = ('yellow', 'on_cyan')
        vmhost_highlights = { migration.to_host.name :
                                  ('white', 'on_green', ['bold']) }
        self.debug_state(current_state, vms_to_migrate, locked_vms,
                         vm_highlights, vmhost_highlights)

        try:
            new_state = \
                current_state.check_migration_sane(migration.vm.name,
                                                   migration.to_host)
        except VMPoolStateSanityError, exc:
            self.debug(2, "<< migration not currently possible")
            return None, exc, None

        self.debug(2, "<< migration sane; new segment: %s" % migration)
        vms_to_migrate = self._update_vms_to_migrate(vms_to_migrate, migration)

        return [ migration ], new_state, vms_to_migrate

    def _update_vms_to_migrate(self, vms_to_migrate, migration):
        vms_to_migrate = copy.copy(vms_to_migrate)
        vm_name = migration.vm.name
        target_host = self.target_host(vm_name)
        if migration.to_host == VMhost.vmhosts[target_host.name]:
            # We're migrating the VM to its final destination -
            # ensure it's not on the todo list any more.
            if vm_name in vms_to_migrate:
                del vms_to_migrate[vm_name]
        else:
            # We're migrating the VM *away* from its final destination
            # so add it (back) to the todo list.
            vms_to_migrate[vm_name] = True

        return vms_to_migrate

    # When iterating through candidate migrations for displacement,
    # some will only be accepted if we can perform the migration
    # immediately, rather than having to recursively find other
    # displacements first.
    ALLOW_RECURSION = 0
    PROHIBIT_RECURSION = 1

    def _displace(self, path, current_state, on_behalf_of,
                  vms_to_migrate, locked_vms):
        """Allow the on_behalf_of migration to take place by
        displacing as many VMs as required away from the migration's
        destination host.  Any VMs whose name is in the locked_vms
        dict is excluded from displacement.

        Returns a (path, new_state, vms_to_migrate, locked_vms) tuple:
        path
            the list of sane migrations ending with on_behalf_of,
            or None if no such path is found
        new_state
            the new state reached by the given path, or None
        vms_to_migrate
            an updated copy of the provided vms_to_migrate dict, taking into
            account any VMs which have been migrated
        locked_vms
            an updated copy of the provided locked_vms dict, taking into
            account any VMs which have been migrated

        Recursively calls _displace() / _solve_single() as necessary.
        """
        usurper_name = on_behalf_of.vm.name
        self.debug(2, "\n_displace from %s for %s" % \
                       (on_behalf_of.to_host.name, usurper_name))
        self.debug(2, "vms_to_migrate: %s" % \
                       ", ".join(vms_to_migrate.keys()))

        # Ensure displacement can't touch the VM we're displacing on behalf of,
        # otherwise when we've successfully displaced, we might not be able to
        # perform the migration we originally wanted to do.
        locked_for_displacement = copy.copy(locked_vms)
        locked_for_displacement[usurper_name] = True
        self.debug(2, "+ locked %s" % usurper_name)

        candidates = \
            self._find_displacement_candidates(path, current_state,
                                               vms_to_migrate, on_behalf_of,
                                               locked_for_displacement)
        for migration, recursion_mode in candidates:
            if recursion_mode == self.PROHIBIT_RECURSION:
                (partial_displacements,
                 partially_displaced_state,
                 partially_displaced_vms_to_migrate) = \
                    self._solve_single(path, current_state, migration,
                                       vms_to_migrate, locked_for_displacement)
                if partial_displacements is not None:
                    self.debug_state(partially_displaced_state,
                                      partially_displaced_vms_to_migrate,
                                      locked_for_displacement)

                # no change to which VMs are locked
                partially_displaced_locked_vms = locked_for_displacement
            elif recursion_mode == self.ALLOW_RECURSION:
                (partial_displacements,
                 partially_displaced_state,
                 partially_displaced_vms_to_migrate,
                 partially_displaced_locked_vms) = \
                    self._solve_to(path, current_state, migration,
                                   vms_to_migrate, locked_for_displacement)
            else:
                raise RuntimeError("BUG: unknown recursion_mode %s" %
                                   recursion_mode)

            if partial_displacements is None:
                continue
            self.debug(2, "+ path to unvalidated displacement: %s" % \
                           partial_displacements)

            remaining_displacements, fully_displaced_state, \
                fully_displaced_vms_to_migrate, displaced_locked_vms = \
                self._recurse_displacement(path + partial_displacements,
                                           partially_displaced_state,
                                           migration, on_behalf_of,
                                           partially_displaced_vms_to_migrate,
                                           partially_displaced_locked_vms)
            if remaining_displacements is None:
                # couldn't find a way to make this candidate work
                continue

            displacements = partial_displacements + remaining_displacements

            self.debug(2, "<< solved displacement %d for %s" % \
                           (self.candidate_search_count, on_behalf_of))
            # self.debug(2, "[%s]" % \
            #                ", ".join([ str(m) for m in displacements ]))

            return displacements, fully_displaced_state, \
                fully_displaced_vms_to_migrate, displaced_locked_vms

        self.debug(2, "<< ran out of displacement candidates! " \
                       "giving up on displacement.")
        return None, None, None, None

    candidate_search_count = 0

    def _recurse_displacement(self, path, current_state, migration,
                              on_behalf_of, vms_to_migrate, locked_vms):
        """Once the given displacement migration has been made, see
        whether it was sufficient to allow the on_behalf_of migration
        to take place, and if not, continue recursively displacing
        more VMs until we've displaced enough, or until we reach an
        impasse.

        Returns a (path, new_state, vms_to_migrate, locked_vms) tuple:
        path
            the list of sane migrations ending with on_behalf_of,
            or None if no such path is found
        new_state
            the new state reached by the given path, or None
        vms_to_migrate
            an updated copy of the provided vms_to_migrate dict, taking into
            account any VMs which have been migrated
        locked_vms
            an updated copy of the provided locked_vms dict, taking into
            account any VMs which have been migrated

        Recursively calls _displace() as necessary.
        """
        self.debug(1, "\n>> recurse_displacement for %s" % on_behalf_of)
        self.debug(1, repr(path))

        try:
            current_state = \
                current_state.check_migration_sane(on_behalf_of.vm.name,
                                                   on_behalf_of.to_host)
            displacement_sufficient = True
        except VMPoolStateSanityError, exc:
            displacement_sufficient = False

        vms_to_migrate = self._update_vms_to_migrate(vms_to_migrate,
                                                     on_behalf_of)

        if displacement_sufficient:
            self.debug(2, "<< %s achieves effective displacement" % migration)
            return [ on_behalf_of ], current_state, vms_to_migrate, locked_vms
        else:
            self.debug(2, "+ %s doesn't achieve effective displacement" % \
                           migration)
            # keep on displacing
            rest_of_path, current_state, displaced_vms_to_migrate, locked_vms = \
                self._displace(path + [ on_behalf_of ], current_state,
                               on_behalf_of, vms_to_migrate, locked_vms)
            if rest_of_path is None:
                self.debug(2, "<< couldn't displace enough; give up on this path")
                return None, None, None, None

            self.debug(2, "<< finished displacement for %s" % on_behalf_of)
            return rest_of_path, current_state, \
                displaced_vms_to_migrate, locked_vms

    def _find_displacement_candidates(self, path, current_state, vms_to_migrate,
                                      on_behalf_of, locked_vms):
        """Generator which provides migrations displacing VMs from the
        host targeted by the on_behalf_of migration.  The use of a
        generator means the candidates are provided lazily, so
        searching stops as soon as a suitable one is found.

        Migration candidates are sorted in descending priority as
        follows:

        1. migrating VMs which we need to move anyway to their
           final destination, directly or indirectly via displacment
        2. migrating VMs which we need to move anyway, directly to a non-final
           destination
        3. migrating VMs which we wouldn't otherwise need to move,
           directly away from their non-final destination

        This minimises the number of workloads which are potentially
        impacted, and hopefully helps minimise the number of
        required migrations too.
        """
        VMPoolAdamPathFinder.candidate_search_count += 1

        def _debug_cand(msg):
            self.debug(2, "[%d] %s" % \
                           (VMPoolAdamPathFinder.candidate_search_count, msg))

        # We iterate searching for case 1, and queue up any instances
        # of cases 2 and 3 we find for later, in case we need them.
        case_two, case_three = [ ], [ ]

        displace_from_host = on_behalf_of.to_host
        _debug_cand("finding candidates to displace from %s" %
                    displace_from_host.name)

        for vm_name in current_state.vmhost2vms[displace_from_host.name]:
            if vm_name in locked_vms:
                _debug_cand("1  - %s is locked; not considering" % vm_name)
                continue
            if vm_name in vms_to_migrate:
                to_host = self.target_host(vm_name)
                migration = VMmigration(vm_name, displace_from_host, to_host)
                if migration is on_behalf_of:
                    raise RuntimeError("shouldn't be considering %s "
                                       "which displacement is on behalf of" %
                                       on_behalf_of)
                _debug_cand("1  ? consider required displacement %s" % migration)
                case_two.append((vm_name, to_host))
                _debug_cand("1  + saved case 2: %s ! %s" %
                            (vm_name, to_host.name))
                # We need to perform this migration anyway, so it
                # shouldn't cost us too dearly to recursively displace
                # if necessary in order to make it possible.
                yield (migration, self.ALLOW_RECURSION)
            else:
                case_three.append(vm_name)
                _debug_cand("1  + saved case 3: %s" % vm_name)

        # Case 2: migrating VMs which we need to move anyway, directly
        # to a non-final destination.
        for to_host_name in current_state.vmhost_names():
            to_host = VMhost.vmhosts[to_host_name]
            if to_host == displace_from_host:
                continue
            for vm_name, final_host in case_two:
                if to_host == final_host:
                    continue
                migration = VMmigration(vm_name, displace_from_host, to_host)
                _debug_cand("2  ? consider extra displacement: %s" % migration)
                # This migration isn't ideal, so if it's not directly possible,
                # try something else instead.
                yield (migration, self.PROHIBIT_RECURSION)

        # Case 3. migrating VMs which we wouldn't otherwise need to move,
        # directly away from their non-final destination
        for to_host_name in current_state.vmhost_names():
            to_host = VMhost.vmhosts[to_host_name]
            if to_host == displace_from_host:
                continue
            for vm_name in case_three:
                migration = VMmigration(vm_name, displace_from_host, to_host)
                _debug_cand("3  ? consider extra displacement: %s" % migration)
                # This migration isn't ideal, so if it's not directly possible,
                # try something else instead.
                yield (migration, self.PROHIBIT_RECURSION)

        _debug_cand("no more displacement candidates")

    def target_host(self, vm_name):
        target_host_name = \
            self.path.state_pre_final_provisions.get_vm_vmhost(vm_name)
        return VMhost.vmhosts[target_host_name]
