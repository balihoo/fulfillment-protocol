#!/usr/bin/python

class SchemaParameter(object):
    def __init__(self, description, required=True, default=None, more_schema=None):
        self.description = description
        self.required = required if default is None else False
        self.jsonType = "string"
        self.default = default
        if self.required and default is not None:
            raise Exception("Required parameters can't have default values!")
        self._schema = {
            'type': "--",
            'description': self.description
        }
        if self.default is not None:
            self._schema['default'] = self.default
        if more_schema is not None:
            self._schema.update(more_schema)

    def is_required(self):
        return self.required

    def _get_type(self):
        if self.required:
            return self.jsonType
        elif isinstance(self.jsonType, list):
            return ["null"] + self.jsonType
        elif self.jsonType:
            return ["null", self.jsonType]
        else:
            raise Exception("BLARGH!")

    def to_schema(self, include_version=False):
        self._schema['type'] = self._get_type()
        schema = self._schema.copy()
        if include_version:
            schema['$schema'] = "http://json-schema.org/draft-04/schema"
        return schema

    def parse(self, value):
        if value is not None:
            return self._parse(value)
        if not self.is_required():
            return self.default
        raise Exception("Missing required parameter: {}".format(self.description))

    def _parse(self, value):
        return value

class StringParameter(SchemaParameter):
    def __init__(self, description, pattern=None, **kwargs):
        add_schema = {}
        if pattern:
            add_schema['pattern'] = pattern
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)

    def _parse(self, value):
        return value.strip()

class EnumParameter(SchemaParameter):
    def __init__(self, description, options, **kwargs):
        SchemaParameter.__init__(self, description, more_schema={'enum': options}, **kwargs)
        self.options = options

    def _parse(self, value):
        v = value.strip()
        if v not in self.options:
            raise Exception("{} is not a valid value for Enum!".format(v))
        return v

class BooleanParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        SchemaParameter.__init__(self, description, **kwargs)
        self.jsonType = "boolean"

    def _parse(self, value):
        return bool(value)

class UriParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        add_schema = {
            'format': "uri",
            'minLength': 1
        }
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)

    def _parse(self, value):
        return value.strip()

class ObjectParameter(SchemaParameter):
    def __init__(self, description, properties, **kwargs):
        add_schema = {
            'properties': {name: properties[name].to_schema() for name in properties},
            'required': [name for name in properties if properties[name].is_required()]
        }
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.properties = properties
        self.jsonType = "object"

    def _parse(self, value):
        out = {}
        for name, prop in self.properties.iteritems():
            if name in value:
                out[name] = prop.parse(value[name])
        return out

class LooseObjectParameter(SchemaParameter):
    def __init__(self, description, value_type, key_regex='.+', **kwargs):
        add_schema = {
            'minProperties': 1,
            'patternProperties': {
                key_regex: value_type.to_schema()
            },
            'additionalProperties': False
        }
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.value_type = value_type
        self.jsonType = "object"

    def _parse(self, value):
        out = {}
        for name in value:
            out[name] = self.value_type.parse(value[name])
        return out

class ArrayParameter(SchemaParameter):
    def __init__(self, description, element, min_items=0, max_items=None, unique=False, **kwargs):
        add_schema = { 'items': element.to_schema() }
        if min_items > 0:
            add_schema["minItems"] = min_items
        if max_items:
            add_schema["maxItems"] = max_items
        if unique:
            add_schema["uniqueItems"] = unique

        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.element = element
        self.jsonType = "array"

    def _parse(self, value):
        return [self.element.parse(v) for v in value]

class FloatParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        SchemaParameter.__init__(self, description, **kwargs)
        self.jsonType = "number"

    def _parse(self, value):
        return float(value)

class IntParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        SchemaParameter.__init__(self, description, **kwargs)
        self.jsonType = "integer"

    def _parse(self, value):
        return int(value)

class IsoDateParameter(StringParameter):
    def __init__(self, description, **kwargs):
        StringParameter.__init__(self, description, **kwargs)

class NaiveIsoDateParameter(StringParameter):
    def __init__(self, description, **kwargs):
        StringParameter.__init__(self, description, **kwargs)


class JsonParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        SchemaParameter.__init__(self, description, **kwargs)
        self.jsonType = ["array", "boolean", "integer", "number", "object", "string"]

class SchemaResult(SchemaParameter):
    def __init__(self, description, **kwargs):
        SchemaParameter.__init__(self, description, **kwargs)

class StringResult(StringParameter):
    def __init__(self, description, **kwargs):
        StringParameter.__init__(self, description, **kwargs)

class ObjectResult(ObjectParameter):
    def __init__(self, description, **kwargs):
        ObjectParameter.__init__(self, description, **kwargs)

class ArrayResult(ArrayParameter):
    def __init__(self, description, **kwargs):
        ArrayParameter.__init__(self, description, **kwargs)

class FloatResult(FloatParameter):
    def __init__(self, description, **kwargs):
        FloatParameter.__init__(self, description, **kwargs)

class IntResult(IntParameter):
    def __init__(self, description, **kwargs):
        IntParameter.__init__(self, description, **kwargs)

class IsoDateResult(IsoDateParameter):
    def __init__(self, description, **kwargs):
        IsoDateParameter.__init__(self, description, **kwargs)

class LooseObjectResult(LooseObjectParameter):
    def __init__(self, description, **kwargs):
        LooseObjectParameter.__init__(self, description, **kwargs)

class JsonResult(JsonParameter):
    def __init__(self, description, **kwargs):
        JsonParameter.__init__(self, description, **kwargs)

class UriResult(UriParameter):
    def __init__(self, description, **kwargs):
        UriParameter.__init__(self, description, **kwargs)
