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

stateA, stateB, expected_path = testcases.fixed.case_max_recursion_depth()
stateA = VMPoolState().init_by_vmhosts(stateA)
stateB = VMPoolState().init_by_vmhosts(stateB)

path_finder = STRATEGY(stateA, stateB)
path_finder.immediate_debugging = True

try:
    path = path_finder.find_path()
except RuntimeError, exc:
    traceback.print_exc(exc)
    sys.exit(1)

if path:
    print "-" * 70
    print "Solution:\n\n", path.dump()
    #path.animate(True)
else:
    print "\nNo path found to animate."
