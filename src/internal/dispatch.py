from internal import _HANDLER

def dispatch_output(json: str): 
    return _HANDLER.output(json)

def dispatch_random() -> int: 
    return _HANDLER.random()