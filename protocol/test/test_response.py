#!/usr/bin/python

import json
import pprint
import unittest
from response import ActivityResult, ActivityResponse


class TestResponse(unittest.TestCase):

    def setUp(self):
        pass

    def test_Response(self):
        r = ActivityResponse("FAILED")
        self.assertEqual(r.to_json(), {'notes': [], 'reason': None, 'status': 'FAILED', 'trace': []})

        sr = ActivityResponse.from_json(r.to_json())

        self.assertEqual(sr.to_json(), r.to_json())

    def test_ResponseNotes(self):
        r = ActivityResponse("SUCCESS", result=ActivityResult({"data": "yay"}), notes=["Fantastic stuff", "Great details"])
        self.assertEqual(r.to_json(), {'notes': ["Fantastic stuff", "Great details"],
                                       'reason': None, 'status': 'SUCCESS', 'trace': [], 'result': {"data": "yay"}})

        sr = ActivityResponse.from_json(r.to_json())

        self.assertEqual(sr.to_json(), r.to_json())


if __name__ == '__main__':
    unittest.main()
