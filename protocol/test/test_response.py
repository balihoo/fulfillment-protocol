#!/usr/bin/python

import json
import pprint
import arrow
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

    def test_ResponseCache(self):
        r = ActivityResponse("SUCCESS", result=ActivityResult({"data": "yay"}), notes=["Fantastic stuff", "Great details"])

        r.cache_key = "the KEUYUU"
        r.cache_time = arrow.get('2001-01-01T12:12:12Z')
        r.cache_expiration = arrow.get('2001-01-01T12:12:22Z')

        r.instance = "lemon"
        r.run_id = "hound"
        r.workflow_id = "wurf it"
        r.section_name = "-CLASSIFIED-"

        self.assertEqual(r.to_json(), {
            'cache': {'cached': '2001-01-01T12:12:12+00:00',
                      'expires': '2001-01-01T12:12:22+00:00',
                      'key': 'the KEUYUU',
                      'runId': 'hound',
                      'sectionName': '-CLASSIFIED-',
                      'workflowId': 'wurf it'},
            'instance': 'lemon',
            'notes': ["Fantastic stuff", "Great details"],
            'reason': None, 'status': 'SUCCESS', 'trace': [], 'result': {"data": "yay"}})

        r2 = ActivityResponse.from_json(r.to_json())

        self.assertEqual(r.to_json(), r2.to_json())

if __name__ == '__main__':
    unittest.main()
