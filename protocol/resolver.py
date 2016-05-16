
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
        elif type(e) == str and e.startswith("<("):
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
            return

        self.evaluated = True

        try:
            self.result = self._evaluate(self.input)
        except Exception, e:
            self.timeline.error("Unexpected Exception! {}".format(e.message))
            self.resolvable = False

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
        self.value = value
        self.transform = transform

    def get(self, context):
        if type(self.value) == Resolver:
            self.value.evaluate()
            if not self.value.is_resolvable():
                raise Exception("Never gonna work! {}".format(context))
            if not self.value.is_resolved():
                raise Exception("Not resolved yet! {}".format(context))
            self.value = self.value.get_result()

        if self.transform:
            return self.transform(self.value)
        else:
            return self.value


class ResolverContainer(object):
    def __init__(self):
        self._items = {}

    def add(self, key, value, resolver_class=Resolver, transform = None):
        self._items[key] = ResolverWrapper(resolver_class(value) if Resolver.contains_code(value) else value, transform)

    def __contains__(self, name):
        v = self.__getattr__(name)
        return v is not None

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __getattr__(self, name):
        if name in self._items:
            return self._items[name].get(name)
        return None
        # else:
        #     raise Exception("Container has no '{}'!".format(name))
