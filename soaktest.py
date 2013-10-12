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
    stateA, stateB, expected_path = testcases.random.identical_hosts()

    path_finder = STRATEGY(stateA, stateB)
    try:
        path = path_finder.find_path()
    except RuntimeError, exc:
        print path_finder.get_debug()
        traceback.print_exc(exc)
        sys.exit(1)

    if path:
        print path.summary()
    else:
        path_finder.show_challenge(10, 80)
        print "\nNo path found to animate!"
        sys.exit(1)
