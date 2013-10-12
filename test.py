#!/usr/bin/python

import re
import unittest
import textwrap

from vm import VM
from vmhost import VMhost
from vmpoolstate import VMPoolState
import testcases.fixed
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

    def run_test(self, stateA, stateB, expected_path):
        expected_path = textwrap.dedent(expected_path)

        sA = VMPoolState().init_by_vmhosts(stateA)
        sB = VMPoolState().init_by_vmhosts(stateB)

        path_finder = STRATEGY(sA, sB)
        path = path_finder.find_path()

        if path is None:
            if expected_path is None:
                self.assertTrue(True, "found no path as expected")
            else:
                self.fail("failed to find path\n%s" % path_finder.get_debug())
        elif path == expected_path:
            self.assertTrue(True, "found expected path, cost %d" % path.cost)
        else:
            self.assertMultiLineEqual(path.dump(), expected_path,
                                      path_finder.get_debug())

for attr in dir(testcases.fixed):
    m = re.match('^case_(.+)', attr)
    if not m:
        continue
    case_name = m.group(1)
    test_name = 'test_' + case_name
    method = getattr(testcases.fixed, attr)
    def test_runner(self, method2=method):
        return self.run_test(*method2())
    setattr(TestPathDiscovery, test_name, test_runner)

unittest.main()
