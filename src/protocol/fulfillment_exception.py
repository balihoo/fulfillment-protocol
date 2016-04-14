import traceback
import sys

class FulfillmentException(Exception):
    response_code = None
    def __init__(self, message, inner_exception=None, notes=None):
        self.notes = notes
        if inner_exception is not None:
            #this is the trace of the inner exception
            exparms = sys.exc_info()
            self._trace = traceback.format_exception(*exparms)
            message += ": " + inner_exception.message
        else:
            self._trace = []
        super(FulfillmentException, self).__init__(message)

    def trace(self):
        # this is the trace from where this exception was thrown
        exparms = sys.exc_info()
        trace = traceback.format_exception(*exparms)
        # return them concatenated, most recent last
        return self._trace + trace

class FulfillmentValidationException(FulfillmentException):
    """ Failure: A retry without fixing the input will not work """
    response_code = "INVALID"

class FulfillmentFatalException(FulfillmentException):
    """ Failure: A retry with the current input will not work """
    response_code = "FATAL"

class FulfillmentFailedException(FulfillmentException):
    """ Cancel: A retry might work """
    response_code = "FAILED"

class FulfillmentErrorException(FulfillmentException):
    """ Cancel: An error was encountered, retry might work """
    response_code = "ERROR"

class FulfillmentDeferException(FulfillmentException):
    """ Cancel: Result not yet available, retry """
    response_code = "DEFER"
