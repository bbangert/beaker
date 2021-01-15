import pytest
from beaker.cache import make_params_serializer

def test_serializer_simple_fun():

    def f0():
        pass

    f0_serializer = make_params_serializer(f0)
    assert f0_serializer() == {}


f1_test_params = [
    ((1, 2), {'a': 1, 'b': 2})
]

@pytest.mark.parametrize(
     'args, expected',
     f1_test_params
 )
def test_serializer_args_fun(args, expected):
    def f1(a, b):
        pass

    f1_serializer = make_params_serializer(f1)
    assert f1_serializer(*args) == expected


f2_test_params = [
    (
        [], {'b': 3, 'a': 2},
        {'a': 2, 'b': 3, 'c': 3}
    ),
    (
        [1], {'b': 3},
        {'a': 1, 'b': 3, 'c': 3}
    ),
    (
        [1], {'b': 4, 'c': 5},
        {'a': 1, 'b': 4, 'c': 5}
    ),
    (
        [1, 2], {},
        {'a': 1, 'b': 2, 'c': 3}
    ),
    (
        [1, 2, 3], {},
        {'a': 1, 'b': 2, 'c': 3}
    ),
    (
        [1, 2, 4], {},
        {'a': 1, 'b': 2, 'c': 4}
    ),
]

@pytest.mark.parametrize(
     'args, kwargs, expected',
     f2_test_params
 )
def test_serializer_generic(args, kwargs, expected):
    def f2(a, b, c=3):
        pass

    f2_serializer = make_params_serializer(f2)
    assert f2_serializer(*args, **kwargs) == expected
