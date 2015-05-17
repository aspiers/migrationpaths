#!/usr/bin/python

import unittest
import sys
import traceback

import testcases
from vm import VM
from vmhost import VMhost
from vmpoolstate import VMPoolState
from vmpoolstateerrors import VMPoolStateSanityError
from aspiers import VMPoolAdamPathFinder

#STRATEGY = VMPoolShortestPathFinder
STRATEGY = VMPoolAdamPathFinder

testcase = 'simple_swap'
if len(sys.argv) == 2:
    testcase = sys.argv[1]
testcase = getattr(testcases.fixed, "case_%s" % testcase)

stateA, stateB, expected_path = testcase()
stateA = VMPoolState().init_by_vmhosts(stateA)
stateB = VMPoolState().init_by_vmhosts(stateB)

current_state = stateA

path_finder = STRATEGY(current_state, stateB)
print path_finder.path.challenge_visualization(10, 80)

first = True

while True:
    if first:
        msg = "Enter migration " \
              "(VM name and destination host separated by a space) > "
        first = False
    else:
        msg = "Enter migration > "
    command = raw_input(msg)
    vm_name, to_host_name = command.split()
    to_host = VMhost.vmhosts[to_host_name]
    try:
        current_state = \
            current_state.check_migration_sane(vm_name, to_host)
    except VMPoolStateSanityError, exc:
        print exc
        print

    path_finder = STRATEGY(current_state, stateB)
    print path_finder.path.challenge_visualization(10, 80)

