from resolver import Resolver, ResolverContainer

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

    def simple(self):
        return self.jsonType not in ('array', 'object')

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
            raise Exception("Every Schema MUST have a jsonType! ='{}'".format(self.jsonType))

    def to_schema(self, include_version=False):
        self._schema['type'] = self._get_type()
        schema = self._schema.copy()
        if include_version:
            schema['$schema'] = "http://json-schema.org/draft-04/schema"
        return schema

    def parse(self, value, context=""):
        if value is not None:
            if type(value) in (str, ):
                value = unicode(value, 'utf-8')
            try:
                return self._parse(value, context)
            except Exception, e:
                raise Exception("Exception while parsing {}: {}".format(context, e))
        if not self.is_required():
            try:
                return self._parse(self.default, context+"/-default-/") if self.default is not None else self.default
            except Exception, e:
                raise Exception("Exception while parsing {}: {}".format(context+"/-default-/", e))
        raise Exception("{}-Missing required parameter (description: {})".format(context, self.description[:40]))

    def _parse(self, value, context):
        return value

class StringParameter(SchemaParameter):
    def __init__(self, description, pattern=None, min_length=None, max_length=None, **kwargs):
        add_schema = {}
        if pattern:
            add_schema['pattern'] = pattern
        if max_length:
            add_schema['maxLength'] = int(max_length)
        if min_length:
            add_schema['minLength'] = int(min_length)
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)

    def _parse(self, value, context=""):
        return value.strip()

class EnumParameter(SchemaParameter):
    def __init__(self, description, options, **kwargs):
        SchemaParameter.__init__(self, description, more_schema={'enum': options}, **kwargs)
        self.options = options

    def _parse(self, value, context=""):
        v = value.strip()
        if v not in self.options:
            raise Exception("{} is not a valid value for Enum!".format(v))
        return v

class BooleanParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        SchemaParameter.__init__(self, description, **kwargs)
        self.jsonType = "boolean"

    def _parse(self, value, context=""):
        if type(value) != bool:
            raise Exception("Expected to parse a bool!")
        return bool(value)

class UriParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        add_schema = {
            'format': "uri",
            'minLength': 1
        }
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)

    def _parse(self, value, context=""):
        return value.strip()

class UuidParameter(StringParameter):
    def __init__(self, description, **kwargs):
        pattern = r"^[0-9A-Fa-f]{8}-([0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}$"
        StringParameter.__init__(self, description, pattern=pattern, **kwargs)

class ObjectParameter(SchemaParameter):
    def __init__(self, description, properties, **kwargs):
        add_schema = {
            'properties': {name: properties[name].to_schema() for name in properties},
            'required': [name for name in properties if properties[name].is_required()]
        }
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.properties = properties
        self.jsonType = "object"

    def _parse(self, value, context=""):
        if type(value) != dict:
            raise Exception("Expected to parse a dict!")
        out = {}
        for name, prop in self.properties.iteritems():
            v = prop.parse(value.get(name, None), context+"[{}]".format(name))
            if v is not None:
                out[name] = v
        return out

class ResolverObjectParameter(ObjectParameter):
    def __init__(self, context, description, properties, resolver_class=Resolver, extra_type=None, **kwargs):
        self.extra_type = extra_type
        self.resolver_class = resolver_class
        self._context = context
        ObjectParameter.__init__(self, description, properties, **kwargs)

    def _parse(self, value, context=""):

        def wrap_parser(prop, name):
            scontext = "{}/{}[{}]".format(self._context, context, name)

            def f(v):
                return prop.parse(v, scontext)
            return f

        out = ResolverContainer(self._context)
        for name, prop in self.properties.iteritems():
            out.add(name, value.get(name, None), self.resolver_class, wrap_parser(prop, name),
                    skip_resolver=type(prop) == ResolverObjectParameter)
        if self.extra_type:
            for name, val in value.iteritems():
                if name not in out:
                    out.add(name, val, self.resolver_class, wrap_parser(self.extra_type, name),
                            skip_resolver=type(self.extra_type) == ResolverObjectParameter)
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

    def _parse(self, value, context=""):
        if type(value) != dict:
            raise Exception("Expected to parse a dict!")
        out = {}
        for name in value:
            out[name] = self.value_type.parse(value[name], context+"[{}]".format(name))
        return out

class StringMapParameter(SchemaParameter):
    def __init__(self, description, **kwargs):
        self.value_type = StringParameter("Value")
        add_schema = {
            'additionalProperties': {
                'type': 'string',
                'description': "string values"
            }
        }

        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.jsonType = "object"

    def _parse(self, value, context=""):
        if type(value) != dict:
            raise Exception("Expected to parse a dict!")
        return value


class ArrayParameter(SchemaParameter):
    def __init__(self, description, element, min_items=0, max_items=None, unique=False, **kwargs):
        add_schema = {'items': element.to_schema()}
        if min_items > 0:
            add_schema["minItems"] = min_items
        if max_items:
            add_schema["maxItems"] = max_items
        if unique:
            add_schema["uniqueItems"] = unique

        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.element = element
        self.jsonType = "array"

    def _parse(self, value, context=""):
        if type(value) not in (list, tuple):
            raise Exception("Expected to parse a list or tuple!")
        return [self.element.parse(v, context + "[{}/{}]".format(i, len(value))) for i, v in enumerate(value)]

class FloatParameter(SchemaParameter):
    def __init__(self, description, minimum=None, maximum=None, **kwargs):
        add_schema = {}
        if minimum:
            add_schema["minimum"] = float(minimum)
        if maximum:
            add_schema["maximum"] = float(maximum)
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.jsonType = "number"

    def _parse(self, value, context=""):
        return float(value)

class IntParameter(SchemaParameter):
    def __init__(self, description, minimum=None, maximum=None, **kwargs):
        add_schema = {}
        if minimum:
            add_schema["minimum"] = int(minimum)
        if maximum:
            add_schema["maximum"] = int(maximum)
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.jsonType = "integer"

    def _parse(self, value, context=""):
        return int(value)

class IsoDateParameter(StringParameter):
    def __init__(self, description, **kwargs):
        StringParameter.__init__(self, description, **kwargs)

class NaiveIsoDateParameter(StringParameter):
    def __init__(self, description, **kwargs):
        pattern = r"^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6]))))$"
        StringParameter.__init__(self, description, **kwargs)

class LocalIsoDateTimeParameter(StringParameter):
    def __init__(self, description, **kwargs):
        pattern = r"^([\+-]?\d{4}(?!\d{2}\b))((-?)((0[1-9]|1[0-2])(\3([12]\d|0[1-9]|3[01]))?|W([0-4]\d|5[0-2])(-?[1-7])?|(00[1-9]|0[1-9]\d|[12]\d{2}|3([0-5]\d|6[1-6])))([T\s]((([01]\d|2[0-3])((:?)[0-5]\d)?|24\:?00)([\.,]\d+(?!:))?)?(\17[0-5]\d([\.,]\d+)?)))$"
        StringParameter.__init__(self, description, pattern=pattern, **kwargs)

class OneOfParameter(SchemaParameter):
    def __init__(self, description, options, **kwargs):
        self.options = options
        add_schema = {
            "oneOf": [o.to_schema() for o in options]
        }
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.jsonType = [o.jsonType for o in options]

    def _parse(self, value, context):
        if value is not None:
            for option in self.options:
                try:
                    val = option.parse(value, context+":OneOf:")
                    if val is not None:
                        return val
                except Exception, e:
                    # print("While parsing OneOf. {}:{}".format(e.message, option.description))
                    pass
        return False

class AnyOfParameter(SchemaParameter):
    def __init__(self, description, options, **kwargs):
        self.options = options
        add_schema = {
            "anyOf": [o.to_schema() for o in options]
        }
        SchemaParameter.__init__(self, description, more_schema=add_schema, **kwargs)
        self.jsonType = [o.jsonType for o in options]

    def _parse(self, value, context):
        if value is not None:
            for option in self.options:
                try:
                    val = option.parse(value, context+":AnyOf:")
                    if val is not None:
                        return val
                except Exception, e:
                    # print("While parsing AnyOf. {}:{}".format(e.message, option.description))
                    pass
        return False

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

class UuidResult(UuidParameter):
    def __init__(self, description, **kwargs):
        UuidParameter.__init__(self, description, **kwargs)
