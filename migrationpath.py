#!/usr/bin/python

from vodict import ValueOrderedDictionary 
from vmpoolstateerrors import VMPoolStateSanityError
from vmmigration import VMmigration

class VMPoolShortestPathFinder:
    """This class enables storage of the state data used during the
    discovery of the shortest path inside an instance.  This makes the
    code thread-safe, allowing discovery of multiple shortest paths in
    parallel (one instance of this class for each).  It also makes the
    code a bit cleaner (albeit slightly more complex) through not
    having to pass several state variables around.

    N.B. Instances should not be reused for multiple runs."""

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

    def __init__(self, initial_state):
        self.initial_state = initial_state
        initial_cost = 0

        # Nodes which still need to be explored, sorted by distance ascending.
        self.todo = ValueOrderedDictionary()
        self.todo[initial_state.unique()] = initial_cost

        # Nodes which have already been fully explored.
        self.done = { }

        # Distances for all nodes (both todo and done)
        self.distances = { initial_state.unique() : initial_cost }

        # Penultimate node in shortest path to given node
        self.previous = { }

        # How to get from penultimate node to given node, as a
        # (vm, to_host, cost) tuple
        self.route = { }

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

        # Did we find a shortest path yet?
        self.found = False

    def cache_state(self, state):
        if state.unique() not in self.cache:
            self.cache[state.unique()] = state

    def shortest_path_to(self, final_state):
        if hasattr(self, 'path'):
            raise RuntimeError, \
                  "cannot reuse VMPoolShortestPathFinder instance"

        self.check_endpoint_vms(final_state)
        self.power_off()

        self.final_state = final_state
        self.final = final_state.unique()
        while len(self.todo) > 0:
            print "todo list:"
            for s in self.todo:
                print "  %2d: %s" % (self.distances[s], s)
            current, dist = self.todo.shift()
            if current == self.final:
                self.found = True
                break
            current_state = self.cache[current]
            print "current_state:", current_state
            self.explore_neighbours(current_state)

            print "    < marking as done:", current_state
            self.done[current] = True

        if self.found:
            # This method is wrapped by VMPoolState.shortest_path_to
            return self.trace_path()
        else:
            return None

    def check_endpoint_vms(self, final_state):
        self.vms_to_power_off = { }
        self.vms_to_move = { }
        self.vms_to_provision = { }
        for start_vm in self.initial_state.vms():
            if start_vm not in final_state.vms():
                self.vms_to_power_off[start_vm] = True
            else:
                from_host = self.initial_state.vm2vmhost[start_vm]
                to_host   = final_state.vm2vmhost[start_vm]
                if from_host != to_host:
                    self.vms_to_move[start_vm] = True
        for end_vm in final_state.vms():
            if end_vm not in self.initial_state.vms():
                self.vms_to_provision[end_vm] = True
        if len(self.vms_to_provision) > 0:
            raise "Need to provision %s but provisioning not supported yet" \
                  % self.vms_to_provision.keys()
        print "VMs requiring power off:", \
              ' '.join(self.vms_to_power_off.keys())
        print "VMs definitely requiring a move:", \
              ' '.join(self.vms_to_move.keys())

    def power_off(self):
        if len(self.vms_to_power_off) > 0:
            for vm in self.vms_to_power_off:
                print "Powering off VM %s" % vm
                self.initial_state.remove_vm(vm)
            # Reinitialize
            self.__init__(self.initial_state)
        
    def explore_neighbours(self, current_state):
        """Explore all neighbours from current state."""
        
        # Assuming we're given the end state in advance, optimise the
        # search order by prioritising exploration of neighbours
        # resulting from migrating VMs which need to be migrated, over
        # exploration of those resulting from VMs which do not.
        moved_vms = [ ]
        unmoved_vms = [ ]
        for vm in current_state.vms():
            if vm in self.vms_to_move:
                moved_vms.append(vm)
            else:
                unmoved_vms.append(vm)

        for vm in moved_vms + unmoved_vms:
            from_host = current_state.vm2vmhost[vm]
            print "  examining %s, currently on %s" % (vm, from_host)

            for to_host in current_state.vmhost2vms:
                if from_host == to_host:
                    continue

                migration = VMmigration(vm, from_host, to_host)
                print "    %s" % migration
                cost = migration.cost()
                new_state = current_state.migrate(vm, to_host)
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

                self.check_edge(current_state, new_state, vm, to_host, cost)

                new = new_state.unique()
                if new not in self.done and new not in self.todo:
                    self.todo.insert(new, self.distances[new_state.unique()])
        
    def check_edge(self, current_state, new_state, vm, to_host, cost):
        """Check whether we've found a quicker way of getting from the
        initial state to new_state."""
        new = new_state.unique()
        current = current_state.unique()
        alt = self.distances[current] + cost
        if new not in self.distances or \
           alt < self.distances[new]:
            print "    + new shortest path cost %d (total %d)" % (cost, alt)
            print "    +     to %s" % new
            self.distances[new] = alt
            self.previous[new] = current
            self.route[new] = (vm, to_host, cost)
            return

        if alt == self.distances[new]:
            print "    = equally optimal path cost %d (total: %d)" % (cost, alt)
            print "    =     to %s" % new
        else:
            print "    - suboptimal path cost %d (total: %d)" % (cost, alt)
            print "    -     to %s" % new

    def trace_path(self):
        # Trace path backwards from end to start
        self.path = [ ]
        cur = self.final
        while True:
            self.path.insert(0, cur)
            cur = self.previous.get(cur, None)
            if cur == None:
                break
        return self.path
    
    def report(self):
        if not self.found:
            print "didn't find a shortest path"
            return

        print "Short path found with cost %d:" % self.distances[self.final]
        print "Start: ", self.path[0]
        for state in self.path[1:]:
            prev = self.previous[state]
            from_state = self.cache[prev]
            (vm, to_host, cost) = self.route[state]
            from_host = from_state.vm2vmhost[vm]
            print "%s: %s -> %s  cost %d" % (vm, from_host, to_host, cost)
        print "End:   ", self.path[-1]
        print "todo list size:", len(self.todo)
        print "done list size:", len(self.done)

