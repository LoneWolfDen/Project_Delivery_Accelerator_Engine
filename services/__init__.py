"""Services package — domain-split business logic.

Each module owns one domain.  All imports are top-level (no deferred
``from x import y`` inside function bodies).

Domains
-------
project     — CRUD, persistence, lifecycle (archive/restore/delete)
ingest      — file ingestion into context store
intelligence — build/load project intelligence
review      — persona review runs, weakness/decision tracking
proposal    — proposal tracker and versioning
hierarchy   — Phase → Version → Review hierarchy model
admin       — config, health, lifecycle logs
deepdive    — SME deep-dive analysis and feedback
diagram     — drawio diagram generation/storage
presales    — pre-sales feedback, tokens, finalisation
"""
