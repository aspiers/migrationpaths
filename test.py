#!/usr/bin/python

import unittest
import textwrap

from vm import VM
from vmhost import VMhost
from vmpoolstate import VMPoolState
from dijkstra import VMPoolShortestPathFinder
from aspiers import VMPoolAdamPathFinder

#STRATEGY = VMPoolShortestPathFinder
STRATEGY = VMPoolAdamPathFinder

class TestPathDiscovery(unittest.TestCase):
    longMessage = True
    maxDiff = None

    def setUp(self):
        VM.reset()
        VMhost.reset()

    def test_simple_swap(self):
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
        expected_path = """\
            shutdown: 
            ! vm1@256: demo1@4096 -> demo2@4096  cost 256
            ! vm2@256: demo2@4096 -> demo1@4096  cost 256
            provision: 
        """
        return self.run_test(stateA, stateB, expected_path)

    def test_simple_cessation(self):
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
        expected_path = """\
            shutdown: 
            ! vm1@3256: demo1@4096 -> demo3@4096  cost 3256
            ! vm2@3256: demo2@4096 -> demo1@4096  cost 3256
            provision: 
        """
        return self.run_test(stateA, stateB, expected_path)

    def test_swap_with_one_temp(self):
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
        expected_path = """\
            shutdown: 
            ! vm2@3256: demo2@4096 -> demo3@4096  cost 3256
            ! vm1@3256: demo1@4096 -> demo2@4096  cost 3256
            ! vm2@3256: demo3@4096 -> demo1@4096  cost 3256
            provision: 
        """
        return self.run_test(stateA, stateB, expected_path)

    def test_shutdown_and_swap(self):
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
        # swap vm5 and vm9
        stateB = {
            'demo1' : [ vm1 ],
            'demo2' : [ vm3, vm4, vm5 ],
            'demo3' : [ ],
            'demo4' : [ vm9 ]
            }

        expected_path = """\
            shutdown: vm2, vm6, vm7, vm8
            ! vm9@256: demo2@3048 -> demo4@2448  cost 256
            ! vm5@1024: demo4@2448 -> demo2@3048  cost 1024
            provision: 
        """

        return self.run_test(stateA, stateB, expected_path)

    def test_tricky(self):
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

        return self.run_test(stateA, stateB, expected_path)

    def test_chain6(self):
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
        return self.run_test(stateA, stateB, expected_path)

    def test_chain4(self):
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

        return self.run_test(stateA, stateB, expected_path)

    def run_test(self, stateA, stateB, expected_path):
        expected_path = textwrap.dedent(expected_path)

        sA = VMPoolState().init_by_vmhosts(stateA)
        sB = VMPoolState().init_by_vmhosts(stateB)

        path_finder = STRATEGY(sA, sB)
        path = path_finder.find_path()

        if path is None and expected_path is None:
            assertTrue(True, "%s found no path as expected" % test.__name__)
        elif path == expected_path:
            self.assertTrue(True, "%s found expected path, cost %d" % \
                (test.__name__, path.cost))
        else:
            self.assertMultiLineEqual(path.dump(), expected_path,
                                      path_finder.get_debug())

unittest.main()
