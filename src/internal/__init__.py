from .handlers import Handler, LocalHandler, NoopHandler


def _setup_handler() -> Handler:
    return LocalHandler.get() or NoopHandler.get()


_HANDLER: Handler = _setup_handler()

from .dispatch import dispatch_output, dispatch_random
