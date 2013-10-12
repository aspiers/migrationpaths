#!/usr/bin/python

from vm import VM
from vmhost import VMhost

def case_simple_swap():
    host1 = VMhost('host1', 'x86_64', 4096)
    host2 = VMhost('host2', 'x86_64', 4096)
    vm1 = VM('vm1', 'x86_64', 256)
    vm2 = VM('vm2', 'x86_64', 256)
    stateA = {
        'host1' : [ vm1 ],
        'host2' : [ vm2 ],
        }
    stateB = {
        'host1' : [ vm2 ],
        'host2' : [ vm1 ],
        }
    expected_path = """\
        shutdown: 
        ! vm1@256: host1@4096 -> host2@4096  cost 256
        ! vm2@256: host2@4096 -> host1@4096  cost 256
        provision: 
    """
    return (stateA, stateB, expected_path)

def case_simple_cessation():
    host1 = VMhost('host1', 'x86_64', 4096)
    host2 = VMhost('host2', 'x86_64', 4096)
    host3 = VMhost('host3', 'x86_64', 4096)
    vm1 = VM('vm1', 'x86_64', 3256)
    vm2 = VM('vm2', 'x86_64', 3256)
    stateA = {
        'host1' : [ vm1 ],
        'host2' : [ vm2 ],
        }
    stateB = {
        'host1' : [ vm2 ],
        'host3' : [ vm1 ],
        }
    expected_path = """\
        shutdown: 
        ! vm1@3256: host1@4096 -> host3@4096  cost 3256
        ! vm2@3256: host2@4096 -> host1@4096  cost 3256
        provision: 
    """
    return (stateA, stateB, expected_path)

def case_swap_with_one_temp():
    host1 = VMhost('host1', 'x86_64', 4096)
    host2 = VMhost('host2', 'x86_64', 4096)
    host3 = VMhost('host3', 'x86_64', 4096)
    vm1 = VM('vm1', 'x86_64', 3256)
    vm2 = VM('vm2', 'x86_64', 3256)
    stateA = {
        'host1' : [ vm1 ],
        'host2' : [ vm2 ],
        'host3' : [ ],
        }
    stateB = {
        'host1' : [ vm2 ],
        'host2' : [ vm1 ],
        'host3' : [ ],
        }
    expected_path = """\
        shutdown: 
        ! vm2@3256: host2@4096 -> host3@4096  cost 3256
        ! vm1@3256: host1@4096 -> host2@4096  cost 3256
        ! vm2@3256: host3@4096 -> host1@4096  cost 3256
        provision: 
    """
    return (stateA, stateB, expected_path)

def case_complex_swap():
    host1 = VMhost('host1', 'x86_64', 4096, 280)
    host2 = VMhost('host2', 'x86_64', 4096, 280)
    host3 = VMhost('host3', 'x86_64', 4096, 280)
    vm1 = VM('vm1', 'x86_64', 300)
    vm2 = VM('vm2', 'x86_64', 3000)
    vm3 = VM('vm3', 'x86_64', 3700)
    stateA = {
        'host1' : [ vm1 ],
        'host2' : [ vm2 ],
        'host3' : [ vm3 ],
        }
    stateB = {
        'host1' : [ vm1 ],
        'host2' : [ vm3 ],
        'host3' : [ vm2 ],
        }
    expected_path = """\
        shutdown: 
        ! vm1@256: host1@4096 -> host2@4096  cost 256
        ! vm2@256: host2@4096 -> host1@4096  cost 256
        provision: 
    """
    return (stateA, stateB, expected_path)

def case_shutdown_and_swap():
    host1 = VMhost('host1', 'x86_64', 4096)
    host2 = VMhost('host2', 'x86_64', 3048)
    host3 = VMhost('host3', 'i386'  , 4096)
    host4 = VMhost('host4', 'i386'  , 2448)

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
        'host1' : [ vm1, vm2 ],
        'host2' : [ vm3, vm4, vm9 ],
        'host3' : [ vm7, vm8 ],
        'host4' : [ vm5, vm6 ]
        }
    # swap vm5 and vm9
    stateB = {
        'host1' : [ vm1 ],
        'host2' : [ vm3, vm4, vm5 ],
        'host3' : [ ],
        'host4' : [ vm9 ]
        }

    expected_path = """\
        shutdown: vm2, vm6, vm7, vm8
        ! vm9@256: host2@3048 -> host4@2448  cost 256
        ! vm5@1024: host4@2448 -> host2@3048  cost 1024
        provision: 
    """
    return (stateA, stateB, expected_path)

def case_tricky():
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

    expected_path = """\
        shutdown: vm6
        ! vm4@900: host2@2256 -> host3@2256  cost 900
        ! vm3@900: host1@2256 -> host2@2256  cost 900
        ! vm2@1000: host2@2256 -> host1@2256  cost 1000
        ! vm4@900: host3@2256 -> host2@2256  cost 900
        ! vm5@150: host3@2256 -> host2@2256  cost 150
        provision: 
    """
    return (stateA, stateB, expected_path)

def case_chain4():
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
    small1 = VM('small1', 'x86_64', 370)
    small2 = VM('small2', 'x86_64', 380)
    small3 = VM('small3', 'x86_64', 390)
    small4 = VM('small4', 'x86_64', 400)
    tiny1  = VM('tiny1', 'x86_64', 100)
    tiny2  = VM('tiny2', 'x86_64', 100)
    tiny3  = VM('tiny3', 'x86_64', 100)
    tiny4  = VM('tiny4', 'x86_64', 100)

    stateA = {
        'host1' : [ big1, small1 ],
        'host2' : [ big2, small2 ],
        'host3' : [ big3, small3 ],
        'host4' : [ big4, small4 ],
        'hostX' : [ tiny1, tiny2, tiny3, tiny4 ],
        }
    stateB = {
        'host1' : [ big1, small4, tiny1 ],
        'host2' : [ big2, small3, tiny2 ],
        'host3' : [ big3, small2, tiny3 ],
        'host4' : [ big4, small1, tiny4 ],
        'hostX' : [ ],
        }

    expected_path = """\
        shutdown: 
        ! big1@500: host1@1256 -> hostX@1256  cost 500
        ! small4@400: host4@1256 -> host1@1256  cost 400
        ! small1@370: host1@1256 -> host4@1256  cost 370
        ! big1@500: hostX@1256 -> host1@1256  cost 500
        ! big2@510: host2@1256 -> hostX@1256  cost 510
        ! small3@390: host3@1256 -> host2@1256  cost 390
        ! small2@380: host2@1256 -> host3@1256  cost 380
        ! big2@510: hostX@1256 -> host2@1256  cost 510
        ! tiny1@100: hostX@1256 -> host1@1256  cost 100
        ! tiny2@100: hostX@1256 -> host2@1256  cost 100
        ! tiny3@100: hostX@1256 -> host3@1256  cost 100
        ! tiny4@100: hostX@1256 -> host4@1256  cost 100
        provision: 
    """
    return (stateA, stateB, expected_path)

def case_chain6():
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

    expected_path = """\
        shutdown: big6, small1
        ! big2@510: host2@1256 -> host6@1256  cost 510
        ! small5@390: host5@1256 -> host2@1256  cost 390
        ! small2@360: host2@1256 -> host5@1256  cost 360
        ! big2@510: host6@1256 -> host2@1256  cost 510
        ! big3@520: host3@1256 -> host6@1256  cost 520
        ! small4@380: host4@1256 -> host3@1256  cost 380
        ! small3@370: host3@1256 -> host4@1256  cost 370
        ! big3@520: host6@1256 -> host3@1256  cost 520
        ! small6@400: host6@1256 -> host1@1256  cost 400
        ! tiny1@100: hostX@1256 -> host1@1256  cost 100
        ! tiny2@100: hostX@1256 -> host2@1256  cost 100
        ! tiny3@100: hostX@1256 -> host3@1256  cost 100
        ! tiny4@100: hostX@1256 -> host4@1256  cost 100
        provision: tiny5
    """
    return (stateA, stateB, expected_path)
