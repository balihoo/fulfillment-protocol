from timeline import Timeline
import exec_functions
import traceback
import signal
import sys

class TimeOut():
    def __init__(self, seconds):
        self.timeout = seconds
        self.goahead = True

    def __enter__(self):
        def h(s,f):
            raise Exception("TIMEOUT")

        try:
            self.oldh = signal.signal(signal.SIGALRM, h)
        except ValueError as e:
            self.goahead = False
            print("running without timeout")

        if self.goahead:
            signal.setitimer(signal.ITIMER_REAL, self.timeout)

    def __exit__(self, type, value, traceback):
        if self.goahead:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self.oldh)

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class Resolver(object):
    CODE_START = "<("

    @classmethod
    def _is_code(cls, s):
        return s.startswith(Resolver.CODE_START)

    @classmethod
    def contains_code(cls, s):
        t = type(s)
        if t in (str, unicode):
            return cls._is_code(s)
        if t == dict:
            return any([cls.contains_code(i) for i in s.itervalues()])
        if t in (tuple, list):
            return any([cls.contains_code(i) for i in s])
        return False

    def __init__(self, input, timeout_sec=5):
        self.timeout = timeout_sec
        self.input = input
        self.timeline = Timeline()
        self.record = None
        self.evaluation_context = {}
        self.evaluation_context.update(exec_functions.safe_builtins)
        self.evaluation_context.update(exec_functions.utils)
        self.needs_evaluation = self.contains_code(input)

        self.evaluated = not self.needs_evaluation
        self.result = input if self.evaluated else None
        self.resolvable = True
        self.resolved = not self.needs_evaluation
        self.code = None

    def _evaluate(self, e):
        self.result = self.__evaluate(e)
        self.resolved = True
        return self.result

    def __evaluate(self, e):
        if type(e) == dict:
            offending_keys = [k for k in e.keys() if k.startswith(Resolver.CODE_START)]
            if offending_keys:
                raise Exception("Operators like '{}' are NOT supported!".format(", ".join(offending_keys)))
            return {k: self.__evaluate(v) for k, v in e.iteritems()}
        elif type(e) in (tuple, list):
            if e and e[0] == Resolver.CODE_START:
                return self.__evaluate("\n".join(e))
            return [self.__evaluate(v) for v in e]
        elif type(e) in (str, unicode) and self._is_code(e):
            return self._evaluate_str(e)
        return e

    def _evaluate_str(self, s):
        return self.__execute(s[len(Resolver.CODE_START):], self.evaluation_context)

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

        self.code = wcode
        outside_vars.update(dict(__builtins__={}))

        try:
            with TimeOut(seconds=self.timeout):
                exec wcode in outside_vars, {exname: ReturnException}
        except ReturnException, e:
            return e.value
        except SyntaxError as err:
            error_class = err.__class__.__name__
            detail = "{} '{}'".format(err.args[0], err.text)
            line_number = "{}:{}".format(err.lineno, err.offset)
            msg = "{}(line {}) {}".format(error_class, line_number, detail)
            self.timeline.error(msg)
            self.resolvable = False

    def evaluate(self):
        if self.evaluated:
            return self.get_result()

        self.evaluated = True
        try:
            return self._evaluate(self.input)
        except Exception, err:
            error_class = err.__class__.__name__
            detail = err.args[0]
            cl, exc, tb = sys.exc_info()
            line_number = traceback.extract_tb(tb)[-1][1]
            msg = "Error in script: {}(line {}) {}".format(error_class, line_number, detail)
            self.timeline.error(msg)
            self.resolvable = False
        return None

    def get_result(self):
        return self.result if self.is_resolved() else None

    def is_resolved(self):
        return self.resolvable and self.resolved

    def is_resolvable(self):
        return self.resolvable

    def is_evaluated(self):
        return self.evaluated

    def to_json(self):
        return {
            "input": self.input,
            "result": self.get_result(),
            "resolvable": self.resolvable,
            "resolved": self.is_resolved(),
            "evaluated": self.evaluated,
            "needsEvaluation": self.needs_evaluation,
            "timeline": self.timeline.to_json(),
            "code": self.code
        }

    def last_msg(self):
        evts = self.timeline.events
        if evts and evts[-1].messages:
            return evts[-1].messages[0]

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
            if not self.resolver.is_resolved():
                self.value = self.resolver.evaluate()
                if not self.resolver.is_resolvable():
                    raise Exception("{} is not resolvable!".format(context))
                if not self.resolver.is_resolved():
                    raise Exception("{} is NOT resolved yet!".format(context))
                self.transform()
        return self.value

    def to_json(self, detailed=False):
        if detailed and self.resolver:
            return self.resolver.to_json()
        if self.resolver:
            if not self.resolver.is_resolved():
                try:
                    self.get('to_json')
                except: pass
        if hasattr(self.value, 'to_json'):
            return self.value.to_json(detailed)
        return self.value


class ResolverContainer(object):
    def __init__(self, context=None):
        self._items = {}
        self._context = context if context is not None else "-"
        self.timeline = Timeline()

    def add(self, key, value, resolver_class=Resolver, transform=None, skip_resolver=False):
        if Resolver.contains_code(value) and not skip_resolver:
            self._items[key] = ResolverWrapper(resolver_class(value), transform)
            return
        elif transform:
            # Transform immediately.. keep any non-none values..
            transformed = transform(value)
            if transformed is not None:
                self._items[key] = ResolverWrapper(transformed)
                return
        elif value is not None:
            self._items[key] = ResolverWrapper(value)

    def _build_context(self, c):
        return "{}/{}".format(self._context, c)

    def __contains__(self, name):
        return self._items.get(name, None) is not None

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __getattr__(self, name):
        if name in self._items:
            try:
                return self._items[name].get(self._build_context(name))
            except Exception, e:
                self.timeline.error("Resolver Error! {}".format(e.message))
        else:
            self.timeline.warning("Resolver container ({}) didn't have '{}'".format(self._context, name))
        return None

    def _resolvers(self):
        return {name: wrapper.resolver for (name, wrapper) in self._items.iteritems() if wrapper.resolver}

    def evaluate(self):
        for (name, item) in self._items.iteritems():
            try:
                item.get(self._build_context('{}(while evaluating)'.format(name)))
            except Exception, e:
                self.timeline.error("Resolver Error! {}".format(e.message))

    def all_resolved(self):
        return not len(self.unresolved())

    def unresolved(self):
        return [n for n, p in self._resolvers().iteritems() if not p.is_resolved()]

    def impossible(self):
        return [n for n, p in self._resolvers().iteritems() if not p.is_resolvable()]

    def to_json(self, detailed=False):
        return {name: v.to_json(detailed) for (name, v) in self._items.iteritems()}
