import json
import boto3
from botocore.client import Config

from .fulfillment_parser import parse_event, parse_result
from .fulfillment_exception import (
    FulfillmentException,
    FulfillmentFailedException
)
from .response import ActivityResponse, ActivityStatus
from .schema import ObjectParameter
from .datazipper import DataZipper
from .param_validator import ParamValidator


def default_log(message):
    print(message)


class FulfillmentWorker(object):
    SWF_LIMIT = 32000

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
        default_exception=FulfillmentFailedException
    ):
        self._description = description
        self._params = parameters
        self._handler = handler
        self._result = result
        self._activity = {
            'name': activity_name,
            'version': activity_version
        }
        self._schema = {
            'description': description,
            'params': ObjectParameter('', properties=parameters).to_schema(),
            'result': result.to_schema(),
            'activity': self._activity
        }
        self._validator = ParamValidator(parameters)
        self._default_exception = default_exception
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
        task = self._swf.poll_for_activity_task(
            domain=self._swf_domain,
            taskList=self._task_list
        )
        token = task.get('taskToken', None)

        if token:
            return task.get('input'), token

        # No task
        return None, None

    def _success(self, token, result, notes):
        response = ActivityResponse(ActivityStatus.SUCCESS, result, notes=notes)
        self._swf.respond_activity_task_completed(taskToken=token, result=json.dumps(response.pack()))

    def _fail(self, token, e):
        error_message = str(e)

        response = ActivityResponse(
            e.response_code(),
            notes=e.notes,
            result=error_message,
            trace=e.trace(),
            reason=error_message
        )
        response_string = json.dumps(response.pack())

        if e.retry():
            self._swf.respond_activity_task_canceled(
                taskToken=token,
                details=response_string
            )
        else:
            self._swf.respond_activity_task_failed(
                taskToken=token,
                reason=error_message[:256],  # boto has a length constraint
                details=response_string
            )

    def _invalid(self, token, validation_errors):
        response = ActivityResponse(ActivityStatus.INVALID, validation_errors=validation_errors)
        self._swf.respond_activity_task_failed(
            taskToken=token,
            reason="{} validation error(s)".format(len(validation_errors)),
            details=json.dumps(response.pack())
        )

    def handle(self, token, event):
        if isinstance(event, str):
            event = json.loads(DataZipper.receive(event))

        if 'LOG_INPUT' in event:
            print(json.dumps(event, indent=4))

        if 'RETURN_SCHEMA' in event:
            return self._schema

        validation_error = self._validator.validate(event)
        if validation_error:
            return self._invalid(token, validation_error)

        try:
            kwargs = parse_event(event, self._params)
            result = self._handler(**kwargs)
            (valid_result, notes) = parse_result(result, self._result)
            self._success(token, valid_result, notes)
        except FulfillmentException as e:
            self._fail(token, e)
        except Exception as e:
            print("default!")
            wrapped = self._default_exception('unhandled exception', inner_exception=e)
            self._fail(token, wrapped)

    def run(self):
        event, token = self._poll()

        if token:
            self.handle(token, event)
            return token
