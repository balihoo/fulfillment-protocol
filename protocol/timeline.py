import json
import arrow


class Timeline(object):
    default_when = None

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
        return json.dumps(self.to_json())

    def __len__(self):
        return len(self.events)


class TimelineEventType(object):
    NOTE = "NOTE"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class TimelineEvent(object):
    def __init__(self, event_type, messages, when=None):
        self.event_type = event_type
        self.messages = messages if type(messages) in (list, tuple) else [messages]
        self.when = when or Timeline.default_when

    def to_json(self):
        return {
            "eventType": self.event_type,
            "messages": self.messages,
            "when": self.when.isoformat() if self.when else "--",
            "now": arrow.utcnow().isoformat()
        }

    def __repr__(self):
        return "{} {} {}".format(self.event_type, "\n\t".join(self.messages), self.when)

    def __eq__(self, other):
        return self.messages == other.messages
