"""Simple in-process event bus used by HealthBand modules."""

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

EventPayload = dict[str, Any]
EventHandler = Callable[[EventPayload], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_name)
        if handlers is None:
            return
        if handler in handlers:
            handlers.remove(handler)
        if not handlers:
            self._handlers.pop(event_name, None)

    def publish(self, event_name: str, payload: EventPayload) -> None:
        handlers = tuple(self._handlers.get(event_name, ()))
        for handler in handlers:
            try:
                handler(payload)
            except Exception:
                logger.exception("Unhandled error in event handler for event '%s'.", event_name)
