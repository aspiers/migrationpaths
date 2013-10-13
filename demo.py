#!/usr/bin/python

import unittest
import sys
import random
import time
import traceback

import testcases
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

STRATEGY = VMPoolAdamPathFinder

clear = True
sleep = 0.2
start_sleep = 1.0
end_sleep = 2.0

if len(sys.argv) >= 2:
    sleep = float(sys.argv[1])
if len(sys.argv) >= 3:
    clear = False if sys.argv[2] == 'false' else True
if len(sys.argv) >= 4:
    start_sleep = float(sys.argv[3])
if len(sys.argv) >= 5:
    end_sleep = float(sys.argv[4])

while True:
    #min_vm_ram = random.randint(128, 512)
    max_vm_ram = random.randint(1024, 4096)
    stateA, stateB, expected_path = \
        testcases.random.identical_hosts(num_hosts=5) #, max_vm_ram=max_vm_ram)

    path_finder = STRATEGY(stateA, stateB)
    try:
        path = path_finder.find_path()
    except RuntimeError, exc:
        continue # nothing to see here, move along

    if path:
        path.animate(clear, sleep, start_sleep, end_sleep)
    else:
        print path_finder.challenge_visualization(10, 80)
        print "\nNo path found to animate!"
        time.sleep(10)
