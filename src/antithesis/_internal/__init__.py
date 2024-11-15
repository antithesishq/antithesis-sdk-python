"""Internal
The internal module contains handlers for voidstar,
local output, and no-op along with the fallback
mechanism for choosing and initializing the 
active handler
"""

import os

from .handlers import (
    Handler,
    LocalHandler,
    NoopHandler,
    VoidstarHandler,
    _setup_handler,
    _version_message,
)
from .sdk_constants import (
    ANTITHESIS_SDK_VERSION,
    ANTITHESIS_PROTOCOL_VERSION,
    ASSERTION_CATALOG_ENV_VAR,
    ASSERTION_CATALOG_NAME,
    COVERAGE_MODULE_LIST,
)


def dispatch_output(json: str):
    """dispatch_output forwards the provided string
    to the active HANDLER.  There is no validation that
    the forwarded string is in valid JSON format.

    Args:
        json (str): String that will be forwarded to
            the active handler.
    """
    return _HANDLER.output(json)


def dispatch_random() -> int:
    """dispatch_random requests a random 64-bit
           integer from the active handler.

    Returns:
        int: A random 64 bit int
    """
    return _HANDLER.random()


# ----------------------------------------------------------------------
# Evaluate once - on load
# ----------------------------------------------------------------------
_HANDLER: Handler = _setup_handler()
_HANDLER.output(_version_message())
