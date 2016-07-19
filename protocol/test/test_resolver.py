#!/usr/bin/python
# -*- coding: utf-8 -*-
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

    def test_ExecMultiLine(self):
        r = Resolver([
            "<(",
            "def func(things):",
            "  return s2j('[1,2,{}]'.format(things))",
            "return func('3')"
        ])

        self.assertFalse(r.evaluated)
        r.evaluate()
        self.assertEqual(r.result, [1, 2, 3])

    def test_ExecCompound(self):
        r = Resolver({"one two three": "<(return [1, 2, 3]"})

        self.assertFalse(r.evaluated)
        r.evaluate()
        self.assertEqual(r.result, {"one two three": [1, 2, 3]})

    def test_ExecError(self):
        r = Resolver({"one two three": "<(return [1, 2, 3"})

        self.assertFalse(r.evaluated)
        r.evaluate()
        self.assertEqual(r.timeline.events[0].messages, ['Unexpected Evaluation Exception! invalid syntax (<string>, line 3)'])
        self.assertEqual(r.result, None)

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

        r.add("whaaa_eval", "<( { 'a' : 'steel', 'b' : 'hammock®' }['a']", transform=lambda x: x+"y")

        self.assertEqual(r.whaaa_eval, "steely")
        self.assertEqual(r["whaaa_eval"], "steely")

        self.assertTrue("stuff" in r)
        self.assertTrue("whaaa_eval" in r)
        self.assertFalse("pickle" in r)

        self.assertEqual(r.to_json(), {'stuff': 'yes', 'things': 'worm', 'whaaa': 'steely', 'whaaa_eval': 'steely'})

        self.assertEqual(r.to_json(True), {'stuff': 'yes',
                                           'things': {'evaluated': True,
                                                      'input': "<( 'wo' + 'rm'",
                                                      'needsEvaluation': True,
                                                      'resolvable': True,
                                                      'resolved': True,
                                                      'result': 'worm',
                                                      'timeline': []},
                                           'whaaa': 'steely',
                                           'whaaa_eval': {'evaluated': True,
                                                          'input': "<( { 'a' : 'steel', 'b' : 'hammock®' }['a']",
                                                          'needsEvaluation': True,
                                                          'resolvable': True,
                                                          'resolved': True,
                                                          'result': 'steel',
                                                          'timeline': []}})

    def test_ResolverCompound(self):
        r = ResolverContainer()
        r.add("stuff", "yes")

        self.assertEqual(r.stuff, "yes")
        self.assertEqual(r["stuff"], "yes")

        r.add("things", "<( 'wo' + 'rm'")

        self.assertEqual(r.things, "worm")
        self.assertEqual(r["things"], "worm")

        r2 = ResolverContainer()
        r2.add("blue", "<( 5 + 27")

        self.assertEqual(r2.blue, 32)

        r.add("sub", r2)

        self.assertEqual(r.to_json(), {'stuff': 'yes', 'sub': {'blue': 32}, 'things': 'worm'})

        self.assertEqual(r.to_json(True), {'stuff': 'yes',
                                           'sub': {'blue': {'evaluated': True,
                                                            'input': '<( 5 + 27',
                                                            'needsEvaluation': True,
                                                            'resolvable': True,
                                                            'resolved': True,
                                                            'result': 32,
                                                            'timeline': []}},
                                           'things': {'evaluated': True,
                                                      'input': "<( 'wo' + 'rm'",
                                                      'needsEvaluation': True,
                                                      'resolvable': True,
                                                      'resolved': True,
                                                      'result': 'worm',
                                                      'timeline': []}})


if __name__ == '__main__':
    unittest.main()
