
from timeline import Timeline


class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


class Resolver(object):

    @classmethod
    def is_code(cls, s):
        return str(s).startswith("<(")

    @classmethod
    def contains_code(cls, s):
        if type(s) == dict:
            return any([cls.contains_code(i) for i in s.itervalues()])
        if type(s) in (tuple, list):
            return any([cls.contains_code(i) for i in s])
        return cls.is_code(s)

    def __init__(self, input):
        self.input = input
        self.timeline = Timeline()
        self.record = None
        self.evaluation_context = {}
        self.needs_evaluation = self.contains_code(input)

        self.evaluated = not self.needs_evaluation
        self.result = input if self.evaluated else None
        self.resolvable = True

    def _evaluate(self, e):
        if type(e) == dict:
            return {k: self._evaluate(v) for k, v in e.iteritems()}
        elif type(e) in (tuple, list):
            return (self._evaluate(v) for v in e)
        elif type(e) in (str, unicode) and e.startswith("<("):
            return self._evaluate_str(e)
        else:
            return e

    def _evaluate_str(self, s):
        return self.__execute(s[2:], self.evaluation_context)

    def __wrap_code(self, code, indentation=4):
        # Sneak a return in here for single statement
        if "return" not in code and "\n" not in code:
            code = "return {}".format(code)

        exname = 'exec_return'
        fname = 'resolver_func'
        indent = ' ' * indentation
        wrapped_code = "def {}():\n{}".format(fname, indent)
        wrapped_code += code.strip().replace("\n", "\n{}".format(indent)).strip()
        wrapped_code += "\nraise {}({}())".format(exname, fname)
        return wrapped_code, exname

    def __execute(self, code, outside_vars):
        wcode, exname = self.__wrap_code(code)
        # print(wcode)
        try:
            exec wcode in outside_vars, {exname: ReturnException}
        except ReturnException, e:
            return e.value

    def evaluate(self):
        if self.evaluated:
            return False

        self.evaluated = True

        try:
            self.result = self._evaluate(self.input)
            return True
        except Exception, e:
            self.timeline.error("Unexpected Exception! {}".format(e.message))
            self.resolvable = False
        return False

    def get_result(self):
        return self.result

    def is_resolved(self):
        return self.result is not None

    def is_resolvable(self):
        return self.resolvable

    def is_evaluated(self):
        return self.evaluated

    def to_json(self):
        return {
            "input": self.input,
            "result": self.result,
            "resolvable": self.resolvable,
            "resolved": self.result is not None,
            "evaluated": self.evaluated,
            "needsEvaluation": self.needs_evaluation,
            "timeline": self.timeline.to_json()
        }


class ResolverWrapper(object):
    def __init__(self, value, transform=None):
        self.resolver = value if isinstance(value, Resolver) else None
        self.value = value if not self.resolver else None
        self._transform = transform
        if not self.resolver:
            self.transform()

    def transform(self):
        if self._transform:
            self.value = self._transform(self.value)

    def get(self, context):
        if self.resolver:
            if self.resolver.evaluate() and self.resolver.is_resolved():
                self.value = self.resolver.get_result()
                self.transform()
            if not self.resolver.is_resolvable():
                raise Exception("Never gonna work! {}".format(context))
            if not self.resolver.is_resolved():
                raise Exception("Not resolved yet! {}".format(context))

        return self.value

    def to_json(self, detailed=False):
        if detailed and self.resolver:
            return self.resolver.to_json()
        if hasattr(self.value, 'to_json'):
            return self.value.to_json(detailed)
        return self.value


class ResolverContainer(object):
    def __init__(self):
        self._items = {}

    def add(self, key, value, resolver_class=Resolver, transform=None, skip_resolver=False):
        self._items[key] = ResolverWrapper(resolver_class(value) if Resolver.contains_code(value) and not skip_resolver else value, transform)

    def __contains__(self, name):
        if name not in self._items:
            return False
        v = self.__getattr__(name)
        return v is not None

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __getattr__(self, name):
        if name in self._items:
            return self._items[name].get(name)
        print("Resolver container didn't have '{}'".format(name))
        return None

    def _resolvers(self):
        return {name: wrapper.resolver for (name, wrapper) in self._items.iteritems() if wrapper.resolver}

    def evaluate(self):
        return [resolver.evaluate() for resolver in self._resolvers().itervalues()]

    def all_resolved(self):
        return not len(self.unresolved())

    def unresolved(self):
        return [n for n, p in self._resolvers().iteritems() if not p.is_resolved()]

    def impossible(self):
        return [n for n, p in self._resolvers().iteritems() if not p.is_resolvable()]

    def to_json(self, detailed=False):
        return {name: v.to_json(detailed) for (name, v) in self._items.iteritems()}
