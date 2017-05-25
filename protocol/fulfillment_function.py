from typing import Union

from .fulfillment_parser import parse_event, parse_result
from .fulfillment_exception import (
    FulfillmentException,
    FulfillmentFailedException
)

from .schema import ObjectParameter
from .datazipper import DataZipper
from .response import ActivityResponse, ActivityStatus
from jsonschema import Draft4Validator
import json


class FulfillmentFunction(object):

    SWF_LIMIT = 32000

    def __init__(
        self,
        description,
        parameters,
        result,
        handler,
        debug_handler=None,
        default_exception=FulfillmentFailedException,
        disable_protocol=False
    ):
        self._description = description
        self._params = parameters
        self._handler = handler
        self._debug_handler = debug_handler
        self._result = result
        self._schema = {
            'description': description,
            'params': ObjectParameter("", properties=parameters).to_schema(),
            'result': result.to_schema()
        }
        self._validator = Draft4Validator(ObjectParameter("", properties=parameters).to_schema(True))
        self._exception = default_exception
        self._disable_protocol = disable_protocol # Allow the function author to disable the protocol (like Node)

    @classmethod
    def error_response(cls, e):
        message = str(e)  # BaseException.message deprecated (see PEP-0352)
        response = ActivityResponse(e.response_code(), notes=e.notes, result=message, trace=e.trace(), reason=message)
        return response.serialize()

    @classmethod
    def success_response(cls, result, notes, disable_protocol):
        if disable_protocol:
            return result

        response = ActivityResponse(ActivityStatus.SUCCESS, result, notes=notes)
        return response.serialize()

    @classmethod
    def invalid_response(cls, validation_errors, disable_protocol):
        if disable_protocol:
            return None

        response = ActivityResponse(ActivityStatus.INVALID, validation_errors=validation_errors)
        return response.serialize()

    def handle(self, event: Union[str, dict], context):
        if isinstance(event, str):
            event = json.loads(DataZipper.receive(event))

        if 'LOG_INPUT' in event:
            print(json.dumps(event, indent=4))

        if 'LOG_CONTEXT' in event:
            print(json.dumps(context, indent=4))

        if 'RETURN_SCHEMA' in event:
            return self._schema

        # Always override _disable_protocol with the value in the event (if there is one)
        disable_protocol = event.get("DISABLE_PROTOCOL", self._disable_protocol)

        validation_errors = self._validator.validate(event)
        if validation_errors:
            return self.invalid_response(validation_errors, disable_protocol)

        try:
            kwargs = parse_event(event, self._params)
            if 'DEBUG_MODE' in event:
                result = self._debug_handler(debug_mode=event['DEBUG_MODE'], **kwargs)
            else:
                result = self._handler(**kwargs)
            (valid_result, notes) = parse_result(result, self._result)
            return self.success_response(valid_result, notes, disable_protocol)
        except FulfillmentException as e:
            if disable_protocol:
                raise

            return self.error_response(e)
        except Exception as e:
            if disable_protocol:
                raise

            wrapped = self._exception("unhandled exception", inner_exception=e)
            return self.error_response(wrapped)


