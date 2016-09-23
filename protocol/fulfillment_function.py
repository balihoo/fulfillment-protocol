from fulfillment_exception import (
    FulfillmentException,
    FulfillmentValidationException,
    FulfillmentFailedException
)

from schema import ObjectParameter
from datazipper import DataZipper
from response import ActivityResponse, ActivityStatus
from jsonschema import Draft4Validator
import re
import json

#http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case
param_rex = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
def fix_param_name(name):
    """ convert camel case names (with spaces) to normal python arg names """
    return param_rex.sub(r'_\1', name.replace(' ', '_')).lower()

class FulfillmentFunction(object):

    SWF_LIMIT = 32768

    def __init__(
            self,
            description,
            parameters,
            result,
            handler,
            default_exception=FulfillmentFailedException,
            disable_protocol=False
    ):
        self._description = description
        self._params = parameters
        self._handler = handler
        self._result = result
        self._schema = {
            'description': description,
            'params': ObjectParameter("", properties=parameters).to_schema(),
            'result': result.to_schema()
        }
        self._validator = Draft4Validator(ObjectParameter("", properties=parameters).to_schema(True))
        self._exception = default_exception
        self._disable_protocol = disable_protocol # Allow the function author to disable the protocol (like Node)

    def error_response(self, e, disable_protocol):
        if disable_protocol:
            raise e

        response = ActivityResponse(e.response_code(), notes=e.notes, result=e.message, trace=e.trace(), reason=e.message)
        response_json = response.to_json()
        response_text = json.dumps(response_json)
        if len(response_text) >= FulfillmentFunction.SWF_LIMIT:
            return DataZipper.deliver(response_text, FulfillmentFunction.SWF_LIMIT)
        return response_json

    def success_response(self, result, notes, disable_protocol):
        if disable_protocol:
            return result

        response = ActivityResponse(ActivityStatus.SUCCESS, result, notes=notes)
        response_json = response.to_json()
        response_text = json.dumps(response_json)
        if len(response_text) >= FulfillmentFunction.SWF_LIMIT:
            return DataZipper.deliver(response_text, FulfillmentFunction.SWF_LIMIT)
        return response_json

    def invalid_response(self, validation_errors, disable_protocol):
        if disable_protocol:
            return None

        response = ActivityResponse(ActivityStatus.INVALID, notes=validation_errors)
        response_json = response.to_json()
        response_text = json.dumps(response_json)
        if len(response_text) >= FulfillmentFunction.SWF_LIMIT:
            return DataZipper.deliver(response_text, FulfillmentFunction.SWF_LIMIT)
        return response_json

    def parse(self, event):
        kwargs = {}
        for (name, param) in self._params.iteritems():
            try:
                value = event[name] if name in event else None
                param_name = fix_param_name(name)
                kwargs[param_name] = param.parse(value)
            except Exception as e:
                msg = "Error parsing parameter '{}'".format(name)
                raise FulfillmentValidationException(msg, inner_exception=e)
        return kwargs

    def parse_result(self, result):
        if isinstance(result, tuple):
            (res, notes) = result
            return (self._result.parse(res), notes)
        else:
            return (self._result.parse(result), [])

    def handle(self, event, context):
        if type(event) in (str, unicode):
            event = json.loads(DataZipper.receive(event))

        if 'LOG_INPUT' in event:
            print(json.dumps(event, indent=4))

        if 'LOG_CONTEXT' in event:
            print(json.dumps(context, indent=4))

        if 'RETURN_SCHEMA' in event:
            return self._schema

        # Always override _disable_protocol with the value in the event (if there is one)
        disable_protocol = event.get("DISABLE_PROTOCOL", self._disable_protocol)

        validation_errors = ["Validation Error:{} @{}".format(str(err), err.absolute_path)
                             for err in self._validator.iter_errors(event)]

        if validation_errors:
            return self.invalid_response(validation_errors, disable_protocol)

        try:
            kwargs = self.parse(event)
            result = self._handler(**kwargs)
            (valid_result, notes) = self.parse_result(result)
            return self.success_response(valid_result, notes, disable_protocol)
        except FulfillmentException as e:
            return self.error_response(e, disable_protocol)
        except Exception as e:
            wrapped = self._exception("unhandled exception", inner_exception=e)
            return self.error_response(wrapped, disable_protocol)


