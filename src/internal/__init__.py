"""Internal
The internal module contains handlers for voidstar,
local output, and no-op along with the fallback
mechanism for choosing and initializing the 
active handler
"""
from .handlers import Handler, _setup_handler, LOCAL_OUTPUT_ENV_VAR
# from .dispatch import dispatch_output, dispatch_random
from .sdk_constants import ANTITHESIS_SDK_VERSION, ANTITHESIS_PROTOCOL_VERSION


_HANDLER: Handler = _setup_handler()

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
