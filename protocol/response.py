
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
    def __init__(self, status, result=None, notes=None, trace=None, reason=None):
        self.status = status
        self.activity_result = result

        self.trace = trace or []
        self.notes = notes or []
        self.reason = reason

        # self.cache_key = None
        # self.cache_time = None
        # self.cache_expiration = None

        self.instance = None
        self.run_id = None
        self.workflow_id = None
        self.section_name = None

    # def addNote(note:String) = {
    #     notes += note
    # }
    #
    # def addTrace(line: String) = {
    #     trace += line
    # }
    #
    # def addTrace(exception: Exception) = {
    #     trace ++= StackTraceFormatter.format(exception.getStackTrace)
    # }

    def to_json(self):
        res = {}
        res["status"] = self.status

        if self.activity_result is not None:
            res["result"] = self.result()

        res["notes"] = self.notes
        res["trace"] = self.trace
        res["reason"] = self.reason

        # if(cacheKey.isDefined) {
        #     res("cache") = Json.obj(
        #         "key" -> cacheKey.get,
        #         "cached" -> cacheTime.get.toString,
        #         "expires" -> cacheExpiration.get.toString,
        #         "runId" -> Json.toJson(runId.getOrElse("--")),
        #         "workflowId" -> Json.toJson(workflowId.getOrElse("--")),
        #         "sectionName" -> Json.toJson(sectionName.getOrElse("--"))
        #     )
        # }

        if self.instance:
            res["instance"] = self.instance

        return res

    # def summary() = {
    #     notes.mkString("\n")+trace.mkString("\n", "\n", "")
    # }

    def serialize(self):
        return json.dumps(self.to_json())

    def result(self):
        if self.activity_result is not None:
            return self.activity_result.result() if isinstance(self.activity_result, ActivityResult) else self.activity_result
        raise Exception("Response has no Activity Result!")

    # def resultStringified:String = {
    #     Json.stringify(result)
    # }

    @classmethod
    def from_json(cls, obj):
        if type(obj) is not dict:
            raise Exception("Invalid Response Format! (not an obj was {})".format(type(obj)))

        if "status" not in obj:
            raise Exception("Invalid Response Format! (no status)")

        response = ActivityResponse(obj["status"])

        if "result" in obj:
            response.activity_result = ActivityResult(obj["result"])

        if "notes" in obj:
            response.notes.extend(obj["notes"])

        if "trace" in obj:
            response.trace.extend(obj["trace"])

        if "instance" in obj:
            response.instance = obj["instance"]

        # if(obj.value.contains("cache")) {
        #     val cache = obj.value("cache").as[JsObject]
        #     response.cacheKey = Some(cache.value("key").as[JsString].value)
        #     response.cacheTime = Some(new DateTime(cache.value("cached").as[JsString].value))
        #     response.cacheExpiration = Some(new DateTime(cache.value("expires").as[JsString].value))
        #     if(cache.value.contains("runId")) {
        #         response.runId = Some(cache.value("runId").as[JsString].value)
        #     }
        #     if(cache.value.contains("workflowId")) {
        #         response.workflowId = Some(cache.value("workflowId").as[JsString].value)
        #     }
        #     if(cache.value.contains("sectionName")) {
        #         response.sectionName = Some(cache.value("sectionName").as[JsString].value)
        #     }
        # }

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
