"""ServiceBus — lightweight synchronous publish/subscribe broker.

Design
------
- In-process only; no network, no threads, no persistence.
- A subscriber is any callable that accepts a single ``Event``.
- Subscribers are registered per topic prefix; ``review.*`` matches
  ``review.started``, ``review.completed``, etc.
- Publishing is fire-and-forget: exceptions in subscribers are logged
  and swallowed so a bad listener never breaks the publishing caller.
- The module exposes a single shared ``bus`` instance.  Tests can
  construct their own ``ServiceBus()`` instances to stay isolated.

Usage
-----
    from contracts.bus import bus
    from contracts.types import Event, Topics

    # Subscribe
    def on_review_done(event: Event) -> None:
        print(event.payload)

    bus.subscribe(Topics.REVIEW_COMPLETED, on_review_done)

    # Publish (from services/review.py)
    bus.publish(Event(
        topic=Topics.REVIEW_COMPLETED,
        payload={"project_id": pid, "review_id": rid},
        source="services.review",
    ))
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Dict, List

from contracts.types import Event

logger = logging.getLogger(__name__)

# Type alias
Subscriber = Callable[[Event], None]


class ServiceBus:
    """Synchronous, in-process pub/sub broker."""

    def __init__(self) -> None:
        # topic_prefix → list of subscribers
        self._subscribers: Dict[str, List[Subscriber]] = defaultdict(list)

    def subscribe(self, topic_prefix: str, fn: Subscriber) -> None:
        """Register ``fn`` for all events whose topic starts with ``topic_prefix``.

        Use ``""`` (empty string) to subscribe to every event.
        """
        self._subscribers[topic_prefix].append(fn)

    def unsubscribe(self, topic_prefix: str, fn: Subscriber) -> None:
        """Remove a previously registered subscriber.  Silent no-op if not found."""
        listeners = self._subscribers.get(topic_prefix, [])
        try:
            listeners.remove(fn)
        except ValueError:
            pass

    def publish(self, event: Event) -> int:
        """Dispatch ``event`` to all matching subscribers.

        Matching rule: subscriber prefix must be a prefix of ``event.topic``
        (whole-segment match, e.g. ``review`` matches ``review.completed`` but
        not ``reviewer.updated``).

        Returns the number of subscribers notified.
        """
        notified = 0
        for prefix, listeners in self._subscribers.items():
            if self._matches(prefix, event.topic):
                for fn in list(listeners):  # snapshot — safe against mutation
                    try:
                        fn(event)
                        notified += 1
                    except Exception:
                        logger.exception(
                            "ServiceBus subscriber %s raised on topic %s",
                            getattr(fn, "__qualname__", repr(fn)),
                            event.topic,
                        )
        return notified

    def clear(self) -> None:
        """Remove all subscriptions.  Intended for test teardown."""
        self._subscribers.clear()

    @staticmethod
    def _matches(prefix: str, topic: str) -> bool:
        """Return True when ``prefix`` is a valid prefix of ``topic``."""
        if prefix == "":
            return True
        if topic == prefix:
            return True
        # Segment boundary: "review" matches "review.completed" not "reviewer"
        return topic.startswith(prefix + ".")


# Shared singleton — import this in services and handlers
bus: ServiceBus = ServiceBus()
