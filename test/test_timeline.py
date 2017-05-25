#!/usr/bin/python

import unittest
from protocol.timeline import *


class TestTimeline(unittest.TestCase):

    def setUp(self):
        pass

    def test_TimelineEvent(self):
        te = TimelineEvent("DUMMY", "hello", arrow.get("2010-01-01"))

        self.assertEqual("{}".format(te), "DUMMY hello 2010-01-01T00:00:00+00:00")

        te2 = TimelineEvent("DUMMY", ["hello", "ya animal"], arrow.get("2015-01-01"))

        self.assertEqual("{}".format(te2), "DUMMY hello\n\tya animal 2015-01-01T00:00:00+00:00")

        self.assertEqual(te.to_json()["when"], "2010-01-01T00:00:00+00:00")
        self.assertEqual(te2.to_json()["when"], "2015-01-01T00:00:00+00:00")

        Timeline.default_when = arrow.get("2000-06-06")

        te3 = TimelineEvent("DUMMY", ["hello", "oh really!"], arrow.get("2010-01-01"))

        self.assertEqual(te3.to_json()["when"], "2010-01-01T00:00:00+00:00")

        te4 = TimelineEvent("DUMMY", ["hello", "finally!"])

        self.assertEqual(te4.to_json()["when"], "2000-06-06T00:00:00+00:00")

    def test_Timeline(self):
        te = Timeline()
        te.error("OH no!")
        self.assertEqual(te.to_json()[-1]["when"], "--")

        Timeline.default_when = arrow.get("2000-06-06")
        te.warning("Not a huge deal")
        self.assertEqual(te.to_json()[-1]["when"], "2000-06-06T00:00:00+00:00")

        Timeline.default_when = arrow.get("2000-07-07")
        te.note(["Pretty interesting stuff", "Social studies"])
        self.assertEqual(te.to_json()[-1]["when"], "2000-07-07T00:00:00+00:00")

if __name__ == '__main__':
    unittest.main()
