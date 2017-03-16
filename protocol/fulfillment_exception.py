import traceback
import sys

class FulfillmentException(Exception):
    def __init__(self, message, inner_exception=None, notes=None):
        self.notes = notes
        if inner_exception is not None:
            #this is the trace of the inner exception
            exparms = sys.exc_info()
            self._trace = traceback.format_exception(*exparms)
            message = "{}: {}".format(message, inner_exception.message)
        else:
            self._trace = []
        super(FulfillmentException, self).__init__(message)

    def trace(self):
        if not self._trace:
            # this is the trace from where this exception was thrown
            exparms = sys.exc_info()
            self._trace = traceback.format_exception(*exparms)
        return self._trace

    def response_code(self):
        raise Exception("Response Code Not Implemented!")

class FulfillmentValidationException(FulfillmentException):
    """ Failure: A retry without fixing the input will not work """
    def response_code(self):
        return "INVALID"

class FulfillmentFatalException(FulfillmentException):
    """ Failure: A retry with the current input will not work """
    def response_code(self):
        return "FATAL"

class FulfillmentFailedException(FulfillmentException):
    """ Cancel: A retry might work """
    def response_code(self):
        return "FAILED"

class FulfillmentErrorException(FulfillmentException):
    """ Cancel: An error was encountered, retry might work """
    def response_code(self):
        return "ERROR"

class FulfillmentDeferException(FulfillmentException):
    """ Cancel: Result not yet available, retry """
    def response_code(self):
        return "DEFER"
