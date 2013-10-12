#!/usr/bin/python

import unittest
import sys

import testcases
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

#STRATEGY = VMPoolShortestPathFinder
STRATEGY = VMPoolAdamPathFinder

if len(sys.argv) >= 2 and sys.argv[1] == 'random':
    stateA, stateB, expected_path = testcases.random.identical_hosts()
else:
    stateA, stateB, expected_path = testcases.fixed.case_chain6()
    stateA = VMPoolState().init_by_vmhosts(stateA)
    stateB = VMPoolState().init_by_vmhosts(stateB)

path_finder = STRATEGY(stateA, stateB)
path = path_finder.find_path()

if path:
    path.animate(True)
else:
    print "\nNo path found to animate."
