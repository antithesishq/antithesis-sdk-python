from internal import _HANDLER
from typing import Callable, Any

def requires_antithesis_output(func: Callable) -> Callable:
    """Wraps output code to reduce needless work in noop cases"""
    def wrapper(*args, **kwargs) -> Any:
        if _HANDLER.handles_output:
            return func(*args, **kwargs)
        else:
            return None
    return wrapper

def dispatch_output(json: str):
    return _HANDLER.output(json)


def dispatch_random() -> int:
    return _HANDLER.random()
