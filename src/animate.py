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

if len(sys.argv) >= 2 and sys.argv[1] == 'random':
    stateA, stateB, expected_path = testcases.random.identical_hosts()
else:
    testcase = 'chain6'
    if len(sys.argv) == 2:
        testcase = sys.argv[1]
    testcase = getattr(testcases.fixed, "case_%s" % testcase)
    stateA, stateB, expected_path = testcase()
    stateA = VMPoolState().init_by_vmhosts(stateA)
    stateB = VMPoolState().init_by_vmhosts(stateB)

path_finder = STRATEGY(stateA, stateB)
try:
    path = path_finder.find_path()
except RuntimeError, exc:
    print path_finder.get_debug()
    traceback.print_exc(exc)
    sys.exit(1)

if path:
    path.animate(True)
else:
    print "\nNo path found to animate."
