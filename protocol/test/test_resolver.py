#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import pprint
import unittest
from resolver import Resolver, ResolverContainer


class TestResolver(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_Contains(self):
        r = Resolver("stuff")
        self.assertTrue(r.contains_code("<(hello"))

    def test_Basic(self):
        r = Resolver("stuff")
        self.assertTrue(r.evaluated)

    def test_ExecSimple(self):
        r = Resolver("<(return [1, 2, 3]")
        self.assertFalse(r.evaluated)
        self.assertEqual(r.evaluate(), [1, 2, 3])

    def test_ExecMultiLine(self):
        r = Resolver(["<(",
            "def func(things):",
            "  return s2j('[1,2,{}]'.format(things))",
            "return func('3')"
        ]).evaluate()
        self.assertEqual(r, [1, 2, 3])

    def test_ExecBadBuiltins(self):
        r = Resolver(["<(",
            "with open('foo') as f:",
            "  f.write('bar')"
        ])
        self.assertEqual(r.evaluate(), None)
        self.assertEqual(r.last_msg(), "Error in script: NameError(line 2) global name 'open' is not defined")

    def test_ExecImport(self):
        r = Resolver("<(\nimport json")
        self.assertEqual(r.evaluate(), None)
        self.assertFalse(r.is_resolved())
        self.assertEqual(r.last_msg(), "Error in script: ImportError(line 2) __import__ not found")

    def test_ExecJson2String(self):
        res = Resolver("<(j2s({ 'foo': 13 })").evaluate()
        self.assertEqual(res, '{"foo": 13}')

    def test_ExecString2Json(self):
        res = Resolver("<(s2j('{ \"foo\": 13 }')").evaluate()
        self.assertEqual(res, {"foo": 13})

    def test_ExecUrlEncode(self):
        res = Resolver("<(urlencode('string_of_characters_like_these:$#@=?%^Q^$')").evaluate()
        self.assertEqual(res,'string_of_characters_like_these%3A%24%23%40%3D%3F%25%5EQ%5E%24')

    def test_ExecGenerator(self):
        res = Resolver(["<(",
            "def fib(n):",
            "    a, b = 0, 1",
            "    for _ in xrange(n):",
            "        yield a",
            "        a, b = b, a + b",
            "return list(fib(10))"
        ]).evaluate()
        self.assertEqual(res, [0, 1, 1, 2, 3, 5, 8, 13, 21, 34])

    def test_ExecRecursion(self):
        res = Resolver(["<(",
            "def fib(n, a=0, b=1):",
            "  return fib(n-1, b, a+b) if n > 0 else a",
            "return fib(10)"
        ]).evaluate()
        self.assertEqual(res, 55)

    def test_InfiniteLoop(self):
        r = Resolver(["<(",
            "while True:",
            "  pass"
        ], timeout_sec=1)
        self.assertEqual(r.evaluate(), None)
        self.assertFalse(r.is_resolved())
        self.assertEqual(r.last_msg(), "Error in script: Exception(line 14) TIMEOUT")

    def test_ExecException(self):
        res = Resolver(["<(",
            "try:",
            "  return 0 / 0",
            "except ZeroDivisionError as z:",
            "  return 'divide by zero'"
        ]).evaluate()
        self.assertEqual(res, 'divide by zero')

    def test_ExecCompound(self):
        r = Resolver({"one two three": "<(return [1, 2, 3]"})

        self.assertFalse(r.evaluated)
        r.evaluate()
        self.assertEqual(r.result, {"one two three": [1, 2, 3]})

    def test_ExecError(self):
        r = Resolver({"one two three": "<(return [1, 2, 3"})

        self.assertFalse(r.evaluated)
        r.evaluate()
        self.assertEqual(r.last_msg(), "SyntaxError(line 3:5) invalid syntax 'raise exec_return(resolver_func())\n'")
        self.assertEqual(r.get_result(), None)

    def test_ExecSectionGen(self):
        res = Resolver(["<(",
            "r = range(65,91)",
            "names = [chr(a)+chr(b) for a in r for b in r]",
            "def valsec(value):",
            "  return { 'value': '#prefix#_{}'.format(value) }",
            "return j2s({",
            "  'sections': { name:valsec(name) for name in names }",
            "})"
        ]).evaluate()
        self.assertEqual(len(res), 21646)

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

        expected = {'stuff': 'yes',
                    'things': {'evaluated': True,
                               'input': "<( 'wo' + 'rm'",
                               'needsEvaluation': True,
                               'resolvable': True,
                               'resolved': True,
                               'result': 'worm',
                               'timeline': [],
                               'code': "def resolver_func():\n    return  'wo' + 'rm'\nraise exec_return(resolver_func())"},
                    'whaaa': 'steely',
                    'whaaa_eval': {'evaluated': True,
                                   'input': "<( { 'a' : 'steel', 'b' : 'hammock®' }['a']",
                                   'needsEvaluation': True,
                                   'resolvable': True,
                                   'resolved': True,
                                   'result': 'steel',
                                   'timeline': [],
                                   'code': "def resolver_func():\n    return  { 'a' : 'steel', 'b' : 'hammock\xc2\xae' }['a']\nraise exec_return(resolver_func())"}}
        detailed = r.to_json(detailed=True)

        self.assertEqual(expected, detailed)

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

        expected = {'stuff': 'yes',
                    'sub': {'blue': {'evaluated': True,
                                     'input': '<( 5 + 27',
                                     'needsEvaluation': True,
                                     'resolvable': True,
                                     'resolved': True,
                                     'result': 32,
                                     'code': 'def resolver_func():\n    return  5 + 27\nraise exec_return(resolver_func())',
                                     'timeline': []}},
                    'things': {'evaluated': True,
                               'input': "<( 'wo' + 'rm'",
                               'needsEvaluation': True,
                               'resolvable': True,
                               'resolved': True,
                               'result': 'worm',
                               'code': "def resolver_func():\n    return  'wo' + 'rm'\nraise exec_return(resolver_func())",
                               'timeline': []}}
        detailed = r.to_json(detailed=True)
        self.assertEqual(expected, detailed)


if __name__ == '__main__':
    unittest.main()
