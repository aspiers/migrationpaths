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

    N.B. Instances should not be reused for multiple runs."""

    def run(self):
        return self.solve(self.vms_to_migrate)

    def solve(self, vms_to_migrate):
        vms_to_migrate = copy.copy(self.vms_to_migrate)
        
        print ". Looking for path from"
        print "       %s " % current
        print "    to %s"  % final
        if current.unique() == final.unique():
            if len(vms_to_migrate) == 0:
                return []
            else:
                raise RuntimeError, "Reached final state and still had vms to move", vms_to_migrate
        elif len(vms_to_migrate) == 0:
            raise RuntimeError, "No vms left to move and not yet at final state"        

        path = []
        while len(vms_to_migrate) > 0:
            vm = vms_to_migrate.keys()[0]
            migration = vms_to_migrate[vm]
            assert type(vm) is StringType
            path += self._do_migration(current, final, migration, vms_to_migrate)
        return path

    def _do_migration(self, current, final, migration, vms_to_migrate):
        """Returns path (sequence of migrations) ending with provided
        migration.  vms_to_migrate is the todo list.  migration is the
        ultimate target migration, but we may need to do others before
        we can do it, so it stays on the vms_to_migrate queue until we
        actually manage it."""

        vm = migration.vm.name
        from_host = migration.from_host
        to_host = migration.to_host
        print "+ Trying migration %s" % migration
        print "vms_to_migrate:", vms_to_migrate
        # sanity check
        if current.vm2vmhost[vm] != str(from_host):
            raise RuntimeError, "going from %s, from_host of %s was %s and %s" % \
                (current, vm, current.vm2vmhost[vm], from_host)
        if final.vm2vmhost[vm] != str(to_host):
            raise RuntimeError, "going to %s, to_host of %s was %s and %s" \
                % (final, vm, final.vm2vmhost[vm], to_host)

        try:
            new = current.check_migration_sane(vm, to_host)
        except VMPoolStateSanityError, exc:
            print "  . can't migrate without first making way:"
            print "    %s" % exc
            del vms_to_migrate[vm]
            cession_path, new = self._cede(current, final, migration, vms_to_migrate)
            if not cession_path:
                raise RuntimeError, "Couldn't make way for %s at %s" % (vm, current)
            vms_to_migrate[vm] = migration
            return cession_path + self._path_to(new, final)

            raise RuntimeError, "NYI"

        print ". migration sane"
        del vms_to_migrate[migration.vm.name]
        return [migration] + self._path_to(new, final, vms_to_migrate)

    def _cede(self, current, final, on_behalf_of, vms_to_migrate):
        """Allow the on_behalf_of migration to take place by moving as
        many VMs as it takes away from the migration's destination
        host.  Recurse if necessary."""
        usurper = on_behalf_of.vm
        usurper_host = on_behalf_of.from_host

        print "vms_to_migrate:", vms_to_migrate
        candidates = self._find_cession_candidates(vms_to_migrate, on_behalf_of)
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
            tmp_vms_to_migrate = vms_to_migrate.copy()
            (path, new) = self._do_migration(current, final, migration, tmp_vms_to_migrate)
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
            raise RuntimeError, "NYI"

    def _find_cession_candidates(self, vms_to_migrate, on_behalf_of):
        host_to_clear = on_behalf_of.to_host
        candidates = [ ] # find VMs to move away
        for (vm_name, migration) in vms_to_migrate.iteritems():
            if migration is on_behalf_of:
                raise RuntimeError, "shouldn't be considering %s which cessation is on behalf of" % on_behalf_of
                continue
            if migration.from_host != host_to_clear:
                print "    - %s not on host being cleared (%s)" % (vm_name, host_to_clear)
                continue
            vm = VM.vms[vm_name]
            if not vm:
                raise RuntimeError, "couldn't lookup VM %s" % vm_name
            print "    + %s could make way" % vm_name
            candidates.append(migration)
        return candidates

