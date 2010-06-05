#!/usr/bin/python

from types import *
from vodict import ValueOrderedDictionary 
from vmpoolstateerrors import VMPoolStateSanityError
from vmmigration import VMmigration
from vm import VM

class VMPoolPathFinder:
    """This class enables storage of the state data used during the
    discovery of the path inside an instance.  This makes the code
    thread-safe, allowing discovery of multiple paths in parallel (one
    instance of this class for each).  It also makes the code a bit
    cleaner (albeit slightly more complex) through not having to pass
    several state variables around.

    N.B. Instances should not be reused for multiple runs."""

    def __init__(self, initial_state):
        self.initial_state = initial_state

        # Nodes which have already been fully explored.
        self.done = { }

        # Cache objects by unique string.  This allows us to key
        # self.todo/done/distances/previous by unique string but still
        # be able to retrieve the corresponding object.  Note that
        # this relies on the VMPoolState instances remaining unchanged
        # after caching.  This should be thread-safe since the cache
        # is per path finder run (per instance), within which state
        # instances are constructed during neighbour exploration and
        # not subsequently altered.
        self.cache = { }
        self.cache_state(initial_state)

        # Did we find a path yet?
        self.found = False

    def cache_state(self, state):
        if state.unique() not in self.cache:
            self.cache[state.unique()] = state

    def check_endpoint_vms(self, final_state):
        self.vms_to_power_off = { }
        self.vms_to_move = { }
        self.vms_to_provision = { }
        for start_vm in self.initial_state.vms():
            assert type(start_vm) is StringType
            if start_vm not in final_state.vms():
                self.vms_to_power_off[start_vm] = True
            else:
                from_host = self.initial_state.vm2vmhost[start_vm]
                assert type(from_host) is StringType
                to_host   = final_state.vm2vmhost[start_vm]
                assert type(to_host) is StringType
                if from_host != to_host:
                    self.vms_to_move[start_vm] = VMmigration(start_vm, from_host, to_host)
        for end_vm in final_state.vms():
            if end_vm not in self.initial_state.vms():
                self.vms_to_provision[end_vm] = True
        if len(self.vms_to_provision) > 0:
            raise "Need to provision %s but provisioning not supported yet" \
                  % self.vms_to_provision.keys()
        print "VMs requiring power off:", \
              ' '.join(self.vms_to_power_off.keys())
        print "VMs definitely requiring a move:"
        for vm_to_move, migration in self.vms_to_move.iteritems():
            print "  ", migration

    def power_off(self):
        if len(self.vms_to_power_off) > 0:
            for vm in self.vms_to_power_off:
                print "Powering off VM %s" % vm
                self.initial_state.remove_vm(vm)
            # Reinitialize
            self.__init__(self.initial_state)
        
    def path_to(self, final_state):
        self.check_endpoint_vms(final_state)
        self.power_off()

        self.final_state = final_state
        self.final = final_state.unique()

        self.path = self._path_to(self.initial_state, final_state, self.vms_to_move)
        return self.path

    def _path_to(self, current, final, vms_to_move):
        print ". Looking for path from"
        print "       %s " % current
        print "    to %s"  % final
        if current.unique() == final.unique():
            if len(vms_to_move) == 0:
                return []
            else:
                raise "Reached final state and still had vms to move", vms_to_move
        elif len(vms_to_move) == 0:
            raise "No vms left to move and not yet at final state"        

        path = []
        while len(vms_to_move) > 0:
            vm = vms_to_move.keys()[0]
            migration = vms_to_move[vm]
            assert type(vm) is StringType
            path += self._do_migration(current, final, migration, vms_to_move)
        return path

    def _do_migration(self, current, final, migration, vms_to_move):
        """Returns path (sequence of migrations) ending with provided
        migration.  vms_to_move is the todo list.  migration is the
        ultimate target migration, but we may need to do others before
        we can do it, so it stays on the vms_to_move queue until we
        actually manage it."""

        vm = migration.vm.name
        from_host = migration.from_host
        to_host = migration.to_host
        print "+ Trying migration %s" % migration
        print "vms_to_move:", vms_to_move
        # sanity check
        if current.vm2vmhost[vm] != str(from_host):
            raise "going from %s, from_host of %s was %s and %s" % \
                (current, vm, current.vm2vmhost[vm], from_host)
        if final.vm2vmhost[vm] != str(to_host):
            raise "going to %s, to_host of %s was %s and %s" \
                % (final, vm, final.vm2vmhost[vm], to_host)
        
        new, reason = current.check_migration_sane(vm, to_host)

        if new:
            print ". migration sane"
            del vms_to_move[migration.vm.name]
            return [migration] + self._path_to(new, final, vms_to_move)
        else:
            print "  . can't migrate without first making way:"
            print "    %s" % reason
            del vms_to_move[vm]
            cession_path, new = self._cede(current, final, migration, vms_to_move)
            if not cession_path:
                raise "Couldn't make way for %s at %s" % (vm, current)
            vms_to_move[vm] = migration
            return cession_path + self._path_to(new, final)

            raise "NYI"

    def _cede(self, current, final, on_behalf_of, vms_to_move):
        """Allow the on_behalf_of migration to take place by moving as
        many VMs as it takes away from the migration's destination
        host.  Recurse if necessary."""
        usurper = on_behalf_of.vm
        usurper_host = on_behalf_of.from_host

        print "vms_to_move:", vms_to_move
        candidates = self._find_cession_candidates(vms_to_move, on_behalf_of)
        print "  -- candidates before sorting by cost:"
        for c in candidates:
            print "    %4d %s" % (c.cost(), c)
        candidates.sort()
        print "  -- candidates after sort by cost:"
        for c in candidates:
            print "    %4d %s" % (c.cost(), c)
            
        # TODO: try ceding multiple VMs
        for migration in candidates:
            # Need to be able to backtrack
            tmp_vms_to_move = vms_to_move.copy()
            (path, new) = self._do_migration(current, final, migration, tmp_vms_to_move)
            # ok, so we can get this VM out of the way, but will it
            # actually help?
            new2, reason2 = new.check_migration_sane(usurper, usurper_host)
            if new2:
                print "      + %s achieves effective cession" % migration
                return path
            else:
                print "      + %s doesn't achieve effective cession" % migration
                # next, no depth search for now
                pass
            raise "NYI"

    def _find_cession_candidates(self, vms_to_move, on_behalf_of):
        host_to_clear = on_behalf_of.to_host
        candidates = [ ] # find VMs to move away
        for (vm_name, migration) in vms_to_move.iteritems():
            if migration is on_behalf_of:
                raise "shouldn't be considering %s which cessation is on behalf of" % on_behalf_of
                continue
            if migration.from_host != host_to_clear:
                print "    - %s not on host being cleared (%s)" % (vm_name, host_to_clear)
                continue
            vm = VM.vms[vm_name]
            if not vm:
                raise "couldn't lookup VM %s" % vm_name
            print "    + %s could make way" % vm_name
            candidates.append(migration)
        return candidates

    def report(self):
        for migration in self.path:
            print migration
