from handlers import Handler, LocalHandler, NoopHandler

_HANDLER: Handler = _setup_handler()

def _setup_handler() -> Handler:
    return LocalHandler.get() or NoopHandler.get()
    