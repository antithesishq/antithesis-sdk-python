import sys


def gen[T](x: T) -> T:
    if x:
        return x
    return x


if __name__ == "__main__":
    if sys.argv[1] == "call":
        gen(1)
