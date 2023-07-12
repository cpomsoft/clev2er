""" test of find_lrm.py
"""
import pytest

from clev2er.algorithms.cryotempo.find_lrm import FileFinder


def test_find_lrm():
    """test the clev2er.algorithms.cryotempo.find_lrm.FileFinder class"""
    finder = FileFinder()

    # finder.add_month(1)
    finder.add_year(2020)
    finder.add_year(2019)
    finder.set_baselines("DE")
    finder.set_base_path("/raid6/cpdata/SATS/RA/CRY/L1B/LRM/2019/05")
    files = finder.find_files(flat_search=True)
    assert len(files) > 0, "Should find some files"
    finder.set_base_path("/raid6/cpdata/SATS/RA/CRY/L1B")
    files = finder.find_files()
    assert len(files) > 0, "Should find some files"
    with pytest.raises(FileNotFoundError):
        finder.set_base_path("/tmp/453r/EQR")
    files = finder.find_files()
