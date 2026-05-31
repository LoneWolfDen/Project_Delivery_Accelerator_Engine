"""Handlers package — HTTP request handlers, domain-split.

Each module owns one domain and exposes free functions that accept
``(body: dict, respond: Callable, ...)`` so they are completely
independent of the HTTP handler class and trivially testable.

The ``respond`` callable matches AcceleratorHandler._json_response
so no HTTP primitives leak into the business layer.

Modules
-------
project     — project CRUD, lifecycle, file toggles
ingest      — file ingestion
intelligence — build context, personas
review      — run review, quality gate, weakness/decision status
hierarchy   — hierarchy tree, version detail, diffs
proposal    — proposal create/version/status/document
admin       — config, health, phase transitions
deepdive    — SME deep-dive and feedback
diagram     — diagram generation/retrieval
artifact    — artifact upload/text/toggle/delete/process/patch
presales    — presales feedback, tokens, external submit
"""
