from .handlers import Handler, LocalHandler, NoopHandler, VoidstarHandler


def _setup_handler() -> Handler:
    return VoidstarHandler.get() or LocalHandler.get() or NoopHandler.get()


_HANDLER: Handler = _setup_handler()

from .dispatch import (
        dispatch_output,
        dispatch_random,
        requires_antithesis_output,
)

from .handlers import (
        LOCAL_OUTPUT_ENV_VAR,
)

from .sdk_constants import (
        ANTITHESIS_SDK_VERSION, 
        ANTITHESIS_PROTOCOL_VERSION,
)
