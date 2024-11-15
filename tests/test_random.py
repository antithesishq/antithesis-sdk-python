import pytest

from antithesis.random import get_random, random_choice

def test_random_dist():
    all_vals = set([])
    for i in range(100000):
        random_val = get_random()
        already_has_val = random_val in all_vals
        assert not already_has_val
        all_vals.add(random_val)

def test_random_none():
    random_item = random_choice([])
    assert random_item is None

def test_random_one():
    random_item = random_choice(["abc"])
    assert random_item == "abc"

def test_random_many_list():
    num_items = 20
    start = -5
    end = start + num_items
    things = range(start, end)
    random_item = random_choice(things)
    assert (random_item >= start) and (random_item <= end)

def test_random_many_tuple():
    a_bool =True
    an_int = 10
    a_string = "ab  c"
    a_float = 12.875
    a_list = [100, 200, 300]
    things = (a_bool, an_int, a_string, a_float, a_list)
    random_item = random_choice(things)
    assert ((random_item == a_bool) or
        (random_item == an_int) or
        (random_item == a_string) or
        (random_item == a_float) or
        (random_item == a_list))
