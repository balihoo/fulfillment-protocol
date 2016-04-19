
class FunctionParams(object):
    def __init__(self, event):
        self._values = event

    def __contains__(self, i):
        return i in self._values

    def __getitem__(self, i):
        item = self._values[i]
        if isinstance(item, str):
            return item.strip()
        return item

    def __setitem__(self, i, val):
        self._values[i] = val
        return val

    def get(self, i, default):
        if i in self._values:
            return self[i]
        return default

