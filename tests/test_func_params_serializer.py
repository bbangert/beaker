from beaker.cache import make_params_serializer


def f1():
    pass

def f2(a, b, c=3):
    pass

f2_test_params = [
    {
        'args': [1, 2, 3],
        'kwargs': {},
        'expected': {'a': 1, 'b': 2, 'c': 3}
    },
    {
        'args': [1,2,4],
        'kwargs': {},
        'expected': {'a': 1, 'b': 2, 'c': 4}
    },
    {
        'args': [1],
        'kwargs': {'b': 4, 'c': 5},
        'expected': {'a': 1, 'b': 4, 'c': 5}
    }
]

def f3(a, b=2, *, c=3):
    pass

f3_test_params = [
    {
        'args': [1],
        'kwargs': {'b': 3},
        'expected': {'a': 1, 'b': 3, 'c': 3}
    },
    {
        'args': [1,2],
        'kwargs': {},
        'expected': {'a': 1, 'b': 2, 'c': 3}
    },
    {
        'args': [1],
        'kwargs': {'c': 5},
        'expected': {'a': 1, 'b': 2, 'c': 5}
    }
]

def test_func_params_serializer():

    f1_serializer = make_params_serializer(f1)

    assert f1_serializer() == {}

    f2_serializer = make_params_serializer(f2)
    for params in f2_test_params:
        assert f2_serializer(*params['args'], **params['kwargs']) == params['expected']

    f3_serializer = make_params_serializer(f3)
    for params in f3_test_params:
        assert f3_serializer(*params['args'], **params['kwargs']) == params['expected']
