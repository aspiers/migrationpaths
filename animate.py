#!/usr/bin/python

import unittest

from vm import VM
from vmhost import VMhost
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

#STRATEGY = VMPoolShortestPathFinder
STRATEGY = VMPoolAdamPathFinder

# N.B. 256MB required for dom0 (hardcoded).
# For the sake of easy maths in the example
# we create 2000MB available for domUs.
host1 = VMhost('host1', 'x86_64', 2256)
host2 = VMhost('host2', 'x86_64', 2256)
host3 = VMhost('host3', 'i386',   2256)

vm1 = VM('vm1', 'x86_64', 1000)
vm2 = VM('vm2', 'x86_64', 1000)
vm3 = VM('vm3', 'x86_64',  900)
vm4 = VM('vm4', 'i386'  ,  900)
vm5 = VM('vm5', 'i386'  ,  150)
vm6 = VM('vm6', 'i386'  ,  150)

stateA = {
    'host1' : [ vm1, vm3 ],
    'host2' : [ vm2, vm4 ],
    'host3' : [ vm5, vm6 ],
    }
stateB = {
    'host1' : [ vm1, vm2 ],
    'host2' : [ vm3, vm4, vm5 ],
    'host3' : [ ],
    }

sA = VMPoolState().init_by_vmhosts(stateA)
sB = VMPoolState().init_by_vmhosts(stateB)

path_finder = STRATEGY(sA, sB)
path = path_finder.find_path()
path.animate(True)
