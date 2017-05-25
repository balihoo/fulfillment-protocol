import re

from fulfillment_exception import (
    FulfillmentValidationException
)

param_rex = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def parse_event(event, params):
    kwargs = {}
    for (name, param) in params.items():
        try:
            value = event[name] if name in event else None
            # http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case
            param_name = param_rex.sub(r'_\1', name.replace(' ', '_')).lower()
            kwargs[param_name] = param.parse(value, name)
        except Exception as e:
            msg = "Error parsing parameter '{}'".format(name)
            raise FulfillmentValidationException(msg, inner_exception=e)
    return kwargs


def parse_result(result, result_schema):
    if isinstance(result, tuple):
        (res, notes) = result
        return result_schema.parse(res, 'Parsing result:'), notes
    else:
        return result_schema.parse(result, 'Parsing result:'), []
