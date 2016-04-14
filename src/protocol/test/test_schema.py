#!/usr/bin/python

import unittest
from schema import *
from pprint import pprint
from jsonschema import FormatChecker
from jsonschema import ValidationError
from jsonschema import validate


class TestSchema(unittest.TestCase):

    def setUp(self):
        pass

    def test_StringParameter(self):
        req = StringParameter("Alpha")
        s = req.to_schema(True)
        self.assertEquals(s, {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'type': 'string',
            'description': 'Alpha'})

        validate("fish", s)
        self.assertRaises(ValidationError, lambda: validate(None, s))

        self.assertEqual(req.parse("fish"), "fish")
        self.assertEqual(req.parse(" fish  "), "fish")

    def test_StringParameterOptional(self):
        optional = StringParameter("Beta", required=False, default="honey")
        s = optional.to_schema(True)
        self.assertEquals(s, {
            'default': 'honey',
            '$schema': 'http://json-schema.org/draft-04/schema',
            'type': ['null', 'string'],
            'description': 'Beta'})

        validate("fish", s)
        validate(None, s)
        self.assertRaises(ValidationError, lambda: validate(1, s))
        self.assertRaises(ValidationError, lambda: validate([1, 2, 3], s))
        self.assertRaises(ValidationError, lambda: validate({"ape": "fur"}, s))

        self.assertEqual(optional.parse("fish"), "fish")
        self.assertEqual(optional.parse(None), "honey")

    def test_ObjectParameter(self):
        obj = ObjectParameter("Erbjerct", properties={
            "one": StringParameter("Uno"),
            "two": StringParameter("Dos", required=False)
        })

        obj_schema = obj.to_schema()

        self.assertEquals(obj_schema, {'description': 'Erbjerct',
                                       'properties': {'one': {'description': 'Uno', 'type': 'string'},
                                                      'two': {'description': 'Dos', 'type': ['null', 'string']}},
                                       'required': ['one'],
                                       'type': 'object'})

        input_1 = {"one": "Alabaster"}
        input_2 = {"one": "Alabaster  ",
                   "two": " Soapstone    ",
                   "five": "Shouldn't match anything!"}

        validate(input_1, obj_schema)
        self.assertEquals(obj.parse(input_1), {"one": "Alabaster"})

        validate(input_2, obj_schema)
        self.assertEquals(obj.parse(input_2), {"one": "Alabaster",
                                                  "two": "Soapstone"})

    def test_ArrayParameter(self):
        arr = ArrayParameter("A list of same-type items..",
                             element=StringParameter("Fruit"),
                             unique=True,
                             min_items=3,
                             max_items=5,
                             required=False)

        arr_schema = arr.to_schema()

        self.assertEquals(arr_schema, {'description': 'A list of same-type items..',
                                       'items': {'description': 'Fruit', 'type': 'string'},
                                       'maxItems': 5,
                                       'minItems': 3,
                                       'type': ['null', 'array'],
                                       'uniqueItems': True})

        input_1 = ["one", "two", "three", "four"]
        input_2 = ["one", "two ", "  three", "four"]

        validate(input_1, arr_schema)
        self.assertEquals(arr.parse(input_1), input_1)

        validate(input_2, arr_schema)
        self.assertEquals(arr.parse(input_2), input_1)

        self.assertRaises(ValidationError, lambda: validate(1, arr_schema))
        self.assertRaises(ValidationError, lambda: validate(["one", "two"], arr_schema))
        self.assertRaises(ValidationError, lambda: validate({"one": "two"}, arr_schema))

    def test_EnumParameter(self):
        req = EnumParameter("some options!", options=["fish", "cheese", "apple"])
        s = req.to_schema(True)
        self.assertEquals(s, {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'description': 'some options!',
            'enum': ['fish', 'cheese', 'apple'],
            'type': 'string'
        })

        validate("fish", s)
        validate("cheese", s)
        validate("apple", s)
        self.assertRaises(ValidationError, lambda: validate("shark", s))
        self.assertRaises(ValidationError, lambda: validate(None, s))
        self.assertRaises(Exception, lambda: req.parse("albatross"))

        self.assertEqual(req.parse("fish"), "fish")
        self.assertEqual(req.parse(" fish  "), "fish")

    def test_UriParameter(self):
        req = UriParameter("AN REsource out in the series of tubes")
        s = req.to_schema(True)
        self.assertEquals(s, {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'description': 'AN REsource out in the series of tubes',
            'format': 'uri',
            'minLength': 1,
            'type': 'string'
        })
        # pprint(FormatChecker.checkers)

        # validate("http://google.com/blah/stuff", s, format_checker=FormatChecker(formats=['uri']))
        self.assertRaises(ValidationError, lambda: validate(15, s))
        self.assertRaises(ValidationError, lambda: validate(None, s))


if __name__ == '__main__':
    unittest.main()
