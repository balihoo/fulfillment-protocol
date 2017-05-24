#!/usr/bin/python

import unittest
from schema import *
from jsonschema import Draft4Validator


class TestSchema(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_StringParameter(self):
        req = StringParameter("Alpha")
        s = req.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'type': 'string',
            'description': 'Alpha'})

        self.assertTrue(validator.is_valid("fish"))
        self.assertFalse(validator.is_valid(None))

        self.assertEqual(req.parse("fish"), "fish")
        self.assertEqual(req.parse(" fish  "), "fish")

    def test_StringParameterOptional(self):
        optional = StringParameter("Beta", required=False, default="honey")
        s = optional.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {
            'default': 'honey',
            '$schema': 'http://json-schema.org/draft-04/schema',
            'type': ['null', 'string'],
            'description': 'Beta'})

        self.assertTrue(validator.is_valid("fish"))
        self.assertTrue(validator.is_valid(None))
        self.assertFalse(validator.is_valid(1))
        self.assertFalse(validator.is_valid([1, 2, 3]))
        self.assertFalse(validator.is_valid({"ape": "fur"}))

        self.assertEqual(optional.parse("fish"), "fish")
        self.assertEqual(optional.parse(None), "honey")

    def test_StringParameterLength(self):
        optional = StringParameter("Beta", min_length=5, max_length=10, default="honey")
        s = optional.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {
            'default': 'honey',
            'maxLength': 10,
            'minLength': 5,
            '$schema': 'http://json-schema.org/draft-04/schema',
            'type': ['null', 'string'],
            'description': 'Beta'})

        self.assertTrue(validator.is_valid("fishsticks"))
        self.assertTrue(validator.is_valid(None))
        self.assertFalse(validator.is_valid("fish"))
        self.assertFalse(validator.is_valid(1))
        self.assertFalse(validator.is_valid([1, 2, 3]))
        self.assertFalse(validator.is_valid({"ape": "fur"}))

        self.assertEqual(optional.parse("fish"), "fish")
        self.assertEqual(optional.parse(None), "honey")

    def test_ObjectParameter(self):
        obj = ObjectParameter("Erbjerct", properties={
            "one": StringParameter("Uno"),
            "two": StringParameter("Dos", required=False)
        })

        obj_schema = obj.to_schema()
        validator = Draft4Validator(obj_schema)

        self.assertEqual(obj_schema, {'description': 'Erbjerct',
                                       'properties': {'one': {'description': 'Uno', 'type': 'string'},
                                                      'two': {'description': 'Dos', 'type': ['null', 'string']}},
                                       'required': ['one'],
                                       'type': 'object'})

        input_1 = {"one": "Alabaster"}
        input_2 = {"one": "Alabaster  ",
                   "two": " Soapstone    ",
                   "five": "Shouldn't match anything!"}

        self.assertTrue(validator.is_valid(input_1))
        self.assertEqual(obj.parse(input_1), {"one": "Alabaster"})

        self.assertTrue(validator.is_valid(input_2))
        self.assertEqual(obj.parse(input_2), {"one": "Alabaster",
                                                  "two": "Soapstone"})

        dobj = ObjectParameter("All defaults", properties={
            "fruit": StringParameter("The name of a fruit", default="kiwi"),
            "vegetable": StringParameter("The name of a vegetable", default="celery")
        }, default={})

        dobj_schema = dobj.to_schema()
        dvalidator = Draft4Validator(dobj_schema)

        self.assertEqual(dobj_schema, {'default': {},
                                        'description': 'All defaults',
                                        'properties': {'fruit': {'default': 'kiwi',
                                                                 'description': 'The name of a fruit',
                                                                 'type': ['null', 'string']},
                                                       'vegetable': {'default': 'celery',
                                                                     'description': 'The name of a vegetable',
                                                                     'type': ['null', 'string']}},
                                        'required': [],
                                        'type': ['null', 'object']})

        input_1 = None
        input_2 = {"fruit": "blueberry"}

        self.assertTrue(dvalidator.is_valid(input_1))
        self.assertEqual(dobj.parse(input_1), {'fruit': 'kiwi', 'vegetable': 'celery'})

        self.assertTrue(dvalidator.is_valid(input_2))
        self.assertEqual(dobj.parse(input_2), {'fruit': 'blueberry', 'vegetable': 'celery'})

    def test_ArrayParameter(self):
        arr = ArrayParameter("A list of same-type items..",
                             element=StringParameter("Fruit"),
                             unique=True,
                             min_items=3,
                             max_items=5,
                             required=False)

        arr_schema = arr.to_schema()
        validator = Draft4Validator(arr_schema)

        self.assertEqual(arr_schema, {'description': 'A list of same-type items..',
                                       'items': {'description': 'Fruit', 'type': 'string'},
                                       'maxItems': 5,
                                       'minItems': 3,
                                       'type': ['null', 'array'],
                                       'uniqueItems': True})

        input_1 = ["one", "two", "three", "four"]
        input_2 = ["one", "two ", "  three", "four"]

        self.assertTrue(validator.is_valid(input_1))
        self.assertEqual(arr.parse(input_1), input_1)

        self.assertTrue(validator.is_valid(input_2))
        self.assertEqual(arr.parse(input_2), input_1)

        self.assertFalse(validator.is_valid(1))
        self.assertFalse(validator.is_valid(["one", "two"]))
        self.assertFalse(validator.is_valid({"one": "two"}))

    def test_EnumParameter(self):
        req = EnumParameter("some options!", options=["fish", "cheese", "apple"])
        s = req.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'description': 'some options!',
            'enum': ['fish', 'cheese', 'apple'],
            'type': 'string'
        })

        self.assertTrue(validator.is_valid("fish"))
        self.assertTrue(validator.is_valid("cheese"))
        self.assertTrue(validator.is_valid("apple"))
        self.assertFalse(validator.is_valid("shark"))
        self.assertFalse(validator.is_valid(None))
        self.assertRaises(Exception, lambda: req.parse("albatross"))

        self.assertEqual(req.parse("fish"), "fish")
        self.assertEqual(req.parse(" fish  "), "fish")

    def test_UriParameter(self):
        req = UriParameter("AN REsource out in the series of tubes")
        s = req.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'description': 'AN REsource out in the series of tubes',
            'format': 'uri',
            'minLength': 1,
            'type': 'string'
        })
        # pprint(FormatChecker.checkers)

        # self.assertTrue(validator.is_valid("http://google.com/blah/stuff", s, format_checker=FormatChecker(formats=['uri']))
        self.assertFalse(validator.is_valid(15))
        self.assertFalse(validator.is_valid(None))

    def test_UuidParameter(self):
        req = UuidParameter("02ef139a-417a-4328-9953-5996b9f36dae")
        s = req.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'type': 'string',
            'description': '02ef139a-417a-4328-9953-5996b9f36dae',
            'pattern': '^[0-9A-Fa-f]{8}-([0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}$'
        })

        self.assertTrue(validator.is_valid("02ef139a-417a-4328-9953-5996b9f36dae"))
        self.assertTrue(validator.is_valid("02EF139A-417A-4328-9953-5996B9F36DAE"))
        self.assertTrue(validator.is_valid("02EF139A-417A-4328-9953-5996b9f36dae"))
        self.assertFalse(validator.is_valid(None))
        self.assertFalse(validator.is_valid("123-ABC"))
        self.assertFalse(validator.is_valid(12345678-1234-1234-1234-123456789012))
        self.assertFalse(validator.is_valid("02ef139a_417a-4328-9953-5996b9f36dae"))
        self.assertFalse(validator.is_valid("X02ef139a-417a-4328-9953-5996b9f36dae"))

    def test_OneOfParameter(self):
        req = OneOfParameter("Just one of these things is valid!", options=(
            ArrayParameter("A list of junk", StringParameter("A String", min_length=5)),
            IntParameter("Some number")
        ))
        s = req.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {'$schema': 'http://json-schema.org/draft-04/schema',
                              'description': 'Just one of these things is valid!',
                              'oneOf': [{'description': 'A list of junk',
                                         'items': {'description': 'A String',
                                                   'minLength': 5,
                                                   'type': 'string'},
                                         'type': 'array'},
                                        {'description': 'Some number', 'type': 'integer'}],
                              'type': ['array', 'integer']})

        self.assertTrue(validator.is_valid(12))
        self.assertTrue(validator.is_valid(["hello"]))
        self.assertTrue(validator.is_valid(["hello", "there"]))

        self.assertFalse(validator.is_valid("hello"))
        self.assertFalse(validator.is_valid(["hello", 1]))
        self.assertFalse(validator.is_valid(1.2345))
        for e in validator.iter_errors(1):
            # print dir(e)
            print(e.message, e.instance, end=' ')
            print([c.message for c in e.context])
        return True

    def test_AnyOfParameter(self):
        req = AnyOfParameter("Any of these things could be valid!", options=(
            ArrayParameter("A list of junk", StringParameter("A String", min_length=5)),
            IntParameter("Some number")
        ))
        s = req.to_schema(True)
        validator = Draft4Validator(s)
        self.assertEqual(s, {'$schema': 'http://json-schema.org/draft-04/schema',
                              'description': 'Any of these things could be valid!',
                              'anyOf': [{'description': 'A list of junk',
                                         'items': {'description': 'A String',
                                                   'minLength': 5,
                                                   'type': 'string'},
                                         'type': 'array'},
                                        {'description': 'Some number', 'type': 'integer'}],
                              'type': ['array', 'integer']})

        self.assertTrue(validator.is_valid(12))
        self.assertTrue(validator.is_valid(["hello"]))
        self.assertTrue(validator.is_valid(["hello", "there"]))

        self.assertFalse(validator.is_valid("hello"))
        self.assertFalse(validator.is_valid(["hello", 1]))
        self.assertFalse(validator.is_valid(1.2345))
        for e in validator.iter_errors(1):
            print(dir(e), e.message, e.instance, end=' ')
            for c in e.context:
                print(c.message)
        return True

    def test_ResolverObjectParameter(self):
        obj = ResolverObjectParameter("Erbjerct", "Erbject description", properties={
            "one": StringParameter("Uno", example='Alpha'),
            "two": StringParameter("Dos", required=False),
            "tres": StringParameter("Tres", default="AMAZING"),
            "qqq": ObjectParameter("Blerb", properties={
                "alpha": IntParameter("Number of ponies you've ever ridden"),
                "bete": StringParameter("Name your ferocious fish")
            }, required=False)
        })

        obj_schema = obj.to_schema()
        validator = Draft4Validator(obj_schema)

        self.assertEqual(obj_schema, {'description': 'Erbject description',
                                       'properties': {'one': {'description': 'Uno', 'type': 'string', 'x-example': 'Alpha'},
                                                      'two': {'description': 'Dos', 'type': ['null', 'string']},
                                                      'tres': {'default': 'AMAZING',
                                                               'description': 'Tres',
                                                               'type': ['null', 'string']},
                                                      'qqq': {'required': ['alpha', 'bete'],
                                                              'type': ['null', 'object'],
                                                              'description': 'Blerb',
                                                              'properties':
                                                                  {'alpha': {'type': 'integer', 'description': "Number of ponies you've ever ridden"},
                                                                   'bete': {'type': 'string', 'description': 'Name your ferocious fish'}}}
                                                      },
                                       'required': ['one'],
                                       'type': 'object'})

        input_1 = {"one": "Alabaster"}
        input_2 = {"one": "Alabaster  ",
                   "two": "<( return 'alpha' + ' ' + 'omega' ",
                   "five": "Shouldn't match anything!"}
        input_3 = {"two": "<( return 'alpha' + ' ' + 'omega' ",
                   "five": "Shouldn't match anything!"}
        input_4 = {"one": "Alabaster",
                   "qqq": {
                       "alpha": 15
                   }}

        self.assertTrue(validator.is_valid(input_1))
        con1 = obj.parse(input_1)
        self.assertEqual(con1["one"], "Alabaster")

        self.assertTrue(validator.is_valid(input_2))
        con2 = obj.parse(input_2)
        self.assertEqual(con2["two"], "alpha omega")

        self.assertRaises(Exception, lambda x: con2["tomato"])

        self.assertEqual(con2["tres"], "AMAZING")

        with self.assertRaises(Exception) as context:
            obj.parse(input_3)
            self.assertEqual("Exception while parsing : Erbjerct/[one]-Missing required parameter (description: Uno)", context.exception)

        with self.assertRaises(Exception) as context:
            obj.parse(input_4)
            self.assertEqual("Exception while parsing : Exception while parsing Erbjerct/[qqq]: Erbjerct/[qqq][bete]-Missing required parameter (description: Name your ferocious fish)", context.exception)

    def test_ResolverObjectParameterExtra(self):
        obj = ResolverObjectParameter("Erbjerct", "Erbjerct description", properties={
            "one": StringParameter("Uno"),
            "two": StringParameter("Dos", required=False),
            "tres": StringParameter("Tres", default="AMAZING")
        }, extra_type=StringParameter("Extra thing"))

        obj_schema = obj.to_schema()
        validator = Draft4Validator(obj_schema)

        m = obj.parse({"flower": "<( 'apple'", "one": "fine"})
        self.assertEqual(m.flower, "apple")


if __name__ == '__main__':
    unittest.main()
