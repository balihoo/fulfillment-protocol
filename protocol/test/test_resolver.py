#!/usr/bin/python

import json
import pprint
import unittest
from resolver import Resolver, ResolverContainer


class TestResolver(unittest.TestCase):

    def setUp(self):
        pass

    def test_Contains(self):
        r = Resolver("stuff")
        self.assertTrue(r.contains_code("<(hello"))

    def test_Basic(self):
        r = Resolver("stuff")

        self.assertTrue(r.evaluated)

    def test_ExecSimple(self):
        r = Resolver("<(return [1, 2, 3]")

        self.assertFalse(r.evaluated)
        r.evaluate()
        self.assertEqual(r.result, [1, 2, 3])

    def test_ExecCompound(self):
        r = Resolver({"one two three": "<(return [1, 2, 3]"})

        self.assertFalse(r.evaluated)
        r.evaluate()
        self.assertEqual(r.result, {"one two three": [1, 2, 3]})

    def test_ResolverContainer(self):
        r = ResolverContainer()
        r.add("stuff", "yes")

        self.assertEqual(r.stuff, "yes")
        self.assertEqual(r["stuff"], "yes")

        r.add("things", "<( 'wo' + 'rm'")

        self.assertEqual(r.things, "worm")
        self.assertEqual(r["things"], "worm")

        r.add("whaaa", "steel", transform=lambda x: x+"y")

        self.assertEqual(r.whaaa, "steely")
        self.assertEqual(r["whaaa"], "steely")

        r.add("whaaa_eval", "<( { 'a' : 'steel', 'b' : 'hammock' }['a']", transform=lambda x: x+"y")

        self.assertEqual(r.whaaa_eval, "steely")
        self.assertEqual(r["whaaa_eval"], "steely")

        self.assertTrue("stuff" in r)
        self.assertTrue("whaaa_eval" in r)
        self.assertFalse("pickle" in r)

if __name__ == '__main__':
    unittest.main()
