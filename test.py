#!/usr/bin/python

from vm import VM
from vmhost import VMhost
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

#STRATEGY = VMPoolShortestPathFinder
STRATEGY = VMPoolAdamPathFinder

def find_path(stateA, stateB):
    sA = VMPoolState().init_by_vmhosts(stateA)
    sB = VMPoolState().init_by_vmhosts(stateB)
    path = sA.path_to(sB, STRATEGY)
    # FIXME: allow unit test assertions
    if not path:
        print "didn't find a shortest path"
        return
    path.report()

def simple_swap():
    demo1 = VMhost('demo1', 'x86_64', 4096)
    demo2 = VMhost('demo2', 'x86_64', 4096)
    vm1 = VM('vm1', 'x86_64', 256)
    vm2 = VM('vm2', 'x86_64', 256)
    stateA = {
        'demo1' : [ vm1 ],
        'demo2' : [ vm2 ],
        }
    stateB = {
        'demo1' : [ vm2 ],
        'demo2' : [ vm1 ],
        }
    return find_path(stateA, stateB)

def simple_cessation():
    demo1 = VMhost('demo1', 'x86_64', 4096)
    demo2 = VMhost('demo2', 'x86_64', 4096)
    demo3 = VMhost('demo3', 'x86_64', 4096)
    vm1 = VM('vm1', 'x86_64', 3256)
    vm2 = VM('vm2', 'x86_64', 3256)
    stateA = {
        'demo1' : [ vm1 ],
        'demo2' : [ vm2 ],
        }
    stateB = {
        'demo1' : [ vm2 ],
        'demo3' : [ vm1 ],
        }
    return find_path(stateA, stateB)

def swap_with_one_temp():
    demo1 = VMhost('demo1', 'x86_64', 4096)
    demo2 = VMhost('demo2', 'x86_64', 4096)
    demo3 = VMhost('demo3', 'x86_64', 4096)
    vm1 = VM('vm1', 'x86_64', 3256)
    vm2 = VM('vm2', 'x86_64', 3256)
    stateA = {
        'demo1' : [ vm1 ],
        'demo2' : [ vm2 ],
        'demo3' : [ ],
        }
    stateB = {
        'demo1' : [ vm2 ],
        'demo2' : [ vm1 ],
        'demo3' : [ ],
        }
    return find_path(stateA, stateB)

def tricky1():
    demo1 = VMhost('demo1', 'x86_64', 4096)
    demo2 = VMhost('demo2', 'x86_64', 3048)
    demo3 = VMhost('demo3', 'i386'  , 4096)
    demo4 = VMhost('demo4', 'i386'  , 2448)

    vm1 = VM('vm1', 'x86_64', 2048)
    vm2 = VM('vm2', 'x86_64', 1024)
    vm3 = VM('vm3', 'x86_64', 1024)
    vm4 = VM('vm4', 'x86_64',  512)
    vm5 = VM('vm5', 'i386',   1024)
    vm6 = VM('vm6', 'i386',   1024)
    vm7 = VM('vm7', 'i386',    768)
    vm8 = VM('vm8', 'i386',    512)
    vm9 = VM('vm9', 'i386',    256)

    stateA = {
        'demo1' : [ vm1, vm2 ],
        'demo2' : [ vm3, vm4, vm9 ],
        'demo3' : [ vm7, vm8 ],
        'demo4' : [ vm5, vm6 ]
        }
    stateB = {
        'demo1' : [ vm1 ],
        'demo2' : [ vm3, vm4, vm5 ],
        'demo3' : [ ],
        'demo4' : [ vm9 ]
        }

    return find_path(stateA, stateB)

def tricky():
    # N.B. 256MB required for dom0 (hardcoded).
    # For the sake of easy maths in the example
    # we create 2000MB available for domUs.
    host1 = VMhost('host1', 'x86_64', 2256)
    host2 = VMhost('host2', 'x86_64', 2256)
    host3 = VMhost('host3', 'i386',   2256)

    vm1 = VM('vm1', 'x86_64', 1000)
    vm2 = VM('vm2', 'x86_64', 1000)
#    vm3 = VM('vm3', 'i386',    900)
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

    return find_path(stateA, stateB)

def chain6():
    # N.B. 256MB required for dom0 (hardcoded).
    # For the sake of easy maths in the example
    # we create 1000MB available for domUs.
    host1 = VMhost('host1', 'x86_64', 1256)
    host2 = VMhost('host2', 'x86_64', 1256)
    host3 = VMhost('host3', 'x86_64', 1256)
    host4 = VMhost('host4', 'x86_64', 1256)
    host5 = VMhost('host5', 'x86_64', 1256)
    host6 = VMhost('host6', 'x86_64', 1256)
    hostX = VMhost('hostX', 'x86_64', 1256)

    big1   = VM('big1', 'x86_64', 500)
    big2   = VM('big2', 'x86_64', 510)
    big3   = VM('big3', 'x86_64', 520)
    big4   = VM('big4', 'x86_64', 530)
    big5   = VM('big5', 'x86_64', 540)
    big6   = VM('big6', 'x86_64', 550)
    small1 = VM('small1', 'x86_64', 350)
    small2 = VM('small2', 'x86_64', 360)
    small3 = VM('small3', 'x86_64', 370)
    small4 = VM('small4', 'x86_64', 380)
    small5 = VM('small5', 'x86_64', 390)
    small6 = VM('small6', 'x86_64', 400)
    tiny1  = VM('tiny1', 'x86_64', 100)
    tiny2  = VM('tiny2', 'x86_64', 100)
    tiny3  = VM('tiny3', 'x86_64', 100)
    tiny4  = VM('tiny4', 'x86_64', 100)
    tiny5  = VM('tiny5', 'x86_64', 100)
    tiny6  = VM('tiny6', 'x86_64', 100)

    stateA = {
        'host1' : [ big1, small1 ],
        'host2' : [ big2, small2 ],
        'host3' : [ big3, small3 ],
        'host4' : [ big4, small4 ],
        'host5' : [ big5, small5 ],
        'host6' : [ big6, small6 ],
        'hostX' : [ tiny1, tiny2, tiny3, tiny4 ],
        }
    stateB = {
        'host1' : [ big1, small6, tiny1 ],
        'host2' : [ big2, small5, tiny2 ],
        'host3' : [ big3, small4, tiny3 ],
        'host4' : [ big4, small3, tiny4 ],
        'host5' : [ big5, small2, tiny5 ],
#        'host6' : [ big6, small1, tiny6 ],
        'hostX' : [ ],
        }

    return find_path(stateA, stateB)

def chain4():
    # N.B. 256MB required for dom0 (hardcoded).
    # For the sake of easy maths in the example
    # we create 2000MB available for domUs.
    host1 = VMhost('host1', 'x86_64', 1256)
    host2 = VMhost('host2', 'x86_64', 1256)
    host3 = VMhost('host3', 'x86_64', 1256)
    host4 = VMhost('host4', 'x86_64', 1256)
    hostX = VMhost('hostX', 'x86_64', 1256)

    big1   = VM('big1', 'x86_64', 500)
    big2   = VM('big2', 'x86_64', 510)
    big3   = VM('big3', 'x86_64', 520)
    big4   = VM('big4', 'x86_64', 530)
    small3 = VM('small3', 'x86_64', 370)
    small4 = VM('small4', 'x86_64', 380)
    small5 = VM('small5', 'x86_64', 390)
    small6 = VM('small6', 'x86_64', 400)
    tiny1  = VM('tiny1', 'x86_64', 100)
    tiny2  = VM('tiny2', 'x86_64', 100)
    tiny3  = VM('tiny3', 'x86_64', 100)
    tiny4  = VM('tiny4', 'x86_64', 100)

    stateA = {
        'host1' : [ big1, small3 ],
        'host2' : [ big2, small4 ],
        'host3' : [ big3, small5 ],
        'host4' : [ big4, small6 ],
        'hostX' : [ tiny1, tiny2, tiny3, tiny4 ],
        }
    stateB = {
        'host1' : [ big1, small6, tiny1 ],
        'host2' : [ big2, small5, tiny2 ],
        'host3' : [ big3, small4, tiny3 ],
        'host4' : [ big4, small3, tiny4 ],
        'hostX' : [ ],
        }

    return find_path(stateA, stateB)

#simple_swap()
#simple_cessation()
#swap_with_one_temp()
tricky1()
#tricky()
#chain6()
#chain4()
