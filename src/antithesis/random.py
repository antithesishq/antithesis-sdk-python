"""This module requests both structured and unstructured randomness
from the Antithesis environment.

These functions should not be used to seed a conventional PRNG, and
should not have their return values stored and used to make a decision
at a later time. Doing either of these things makes it much harder
for the Antithesis platform to control the history of your program's
execution, and also makes it harder for Antithesis to explore your
program efficiently . Instead, you should call a function from the
random package every time your program or
[test template](https://antithesis.com/docs/getting_started/first_test/)
needs to make a decision, at the moment that you need to make the
decision.

These functions are also safe to call outside the Antithesis
environment, where they will fall back on values from `random.getrandbits()`.
"""

import random
from typing import Any, List

from antithesis._internal import dispatch_random


def get_random() -> int:
    """Provides a random 64 bit int.

    You should use this value immediately rather than using it later. 
        If you delay, then it is possible for the simulation to branch in between receiving 
        the random data and using it. These branches will have the same random value, 
        which defeats the purpose of branching.

    Similarly, do not use the value to seed a pseudo-random number generator. 
        The PRNG will produce a deterministic sequence of pseudo-random values based on the seed, 
        so if the simulation branches, the PRNG will use the same sequence of values in all branches.
        
    Returns:
        int: A random 64 bit int
    """
    return dispatch_random()


def random_choice(things: List[Any]) -> Any:
    """Provides a randomly chosen item from a list of options.

    You should use this value immediately rather than using it later. 
        If you delay, then it is possible for the simulation to branch in between receiving 
        the random data and using it. These branches will have the same random value, 
        which defeats the purpose of branching.

    Similarly, do not use the value to seed a pseudo-random number generator. 
        The PRNG will produce a deterministic sequence of pseudo-random values based on the seed, 
        so if the simulation branches, the PRNG will use the same sequence of values in all branches.

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


class AntithesisRandom(random.Random):
    def random(self) -> float:
        return (get_random() & ((1 << 53) - 1)) / (2**53)

    def getrandbits(self, k: int) -> int:
        result = 0
        bits_needed = k
        while bits_needed > 0:
            word = get_random() & 0xFFFFFFFFFFFFFFFF
            result = (result << 64) | word
            bits_needed -= 64
        # Trim bits to a power-of-two boundary
        return result & ((1 << k) - 1)

    def _notimplemented(self, *args, **kwds):
        raise NotImplementedError(
            "AntithesisRandom state is controlled by the Antithesis environment."
        )

    getstate = setstate = _notimplemented
