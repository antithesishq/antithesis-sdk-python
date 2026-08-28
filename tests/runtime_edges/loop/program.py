import sys


def total(n):
    s = 0
    for i in range(n):
        s += i
    return s


if __name__ == "__main__":
    total(int(sys.argv[1]))
