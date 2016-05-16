import json


class Timeline(object):
    def __init__(self):
        self.events = []

    def error(self, message, when=None):
        self._add(TimelineEvent(TimelineEventType.ERROR, message, when))

    def warning(self, message, when=None):
        self._add(TimelineEvent(TimelineEventType.WARNING, message, when))

    def note(self, message, when=None):
        self._add(TimelineEvent(TimelineEventType.NOTE, message, when))

    def success(self, message, when=None):
        self._add(TimelineEvent(TimelineEventType.SUCCESS, message, when))

    def _add(self, event):
        if self.events and self.events[-1] == event:
            return None
        self.events.append(event)

    def to_json(self):
        return [entry.to_json() for entry in self.events]

    def __str__(self):
        return json.dumps(self.to_json)


class TimelineEventType(object):
    NOTE = "NOTE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class TimelineEvent(object):
    def __init__(self, event_type, messages, when=None):
        self.event_type = event_type
        self.messages = messages
        self.when = when

    def to_json(self):
        return {
            "eventType": self.event_type,
            "messages": self.messages,
            "when": self.when.isoformat() if self.when else "--"
        }

    def __cmp__(self, other):
        return self.messages == other.messages