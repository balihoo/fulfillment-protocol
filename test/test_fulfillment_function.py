#!/usr/bin/python
import unittest

from protocol.fulfillment_function import FulfillmentFunction
from protocol.schema import StringParameter, StringResult, ObjectParameter, BooleanParameter, ArrayParameter


class TestFulfillmentFunction(unittest.TestCase):
    def test_rate_limit_url_in_schema(self):

        def the_handler():
            pass

        func = FulfillmentFunction(
            description="Manages Test Junk extensions",
            parameters={
                "account": StringParameter("Participant Fake Id"),
                "things": ArrayParameter("Bunch of things",
                                            element=ObjectParameter("", properties={
                                                "text": StringParameter("Whatever"),
                                                "boolThing": BooleanParameter("Nope", required=False),
                                                }), required=False),
            },


            result=StringResult("Campaign ID"),
            handler=the_handler,
            rate_limit_url="the_limit_url_lol.com.org"
        )

        schema = func.handle({'RETURN_SCHEMA': True}, {})
        self.assertEqual(schema['rate_limit_url'], "the_limit_url_lol.com.org")

if __name__ == '__main__':
    unittest.main()
