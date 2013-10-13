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

stateA, stateB, expected_path = testcases.fixed.case_max_recursion_depth()
stateA = VMPoolState().init_by_vmhosts(stateA)
stateB = VMPoolState().init_by_vmhosts(stateB)

current_state = stateA

path_finder = STRATEGY(current_state, stateB)
print path_finder.path.challenge_visualization(10, 80)

while True:
    command = raw_input("Enter command > ")
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

