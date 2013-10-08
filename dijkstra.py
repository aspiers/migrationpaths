#!/usr/bin/python

from vodict import ValueOrderedDictionary 
from vmpoolstateerrors import VMPoolStateSanityError
from pathfinder import VMPoolPathFinder
from vmmigration import VMmigration
from vmpoolpath import VMPoolPath

class VMPoolShortestPathFinder(VMPoolPathFinder):
    """This class enables storage of the state data used during the
    discovery of the shortest path inside an instance.  This makes the
    code thread-safe, allowing discovery of multiple shortest paths in
    parallel (one instance of this class for each).  It also makes the
    code a bit cleaner (albeit slightly more complex) through not
    having to pass several state variables around.

    N.B. Instances should not be reused for multiple runs.
    """

    # // This is the algorithm in pseudo-code from
    # // http://en.wikipedia.org/wiki/Dijkstra's_algorithm
    #
    # Q := set of all nodes
    # while Q is not empty:
    #     u := node in Q with smallest dist[]
    #     // "explore" node u:
    #     for each neighbor v of u still in Q:
    #         check if optimal path to v
    #     // u is now fully "explored"
    #     remove u from Q
    #
    # // However we don't know Q in advance so we have to build it
    # // iteratively by adding neighbours which haven't already
    # // been "explored" (for definition of which see above).  So
    # // instead we track two sets of nodes:
    # //
    # // "todo list" T: nodes discovered but not fully explored.
    # // This is a conceptual subset of Q.
    # T := [ start node ]
    #
    # // "done list" D: fully explored nodes.
    # // This is conceptually equivalent to ~Q, and allows us to
    # // distinguish between nodes which are in Q but have not been
    # // discovered yet, vs. nodes which have been removed from Q.
    # D := empty
    #
    # while T is not empty:
    #     u := node in Q with smallest dist[]
    #     for each neighbor v of u not in D:
    #         check for shorter path to v
    #         if v not in T:
    #             add v to T
    #         
    #     // u is now "explored"
    #     move u from T to D

    def init(self):
        initial_cost = 0

        # Nodes which still need to be explored, sorted by distance ascending.
        self.todo = ValueOrderedDictionary()
        self.todo[self.initial_state.unique()] = initial_cost

        # Nodes which have already been fully explored.
        self.done = { }

        # Distances for all nodes (both todo and done)
        self.distances = { self.initial_state.unique() : initial_cost }

        # Mapping from any node in shortest path to its previous node
        self.previous = { }

        # Mapping from any node in shortest path to the migration
        # which gets there from the previous node.
        self.route = { }

    def run(self):
        self.end = self.state_pre_final_provisions.unique()
        while len(self.todo) > 0:
            print "todo list:"
            for s in self.todo:
                print "  %2d: %s" % (self.distances[s], s)
            current, dist = self.todo.shift()
            if current == self.end:
                self.found = True
                break
            current_state = self.cache_lookup(current)
            print "current_state:", current_state
            self.explore_neighbours(current_state)

            print "    < marking as done:", current_state
            self.done[current] = True

        print "todo list size:", len(self.todo)
        print "done list size:", len(self.done)

        if self.found:
            return self.trace_path()
        else:
            return None

    def explore_neighbours(self, current_state):
        """Explore all neighbours from current state."""
        
        # Assuming we're given the end state in advance, optimise the
        # search order by prioritising exploration of neighbours
        # resulting from migrating VMs which need to be migrated, over
        # exploration of those resulting from VMs which do not.
        migrated_vms = [ ]
        unmigrated_vms = [ ]
        assert current_state
        for vm in current_state.vm_names():
            if vm in self.vms_to_migrate:
                migrated_vms.append(vm)
            else:
                unmigrated_vms.append(vm)

        for vm in migrated_vms + unmigrated_vms:
            from_host = current_state.get_vm_vmhost(vm)
            print "  examining %s, currently on %s" % (vm, from_host)

            for to_host in current_state.vmhost2vms:
                if from_host == to_host:
                    continue

                new_state = current_state.migrate(vm, to_host)
                migration = VMmigration(vm, from_host, to_host)
                print "    %s" % migration
                try:
                    new_state.check_sane()
                except VMPoolStateSanityError, e:
                    print "    . new state %s not sane:" % new_state
                    print "      %s" % e
                    continue

                if new_state.unique() in self.done:
                    print "    . already done:", new_state
                    continue

                self.cache_state(new_state)

                self.check_migration(migration, current_state, new_state)

                new = new_state.unique()
                if new not in self.done and new not in self.todo:
                    self.todo.insert(new, self.distances[new_state.unique()])
        
    def check_migration(self, migration, current_state, new_state):
        """Check whether we've found a quicker way of getting from the
        initial state to new_state.
        """
        new = new_state.unique()
        current = current_state.unique()
        cost = migration.cost()
        alt = self.distances[current] + cost
        if new not in self.distances or \
           alt < self.distances[new]:
            print "    + new shortest path cost %d (total %d)" % (cost, alt)
            print "    +     to %s" % new
            self.distances[new] = alt
            self.previous[new] = current
            self.route[new] = migration
            return

        if alt == self.distances[new]:
            print "    = equally optimal path cost %d (total: %d)" % (cost, alt)
            print "    =     to %s" % new
        else:
            print "    - suboptimal path cost %d (total: %d)" % (cost, alt)
            print "    -     to %s" % new

    def trace_path(self):
        # Trace path backwards from end to start
        migration_sequence = [ ]

        print "route", repr(self.route)
        print "end", repr(self.end)

        cur = self.end
        while True:
            migration = self.route.get(cur, None)
            cur = self.previous.get(cur, None)
            if cur is None:
                break
            migration_sequence.insert(0, migration)

        return migration_sequence
    
