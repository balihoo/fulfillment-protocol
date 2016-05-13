#!/usr/bin/python

import json
import pprint
import unittest
from resolver import Resolver


class TestResolver(unittest.TestCase):

    def setUp(self):
        pass

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


if __name__ == '__main__':
    unittest.main()
