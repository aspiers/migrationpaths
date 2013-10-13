#!/usr/bin/python

import unittest
import sys
import traceback

import testcases
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

#STRATEGY = VMPoolShortestPathFinder
STRATEGY = VMPoolAdamPathFinder

while True:
    stateA, stateB, expected_path = testcases.random.identical_hosts(3, 5)

    path_finder = STRATEGY(stateA, stateB)
    try:
        path = path_finder.find_path()
        if path is not None:
            path.walk()
    except RuntimeError, exc:
        print path_finder.get_debug()
        traceback.print_exc(exc)
        sys.exit(1)

    if path:
        print path.summary()
    else:
        #print path_finder.path.challenge_visualization(10, 80)
        print "No path found!"

    if path_finder.time_elapsed() > 1.0 and path is None:
        print path_finder.path.challenge_visualization(10, 80)
        print path_finder.get_debug()
        print path_finder.path.challenge_visualization(10, 80)
        print path.summary()
        print path.dump()
        print "Took too long; aborting."
        sys.exit(1)
