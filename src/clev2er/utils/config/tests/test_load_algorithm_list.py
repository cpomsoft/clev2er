"""pytest of utils.config.load_config_files()
"""

import os

from clev2er.utils.config.load_config_settings import load_algorithm_list


def test_load_algorithm_list():
    """pytest function for utils.config.load_algorithm_list()"""

    # ----------------------------------------------------------------
    # test with chain: testchain which should return
    #  2 algorithms and no finders
    # -----------------------------------------------------------------
    chain_name = "testchain"

    try:
        alg_list, finder_list, _ = load_algorithm_list(chain_name)
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    n_algs = len(alg_list)
    assert (
        n_algs == 2
    ), f"Should return two algorithms from testchain but {n_algs} returned"

    n_finders = len(finder_list)
    assert n_finders == 0, "Should be no finders returned from testchain"

    # ----------------------------------------------------------------
    # test with chain: cryotempo baseline-c which should return
    #  18 algorithms and 2 finders
    # -----------------------------------------------------------------

    chain_name = "cryotempo"

    try:
        alg_list, finder_list, _ = load_algorithm_list(chain_name, baseline="C")
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    n_algs = len(alg_list)
    assert (
        n_algs == 18
    ), f"Should return 18 algorithms from cryotempo but {n_algs} returned"

    n_finders = len(finder_list)
    assert n_finders == 2, "Should be 2 finders returned from cryotempo"

    try:
        alg_list, finder_list, _ = load_algorithm_list(
            chain_name,
            baseline="C",
            alg_list_file=f"{os.environ['CLEV2ER_BASE_DIR']}"
            "/config/algorithm_lists/cryotempo_C001.xml",
        )
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    n_algs = len(alg_list)
    assert (
        n_algs == 18
    ), f"Should return 18 algorithms from cryotempo but {n_algs} returned"
