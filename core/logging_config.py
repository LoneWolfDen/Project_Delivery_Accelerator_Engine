"""Application logging configuration.

Call ``configure_logging()`` once at server startup.  All other modules
should use the standard pattern::

    import logging
    logger = logging.getLogger(__name__)

This gives structured, levelled output without any third-party dependency.
"""

import logging
import os


def configure_logging() -> None:
    """Configure the root logger for the application.

    Log level is controlled by the ``LOG_LEVEL`` environment variable
    (default: INFO).  Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
