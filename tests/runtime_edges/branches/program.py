import sys


def classify(n):
    if n < 0 or n > 100:
        return "out-of-range"
    if n % 2 == 0 and n != 0:
        return "even"
    return "odd-or-zero"


if __name__ == "__main__":
    classify(int(sys.argv[1]))
