#!/usr/bin/python

# We need binary insertion into an ordered list
from bisect import insort_right, bisect_right

import unittest

class ValueOrderedDictionary(dict):

# not supporting initialisation with data yet
#    def __init__(self, *args, **kwargs):
#        super(ValueOrderedDictionary, self).__init__(*args, **kwargs)
#        dict.__init__(self, *args, **kwargs)

    def __init__(self):
        dict.__init__(self)
        self.ordered_keys = [ ]
        self.ordered_values = [ ]

    def __setitem__(self, new_key, new_val):
        if new_key in self:
            del self[new_key]
        self.insert(new_key, new_val)

    def insert(self, new_key, new_val):
        if new_key in self.ordered_keys:
            raise ValueError, "key %s already in todo list" % new_key
        # N.B. bisect_right is required to ensure FIFO behaviour,
        # otherwise the optimising effects of preferentially examining
        # some neighbours before their peers are lost if the edges in
        # question have the same cost.
        insert_at = bisect_right(self.ordered_values, new_val)
        self.ordered_keys.insert(insert_at, new_key)
        self.ordered_values.insert(insert_at, new_val)
        dict.__setitem__(self, new_key, new_val)

    def __delitem__(self, key):
        if key not in self:
            raise KeyError, key
        # FIXME: this is O(n) not constant
        val = self[key]

        # values aren't unique and remove() removes the first
        # occurrence, but self.ordered_values is sorted so the alignment with
        # self.ordered_keys is preserved.
        self.ordered_values.remove(val)

        self.ordered_keys.remove(key) # keys are unique
        dict.__delitem__(self, key)

    def iterkeys(self):
        return iter(self.ordered_keys)

    def itervalues(self):
        return iter(self.ordered_values)
        
    __iter__ = iterkeys

    def iteritems(self):
        def generator(self = self):
            keys = self.iterkeys()
            while True:
                key = keys.next()
                yield (key, self[key])
        return generator()

    def shift(self):
        k = self.ordered_keys[0]
        v = self.ordered_values[0]
        del self[k]
        return k, v

    def keys(self):
        return self.ordered_keys

    def values(self):
        return self.ordered_values

    def show(self):
        print "dict:", self
        print "keys:", self.keys()
        print "vals:", self.values()

class ValueOrderedDictionaryTestCase(unittest.TestCase):
    def testAll(self):
        # test initialisation
        #vod = ValueOrderedDictionary([('d', 3), ('e', 2)])
        vod = ValueOrderedDictionary()
        assert isinstance(vod, ValueOrderedDictionary), 'class'
        assert len(vod) == 0, 'length'

        try:
            vod2 = ValueOrderedDictionary([('d', 3), ('e', 2)])
        except TypeError:
            pass
        else:
            self.fail("should have raised TypeError, init with args not supported yet")

        # test ordering
        vod.insert('5th', 9)
        vod.insert('3rd', 5)
        vod.insert('1st', 3)
        vod.insert('2nd', 3)
        vod.insert('4th', 7)

        self.check_ordering(vod, 
                            [ '1st', '2nd', '3rd', '4th', '5th' ],
                            [ 3, 3, 5, 7, 9 ])

        # test shift
        top = vod.shift()
        self.assertEqual(top, ('1st', 3))
        self.check_ordering(vod, 
                            [ '2nd', '3rd', '4th', '5th' ],
                            [ 3, 5, 7, 9 ])

        # test membership and addition
        assert 'new' not in vod
        vod['new'] = 8
        assert 'new' in vod, 'new'
        self.assertEqual(vod['new'], 8, 'assignment')

        self.check_ordering(vod, 
                            [ '2nd', '3rd', '4th', 'new', '5th' ],
                            [ 3, 5, 7, 8, 9 ])

        # test duplicate detection
        try:
            vod.insert('new', 18)
        except ValueError:
            pass
        else:
            self.fail("expected a ValueError since new already there")

        # test no corruption by attempted duplicate
        self.assertEqual(vod['new'], 8, 'assignment')
        self.check_ordering(vod, 
                            [ '2nd', '3rd', '4th', 'new', '5th' ],
                            [ 3, 5, 7, 8, 9 ])

        # test shift again
        top2 = vod.shift()
        self.assertEqual(top2, ('2nd', 3))

        self.check_ordering(vod, 
                            [ '3rd', '4th', 'new', '5th' ],
                            [ 5, 7, 8, 9 ])

        # test reordering by changing value
        vod['4th'] = 14

        self.check_ordering(vod, 
                            [ '3rd', 'new', '5th', '4th' ],
                            [ 5, 8, 9, 14 ])

    def check_ordering(self, vod, okeys, ovals):
        self.assertEqual(vod.keys(), okeys)
        self.assertEqual([x for x in vod.iterkeys()], okeys)

        self.assertEqual(vod.values(), ovals)
        self.assertEqual([x for x in vod.itervalues()], ovals)

        self.assertEqual([x for x in vod.iteritems()],
                         zip(okeys, ovals))

if __name__ == '__main__':
    unittest.main()
