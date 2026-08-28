import sys


class CM:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False  # does not suppress


def run(mode):
    try:
        with CM():
            if mode == "zero":
                return 1 // 0
            if mode == "raise":
                raise ValueError("boom")
            return 1
    except ZeroDivisionError:
        return -1
    except (TypeError, ValueError):
        return -2


if __name__ == "__main__":
    run(sys.argv[1])
