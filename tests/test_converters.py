import unittest

from beaker.converters import asbool, aslist


class AsBool(unittest.TestCase):
    def test_truth_str(self):
        for v in ('true', 'yes', 'on', 'y', 't', '1'):
            self.assertTrue(asbool(v), "%s should be considered True" % (v,))
            v = v.upper()
            self.assertTrue(asbool(v), "%s should be considered True" % (v,))

    def test_false_str(self):
        for v in ('false', 'no', 'off', 'n', 'f', '0'):
            self.assertFalse(asbool(v), v)
            v = v.upper()
            self.assertFalse(asbool(v), v)

    def test_coerce(self):
        """Things that can coerce right straight to booleans."""
        self.assertTrue(asbool(True))
        self.assertTrue(asbool(1))
        self.assertTrue(asbool(42))
        self.assertFalse(asbool(False))
        self.assertFalse(asbool(0))

    def test_bad_values(self):
        self.assertRaises(ValueError, asbool, ('mommy!'))
        self.assertRaises(ValueError, asbool, (u'Blargl?'))


class AsList(unittest.TestCase):
    def test_string(self):
        self.assertEqual(aslist('abc'), ['abc'])
        self.assertEqual(aslist('1a2a3', 'a'), ['1', '2', '3'])

    def test_None(self):
        self.assertEqual(aslist(None), [])

    def test_listy_noops(self):
        """Lists and tuples should come back unchanged."""
        x = [1, 2, 3]
        self.assertEqual(aslist(x), x)
        y = ('z', 'y', 'x')
        self.assertEqual(aslist(y), y)

    def test_listify(self):
        """Other objects should just result in a single item list."""
        self.assertEqual(aslist(dict()), [{}])


if __name__ == '__main__':
    unittest.main()

