import re
import json
import boto3
from botocore.client import Config

from fulfillment_exception import (
    FulfillmentException,
    FulfillmentValidationException,
    FulfillmentFailedException
)
from response import ActivityResponse, ActivityStatus
from schema import ObjectParameter
from datazipper import DataZipper
from jsonschema import Draft4Validator

def default_log(message):
    print(message)

class FulfillmentWorker(object):
    SWF_LIMIT = 32000
    param_rex = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')

    def __init__(
        self,
        description,
        parameters,
        result,
        handler,
        region,
        activity_name,
        activity_version,
        swf_domain,
        default_exception=FulfillmentFailedException,
        log=None
    ):
        self._description = description
        self._params = parameters
        self._handler = handler
        self._result = result
        self._schema = {
            'description': description,
            'params': ObjectParameter('', properties=parameters).to_schema(),
            'result': result.to_schema()
        }
        self._validator = Draft4Validator(ObjectParameter('', properties=parameters).to_schema(True))
        self._default_exception = default_exception
        self._log = log if log else default_log
        self._activity = {
            'name': activity_name,
            'version': activity_version
        }
        self._task_list = {'name': '{}{}'.format(activity_name, activity_version)}
        self._swf_domain = swf_domain
        self._activity_registered = False

        self._swf = boto3.client(
            'swf',
            region_name=region,
            config=Config(
                # https://github.com/boto/botocore/pull/634
                connect_timeout=50,
                read_timeout=70
            )
        )

    def _poll(self):
        self._log('polling')

        task = self._swf.poll_for_activity_task(
            domain=self._swf_domain,
            taskList=self._task_list
        )
        token = task.get('taskToken', None)

        if token:
            return task.get('input'), token

        # No task
        return None, None

    def _parse(self, event):
        kwargs = {}
        for (name, param) in self._params.items():
            try:
                value = event[name] if name in event else None
                # http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case
                param_name = FulfillmentWorker.param_rex.sub(r'_\1', name.replace(' ', '_')).lower()
                kwargs[param_name] = param.parse(value, name)
            except Exception as e:
                msg = "Error parsing parameter '{}'".format(name)
                raise FulfillmentValidationException(msg, inner_exception=e)
        return kwargs

    def _parse_result(self, result):
        if isinstance(result, tuple):
            (res, notes) = result
            return self._result.parse(res, 'Parsing result:'), notes
        else:
            return self._result.parse(result, 'Parsing result:'), []

    def _serialize_response(self, response):
        response_json = response.to_json()
        response_text = json.dumps(response_json)

        if len(response_text) >= FulfillmentWorker.SWF_LIMIT:
            return DataZipper.deliver(response_text, FulfillmentWorker.SWF_LIMIT)

        return response_text

    def _success(self, token, result, notes):
        response = ActivityResponse(ActivityStatus.SUCCESS, result, notes=notes)
        self._swf.respond_activity_task_completed(taskToken=token, result=self._serialize_response(response))

    def _fail(self, token, e):
        error_message = str(e)

        response = ActivityResponse(
            e.response_code(),
            notes=e.notes,
            result=error_message,
            trace=e.trace(),
            reason=error_message
        )
        response_string = self._serialize_response(response)

        if e.retry():
            self._swf.respond_activity_task_canceled(taskToken=token, details=response_string)
        else:
            self._swf.respond_activity_task_failed(taskToken=token, details=response_string)

    def _handle(self, token, event):
        if isinstance(event, str):
            event = json.loads(DataZipper.receive(event))

        if 'LOG_INPUT' in event:
            self._log(json.dumps(event, indent=4))

        if 'RETURN_SCHEMA' in event:
            return self._schema

        validation_errors = []
        for err in self._validator.iter_errors(event):
            validation_errors.append({
                'cause': err.cause,
                'context': err.context,
                'message': err.message,
                'path': '/'.join([str(p) for p in err.path]),
                'relative_path': '/'.join([str(p) for p in err.relative_path]),
                'absolute_path': '/'.join([str(p) for p in err.absolute_path]),
                'validator': err.validator,
                'validator_value': err.validator_value
            })

        if validation_errors:
            return self._fail(token, ActivityResponse(ActivityStatus.INVALID, validation_errors=validation_errors))

        try:
            kwargs = self._parse(event)
            result = self._handler(**kwargs)
            (valid_result, notes) = self._parse_result(result)
            self._success(token, valid_result, notes)
        except FulfillmentException as e:
            self._fail(token, e)
        except Exception as e:
            wrapped = self._default_exception('unhandled exception', inner_exception=e)
            self._fail(token, wrapped)

    def run(self):
        input, token = self._poll()

        if token:
            self._log('task {}'.format(token))
            event = json.loads(DataZipper.receive(input))
            self._handle(token, event)
        else:
            self._log('No work to be done for {}/{}'.format(self._swf_domain, self._task_list['name']))
