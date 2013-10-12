#!/usr/bin/python

import unittest
import sys
import time
import traceback

import testcases
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

STRATEGY = VMPoolAdamPathFinder

while True:
    stateA, stateB, expected_path = testcases.random.identical_hosts()

    path_finder = STRATEGY(stateA, stateB)
    try:
        path = path_finder.find_path()
    except RuntimeError, exc:
        continue # nothing to see here, move along

    if path:
        path.animate(True, 0.2)
    else:
        print path_finder.challenge_visualization(10, 80)
        print "\nNo path found to animate!"
        time.sleep(10)
