"""Random64
The random64 module requests both structured and unstructured randomness
from the Antithesis environment.

These functions should not be used to seed a conventional PRNG, and
should not have their return values stored and used to make a decision
at a later time. Doing either of these things makes it much harder
for the Antithesis platform to control the history of your program's
execution, and also makes it harder for Antithesis to learn which
inputs provided at which times are most fruitful. Instead, you should
call a function from the random package every time your program or
[workload] needs to make a decision, at the moment that you need to
make the decision.

These functions are also safe to call outside the Antithesis
environment, where they will fall back on values from random.getrandbits().
"""

from typing import List, Any
from antithesis_sdk._internal import dispatch_random


def get_random() -> int:
    """Provides a random 64 bit int

    Returns:
        int: A random 64 bit int
    """
    return dispatch_random()


def random_choice(things: List[Any]) -> Any:
    """Provides a randomly chosen item from a list of options.
        You should not store this value, but should use it immediately.

    Args:
        things (List[Any]): A list of items to choose from

    Returns:
        Any: A random item taken from the provided list
    """
    lx = len(things)
    if lx == 0:
        return None
    if lx == 1:
        return things[0]
    val = get_random()
    if val < 0:
        val = 0 - val
    idx = val % lx
    return things[idx]


def _cmd_get_random():
    """Smoke-test for fuzz_get_random().

    Examples:
        Should be executed from a devshell

        >>> $ randomx
        1804289383
    """
    val = get_random()
    print(val)
