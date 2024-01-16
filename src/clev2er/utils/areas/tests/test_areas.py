"""pytests for clev2er.utils.areas.areas.py
"""
import pytest

from clev2er.utils.areas.areas import Area


def test_bad_area_name():
    """pytest to check for handling of invalid area names"""
    with pytest.raises(ImportError):
        Area("badname")


def test_good_area_name():
    """pytest to check for handling of valid area names"""
    Area("antarctica")
