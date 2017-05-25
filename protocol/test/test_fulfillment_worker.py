#!/usr/bin/python
import json
import unittest
from unittest.mock import Mock, MagicMock

from fulfillment_worker import FulfillmentWorker
from schema import StringParameter, StringResult
from fulfillment_exception import FulfillmentFatalException
from response import ActivityStatus

REGION = 'us-east-1'
SWF_DOMAIN = 'fulfillment_test'
ACTIVITY_NAME = 'test'
ACTIVITY_VERSION = '1'
TASK_LIST = {'name': ACTIVITY_NAME + ACTIVITY_VERSION}
TASK_TOKEN = 'SOMETASKTOKEN'
INPUT = {
    'stuff': 'things'
}
TASK = {
    'taskToken': TASK_TOKEN,
    'input': json.dumps(INPUT)
}
RESULT = 'some result'
ERROR_MESSAGE = 'loud noises!'


class TestFulfillmentWorker(unittest.TestCase):
    def test_no_task(self):
        worker = FulfillmentWorker(
            description='This is a test worker',
            parameters={
                'stuff': StringParameter('some stuff')
            },
            result=StringResult('the result'),
            handler=Mock(),
            region=REGION,
            activity_name=ACTIVITY_NAME,
            activity_version=ACTIVITY_VERSION,
            swf_domain=SWF_DOMAIN
        )
        worker._swf.poll_for_activity_task = MagicMock(return_value={})

        task_token = worker.run()

        self.assertIsNone(task_token)
        worker._swf.poll_for_activity_task.assert_called_with(domain=SWF_DOMAIN, taskList=TASK_LIST)
        worker._handler.assert_not_called()

    def test_success(self):
        worker = FulfillmentWorker(
            description='This is a test worker',
            parameters={
                'stuff': StringParameter('some stuff')
            },
            result=StringResult('the result'),
            handler=Mock(return_value=RESULT),
            region=REGION,
            activity_name=ACTIVITY_NAME,
            activity_version=ACTIVITY_VERSION,
            swf_domain=SWF_DOMAIN
        )
        worker._swf.poll_for_activity_task = MagicMock(return_value=TASK)
        worker._swf.respond_activity_task_completed = MagicMock()

        task_token = worker.run()

        expected = {
            'taskToken': TASK_TOKEN,
            'result': {
                'status': ActivityStatus.SUCCESS,
                'notes': [],
                'reason': None,
                'result': RESULT,
                'trace': []
            }
        }

        self.assertEqual(task_token, TASK_TOKEN)
        worker._swf.poll_for_activity_task.assert_called_once_with(domain=SWF_DOMAIN, taskList=TASK_LIST)
        worker._handler.assert_called_once_with(stuff=INPUT['stuff'])
        worker._swf.respond_activity_task_completed.assert_called_once()
        call_args = worker._swf.respond_activity_task_completed.call_args[1]
        call_args['result'] = json.loads(call_args['result'])
        self.assertEqual(call_args, expected)

    def test_fatal_error(self):
        error = FulfillmentFatalException(message=ERROR_MESSAGE)

        worker = FulfillmentWorker(
            description='This is a test worker',
            parameters={
                'stuff': StringParameter('some stuff')
            },
            result=StringResult('the result'),
            handler=Mock(side_effect=error),
            region=REGION,
            activity_name=ACTIVITY_NAME,
            activity_version=ACTIVITY_VERSION,
            swf_domain=SWF_DOMAIN
        )
        worker._swf.poll_for_activity_task = MagicMock(return_value=TASK)
        worker._swf.respond_activity_task_failed = MagicMock()

        task_token = worker.run()

        expected = {
            'taskToken': TASK_TOKEN,
            'details': {
                'status': ActivityStatus.FATAL,
                'notes': [],
                'reason': ERROR_MESSAGE,
                'result': ERROR_MESSAGE,
                'trace': error.trace()
            }
        }

        self.assertEqual(task_token, TASK_TOKEN)
        worker._swf.respond_activity_task_failed.assert_called_once()
        call_args = worker._swf.respond_activity_task_failed.call_args[1]
        call_args['details'] = json.loads(call_args['details'])
        self.assertEqual(call_args, expected)

    def test_default_error(self):
        error = Exception(ERROR_MESSAGE)

        worker = FulfillmentWorker(
            description='This is a test worker',
            parameters={
                'stuff': StringParameter('some stuff')
            },
            result=StringResult('the result'),
            handler=Mock(side_effect=error),
            region=REGION,
            activity_name=ACTIVITY_NAME,
            activity_version=ACTIVITY_VERSION,
            swf_domain=SWF_DOMAIN,
            default_exception=FulfillmentFatalException
        )
        worker._swf.poll_for_activity_task = MagicMock(return_value=TASK)
        worker._fail = MagicMock()

        task_token = worker.run()

        self.assertEqual(task_token, TASK_TOKEN)
        worker._fail.assert_called_once()
        call_args = worker._fail.call_args[0]
        self.assertEqual(call_args[0], TASK_TOKEN)
        self.assertIsInstance(call_args[1], FulfillmentFatalException)
        
    def test_validation_error(self):
        error = Exception(ERROR_MESSAGE)

        worker = FulfillmentWorker(
            description='This is a test worker',
            parameters={
                'stuff': StringParameter('some stuff')
            },
            result=StringResult('the result'),
            handler=Mock(side_effect=error),
            region=REGION,
            activity_name=ACTIVITY_NAME,
            activity_version=ACTIVITY_VERSION,
            swf_domain=SWF_DOMAIN
        )
        worker._swf.poll_for_activity_task = MagicMock(return_value={
            'taskToken': TASK_TOKEN,
            'input':  '{"stuff": 1}'
        })

        worker._swf.respond_activity_task_failed = MagicMock()

        task_token = worker.run()

        expected = {
            'taskToken': TASK_TOKEN,
            'details': json.dumps({
                "status": ActivityStatus.INVALID,
                "notes": [],
                "trace": [],
                "reason": None,
                "validation_errors": [
                    {
                        "cause": None,
                        "context": [],
                        "message": "1 is not of type 'string'",
                        "path": "stuff",
                        "relative_path": "stuff",
                        "absolute_path": "stuff",
                        "validator": "type",
                        "validator_value": "string"
                    }
                ]
            })
        }

        self.assertEqual(task_token, TASK_TOKEN)
        call_args = worker._swf.respond_activity_task_failed.call_args[1]
        self.assertEqual(call_args, expected)

if __name__ == '__main__':
    unittest.main()
