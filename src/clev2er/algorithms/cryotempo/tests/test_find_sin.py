""" test of find_sin.py
"""
from os import environ

from clev2er.algorithms.cryotempo.find_sin import FileFinder


def test_find_sin():
    """test the clev2er.algorithms.cryotempo.find_sin.FileFinder class"""

    assert "CPDATA_DIR" in environ, "Missing env variable CPDATA_DIR"

    config = {}
    config["l1b_base_dir"] = f'{environ["CPDATA_DIR"]}/SATS/RA/CRY/L1B'
    config["l1b_baselines"] = "D,E"

    finder = FileFinder(config=config)

    finder.add_year(2009)
    files = finder.find_files()
    assert len(files) == 0, "Should find no files in 2009"

    # finder.add_month(1)
    finder.add_year(2020)
    files = finder.find_files()
    assert len(files) > 0, "Should find some files in 2020"
    finder.add_year(2019)
    files = finder.find_files()
    assert len(files) > 0, "Should find some files in 2019,2020"
