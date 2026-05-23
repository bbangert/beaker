from beaker.util import encoded_path
import pathlib

def test_strips_leading_periods(tmp_path):
    """
    Ensure that leading periods in the identifier are stripped when
    digest_filenames=False to prevent limited traversal
    """

    out = encoded_path(
        root=tmp_path,
        identifiers=["..poc"],
        digest_filenames=False
    )

    p = pathlib.Path(out)

    # The resulting filename must not begin with a dot
    assert not p.name.startswith("."), "Leading periods should be stripped"

    # After stripping leading dots, the stem should match
    assert p.stem == "poc", "Filename should preserve content minus leading dots"

    # And extension should still be present
    assert p.suffix == ".enc"

    # encoded path should be a child of input, ./po/p/poc.enc
    assert p.is_relative_to(tmp_path)

    # check no traversal has put the encoded directory back to the input
    assert str(p.parent) != str(tmp_path.absolute())

