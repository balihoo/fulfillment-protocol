from fulfillment_exception import (
    FulfillmentException,
    FulfillmentValidationException,
    FulfillmentFailedException
)

from schema import ObjectParameter
from datazipper import DataZipper
import re
import json

#http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case
param_rex = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
def fix_param_name(name):
    """ convert camel case names (with spaces) to normal python arg names """
    return param_rex.sub(r'_\1', name.replace(' ', '_')).lower()

class FulfillmentFunction(object):

    SWF_LIMIT = 32768

    def __init__(self, description, parameters, result, handler, default_exception=FulfillmentFailedException):
        self._description = description
        self._params = parameters
        self._handler = handler
        self._result = result
        self._schema = {
            'description': description,
            'params': ObjectParameter("", properties=parameters).to_schema(),
            'result': result.to_schema()
        }
        self._exception = default_exception

    def make_response(self, status, notes=None, result=None, trace=None, reason=None):
        response = {
            'result': result,
            'status': status,
        }
        if notes:
            response['notes'] = notes
        if trace:
            response['trace'] = trace
        if reason:
            response['reason'] = reason

        response_string = json.dumps(response)
        if len(response_string) > FulfillmentFunction.SWF_LIMIT:
            return DataZipper.deliver(response_string, FulfillmentFunction.SWF_LIMIT)
        else:
            return response

    def error_response(self, e):
        return self.make_response(e.response_code, notes=e.notes, result=e.message, trace=e.trace(), reason=e.message)

    def success_response(self, result, notes):
        return self.make_response("SUCCESS", notes, result)

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
        if type(event) == str:
            event = json.loads(DataZipper.receive(event))

        if 'LOG_INPUT' in event:
            print(json.dumps(event, indent=4))

        if 'LOG_CONTEXT' in event:
            print(json.dumps(context, indent=4))

        if 'RETURN_SCHEMA' in event:
            return self._schema

        try:
            kwargs = self.parse(event)
            result = self._handler(**kwargs)
            (valid_result, notes) = self.parse_result(result)
            return self.success_response(valid_result, notes)
        except FulfillmentException as e:
            return self.error_response(e)
        except Exception as e:
            wrapped = self._exception("unhandled exception", inner_exception=e)
            return self.error_response(wrapped)


