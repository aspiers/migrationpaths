#!/usr/bin/python

import unittest

import testcases
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

#STRATEGY = VMPoolShortestPathFinder
STRATEGY = VMPoolAdamPathFinder

stateA, stateB, expected_path = testcases.case_chain6()
sA = VMPoolState().init_by_vmhosts(stateA)
sB = VMPoolState().init_by_vmhosts(stateB)

path_finder = STRATEGY(sA, sB)
path = path_finder.find_path()

if path:
    path.animate(True)
else:
    print "\nNo path found to animate."
