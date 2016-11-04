
import json


#
# The statuses fall into SWF ActivityTask categories of Complete, Fail, Cancel.
#
class ActivityStatus(object):
    # Complete
    SUCCESS = "SUCCESS"

    # Fail
    INVALID = "INVALID"  # A retry without fixing the input will not work
    FATAL = "FATAL"  # A retry with the current input will not work

    # Cancel
    FAILED = "FAILED"  # A retry might work
    ERROR = "ERROR"  # An error was encountered, retry might work
    DEFER = "DEFER"  # Result not yet available, retry

    # Special status for cached results
    CACHED_RESULT_PENDING = "CACHED_RESULT_PENDING"

    # -- uncategorized --
    UNKNOWN = "UNKNOWN"


#
# This is a compound response object that can return the results of a task
# along with notable information about the processing of that task. It also
# can deliver a stack trace and notes about errors that occur in the case of task
# failure.
#
# @param status SUCCESS.. etc
# @param result the result of the task.. will not always be present
#
class ActivityResponse(object):
    def __init__(self, status, result=None, notes=None, trace=None, reason=None, validation_errors=None):
        self.status = status
        self.activity_result = result

        self.trace = trace or []
        self.notes = notes or []
        self.reason = reason

        self.cache_key = None
        self.cache_time = None
        self.cache_expiration = None

        self.instance = None
        self.run_id = None
        self.workflow_id = None
        self.section_name = None

        self.validation_errors = validation_errors

    def to_json(self):
        res = {}
        res["status"] = self.status

        if self.activity_result is not None:
            res["result"] = self.result()

        res["notes"] = self.notes
        res["trace"] = self.trace
        res["reason"] = self.reason

        if self.cache_key:
            res["cache"] = {
                "key": self.cache_key,
                "cached": str(self.cache_time),
                "expires": str(self.cache_expiration),
                "runId": self.run_id,
                "workflowId": self.workflow_id,
                "sectionName": self.section_name
            }

        if self.instance:
            res["instance"] = self.instance

        if self.validation_errors:
            res["validation_errors"] = self.validation_errors

        return res

    def serialize(self):
        return json.dumps(self.to_json())

    def result(self):
        if self.activity_result is not None:
            return self.activity_result.result() if isinstance(self.activity_result, ActivityResult) else self.activity_result
        raise Exception("Response has no Activity Result!")

    @classmethod
    def from_json(cls, obj):
        if type(obj) is not dict:
            raise Exception("Invalid Response Format! (not an obj was {})".format(type(obj)))

        if "status" not in obj:
            raise Exception("Invalid Response Format! (no status)")

        response = ActivityResponse(obj["status"])

        if "result" in obj:
            response.activity_result = ActivityResult(obj["result"])

        response.notes.extend(obj.get("notes", []))

        response.trace.extend(obj.get("trace", []))

        response.instance = obj.get("instance", None)

        response.validation_errors = obj.get("validation_errors", None)

        if "cache" in obj:
            cache = obj["cache"]
            response.cache_key = cache["key"]
            response.cache_time = cache["cached"]
            response.cache_expiration = cache["expires"]
            response.run_id = cache.get("runId", None)
            response.workflow_id = cache.get("workflowId", None)
            response.section_name = cache.get("sectionName", None)

        return response

    @classmethod
    def parse_result(cls, result):
        try:
            # We expect results to come back as legal JSON...
            return json.loads(result)
        except Exception, e:
            # Wasn't json encoded, it's automatically a JSON string..
            print "parse_result failed!", e.message, result
            return result


class ActivityResult(object):
    def __init__(self, result):
        self._result = result

    def result(self):
        return self._result


class EncryptedResult(ActivityResult):
    def __init__(self, eresult):
        ActivityResult.__init__(self, eresult)
        # extends ActivityResult(JsString(eresult)) {
        # val crypter = new Crypter("config/crypto")

    def result(self):
        print "IMPLEMENT DECRYPTION!!"
        return self._result
