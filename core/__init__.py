"""Core infrastructure — paths, logging, shared constants.

This package should not import from any domain module (models, processors,
services, db).  It exists to break circular imports and give every module a
single authoritative source for path and runtime configuration.
"""
