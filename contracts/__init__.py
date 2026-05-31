"""Contracts package — agentic seam definitions for Phase 3.

Provides the stable interfaces that cross domain boundaries so services
and handlers depend on abstractions, not concrete implementations.

Modules
-------
types       — shared value types (ReviewRequest, ReviewResult, Event, …)
bus         — ServiceBus: publish/subscribe event broker
protocols   — ReviewAgent and related runtime Protocols (PEP 544)
"""
