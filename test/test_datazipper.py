#!/usr/bin/python

import os
import unittest
from protocol.datazipper import DataZipper, to_unicode

class MockS3Object(object):
    def __init__(self, bucket, key):
        self.bucket = bucket
        self.key = key.replace("/", "_")
        self.filename = self._filename()

    def _filename(self):
        return "test/{}_{}.outons3butnotreally".format(self.bucket, self.key)

    def put(self, Body = None) -> None:
        self._reset()
        with open(self.filename, "wb") as f:
            f.write(Body)

    def get(self):
        return {"Body": open(self.filename, "rb")}

    def _reset(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

class MockS3(object):

    def Object(self, bucket, key):
        return MockS3Object(bucket, key)

class TestDataZipper(unittest.TestCase):

    def setUp(self):
        DataZipper.s3 = MockS3()

    def test_simple(self):
        self.assertEqual(DataZipper.deliver("Hello", 5000), "Hello")

    def test_zip(self):
        with open('test/bigTestData.json', 'r') as big_json_file:
            big_json = big_json_file.read()

            delivered = DataZipper.deliver(big_json, 30000)
            self.assertTrue(delivered.startswith('FF-ZIP:72686:eJy9vWt3W0eSJfp9fgVWzYeeu1ZlMd+P+dSUL'))

            received = DataZipper.receive(delivered)
            self.assertTrue(len(received) == 72686)

            self.assertTrue(received == big_json)

    def test_url(self):
        with open('test/biggerTestData.json', 'r') as bigger_json_file:
            bigger_json = bigger_json_file.read()

            delivered = DataZipper.deliver(bigger_json, 30000)
            self.assertTrue(delivered =="FF-URL:d76383593d9bb09835c4a248b3d42b22:s3://balihoo.dev.fulfillment/retain_30_180/zipped-ff/d76383593d9bb09835c4a248b3d42b22.ff")

            received = DataZipper.receive(delivered)
            self.assertTrue(len(received) == 394710)

            self.assertTrue(received == bigger_json)

    def test_to_unicode(self):
        as_unicode = "☃"  # snowman!
        as_bytes = as_unicode.encode()
        self.assertEqual(as_unicode, to_unicode(as_unicode))
        self.assertEqual(as_unicode, to_unicode(as_bytes))

if __name__ == '__main__':
    unittest.main()
