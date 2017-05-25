from jsonschema import Draft4Validator
from .schema import ObjectParameter


class ParamValidator(object):
    def __init__(self, parameters):
        self._validator = Draft4Validator(ObjectParameter('', properties=parameters).to_schema(True))

    def validate(self, event):
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

        return validation_errors
