"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_product_output.py
"""
import logging
import os
import string
from typing import Any, Dict

import pytest
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_backscatter import (
    Algorithm as Backscatter,
)
from clev2er.algorithms.cryotempo.alg_basin_ids import Algorithm as BasinIds
from clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction import (
    Algorithm as Cats2008a,
)
from clev2er.algorithms.cryotempo.alg_dilated_coastal_mask import (
    Algorithm as CoastalMask,
)
from clev2er.algorithms.cryotempo.alg_fes2014b_tide_correction import (
    Algorithm as Fes2014b,
)
from clev2er.algorithms.cryotempo.alg_filter_height import (
    Algorithm as FilterHeight,
)
from clev2er.algorithms.cryotempo.alg_geo_corrections import (
    Algorithm as GeoCorrections,
)
from clev2er.algorithms.cryotempo.alg_geolocate_lrm import (
    Algorithm as Geolocate_Lrm,
)
from clev2er.algorithms.cryotempo.alg_geolocate_sin import (
    Algorithm as Geolocate_Sin,
)
from clev2er.algorithms.cryotempo.alg_identify_file import (
    Algorithm as IdentifyFile,
)
from clev2er.algorithms.cryotempo.alg_product_output import Algorithm
from clev2er.algorithms.cryotempo.alg_ref_dem import Algorithm as RefDem
from clev2er.algorithms.cryotempo.alg_retrack import Algorithm as Retracker
from clev2er.algorithms.cryotempo.alg_skip_on_area_bounds import (
    Algorithm as SkipArea,
)
from clev2er.algorithms.cryotempo.alg_skip_on_mode import Algorithm as SkipMode
from clev2er.algorithms.cryotempo.alg_surface_type import (
    Algorithm as SurfaceType,
)
from clev2er.algorithms.cryotempo.alg_uncertainty import (
    Algorithm as Uncertainty,
)
from clev2er.algorithms.cryotempo.alg_waveform_quality import (
    Algorithm as WaveformQuality,
)

# Similar lines in 2 files, pylint: disable=R0801
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "l1b_file",
    [
        ("CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"),  # SIN, over AIS
        ("CS_OFFL_SIR_SIN_1B_20190511T005631_20190511T005758_D001.nc"),  # SIN, over GIS
        ("CS_OFFL_SIR_LRM_1B_20200911T023800_20200911T024631_D001.nc"),  # LRM, over AIS
        ("CS_OFFL_SIR_LRM_1B_20200930T235609_20200930T235758_D001.nc"),  # LRM, over GRN
    ],
)
def test_alg_product_output(l1b_file) -> None:
    """test of clev2er.algorithms.cryotempo.alg_product_output.py"""

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    config_file = f"{base_dir}/config/main_config.yml"
    assert os.path.exists(config_file), f"config file {config_file} does not exist"

    try:
        config = EnvYAML(config_file)  # read the YML and parse environment variables
    except ValueError as exc:
        assert (
            False
        ), f"ERROR: config file {config_file} has invalid or unset environment variables : {exc}"

    # Load cryotempo chain config file by finding latest baseline
    # ie baseline B before A
    reverse_alphabet_list = list(string.ascii_uppercase[::-1])
    baseline = None
    for _baseline in reverse_alphabet_list:
        config_file = f"{base_dir}/config/chain_configs/cryotempo_{_baseline}001.yml"
        if os.path.exists(config_file):
            baseline = _baseline
            break
    assert baseline, "No cryotempo baseline config file found"

    log.info("Using config file %s", config_file)

    try:
        chain_config = EnvYAML(
            config_file
        )  # read the YML and parse environment variables
    except ValueError as exc:
        assert (
            False
        ), f"ERROR: config file {config_file} has invalid or unset environment variables : {exc}"

    # merge the two config files (with precedence to the chain_config)
    config = config.export() | chain_config.export()  # the export() converts to a dict

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise any other Algorithms required by test

    try:
        identify_file = IdentifyFile(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize IdentifyFile algorithm {exc}"

    try:
        surface_type = SurfaceType(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize SurfaceType algorithm {exc}"

    try:
        skip_mode = SkipMode(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize SkipMode algorithm {exc}"

    try:
        fes2014b = Fes2014b(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize Fes2014b algorithm {exc}"

    try:
        cats2008a = Cats2008a(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize Cats2008a algorithm {exc}"

    try:
        geo_corrections = GeoCorrections(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize GeoCorrections algorithm {exc}"

    try:
        skip_area = SkipArea(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize SkipArea algorithm {exc}"

    try:
        coastal_mask = CoastalMask(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize CoastalMask algorithm {exc}"

    try:
        waveform_quality = WaveformQuality(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize WaveformQuality algorithm {exc}"

    try:
        retracker = Retracker(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    try:
        backscatter = Backscatter(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    try:
        geolocate_lrm = Geolocate_Lrm(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    try:
        geolocate_sin = Geolocate_Sin(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    try:
        filter_height = FilterHeight(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize FilterHeight algorithm {exc}"

    try:
        basin_ids = BasinIds(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize BasinIds algorithm {exc}"

    try:
        ref_dem = RefDem(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize RefDem algorithm {exc}"

    try:
        uncertainty = Uncertainty(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize Uncertainty algorithm {exc}"

    # Initialise the Algorithm being tested
    try:
        thisalg = Algorithm(config=config)  # no config used for this alg
    except (KeyError, FileNotFoundError) as exc:
        assert False, f"Could not initialize algorithm {exc}"

    # -------------------------------------------------------------------------
    # Test with L1b file

    l1b_file = f"{base_dir}/testdata/cs2/l1bfiles/{l1b_file}"
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict: Dict[str, Any] = {}

    # setup dummy shared_dict results from other algorithms

    shared_dict["l1b_file_name"] = l1b_file

    # mock the final lat/lon from nadir

    # Run other alg process required by test to fill in
    # required shared_dict parameters

    success, _ = identify_file.process(l1b, shared_dict, log, 0)
    assert success, "identify_file algorithm should not fail"

    success, _ = skip_mode.process(l1b, shared_dict, log, 0)
    assert success, "skip_mode algorithm should not fail"

    success, _ = skip_area.process(l1b, shared_dict, log, 0)
    assert success, "skip_area algorithm should not fail"

    success, _ = surface_type.process(l1b, shared_dict, log, 0)
    assert success, "surface_type algorithm should not fail"

    success, _ = coastal_mask.process(l1b, shared_dict, log, 0)
    assert success, "coastal_mask algorithm should not fail"

    success, _ = cats2008a.process(l1b, shared_dict, log, 0)
    assert success, "cats2008a algorithm should not fail"
    success, _ = fes2014b.process(l1b, shared_dict, log, 0)
    assert success, "fes2014b algorithm should not fail"

    success, _ = geo_corrections.process(l1b, shared_dict, log, 0)
    assert success, "geo_corrections algorithm should not fail"

    success, _ = waveform_quality.process(l1b, shared_dict, log, 0)
    assert success, "waveform quality algorithm should not fail"

    success, _ = retracker.process(l1b, shared_dict, log, 0)
    assert success, "retracker algorithm should not fail"

    success, _ = backscatter.process(l1b, shared_dict, log, 0)
    assert success, "backscatter algorithm should not fail"

    success, _ = geolocate_lrm.process(l1b, shared_dict, log, 0)
    assert success, "geolocate_lrm algorithm should not fail"

    success, _ = geolocate_sin.process(l1b, shared_dict, log, 0)
    assert success, "geolocate_sin algorithm should not fail"

    success, _ = basin_ids.process(l1b, shared_dict, log, 0)
    assert success, "basin_ids algorithm should not fail"

    success, _ = ref_dem.process(l1b, shared_dict, log, 0)
    assert success, "ref_dem algorithm should not fail"

    success, _ = filter_height.process(l1b, shared_dict, log, 0)
    assert success, "filter_height algorithm should not fail"

    success, _ = uncertainty.process(l1b, shared_dict, log, 0)
    assert success, "uncertainty algorithm should not fail"

    # Run the alg process
    success, error_str = thisalg.process(l1b, shared_dict, log, 0)
    assert success, f"algorithm should not fail {error_str}"

    # Test outputs of algorithm

    assert "product_filename" in shared_dict, "product_filename not in shared_dict"

    dset = Dataset(shared_dict["product_filename"], "r")

    # check that all these netcdf parameters are in product
    # and of correct length
    ct_params = [
        "time",
        "latitude",
        "longitude",
        "instrument_mode",
        "elevation",
        "backscatter",
        "surface_type",
        "reference_dem",
        "basin_id",
        "basin_id2",
        "uncertainty",
    ]

    for param in ct_params:
        assert len(dset[param][:].data) == len(l1b["lat_20_ku"][:].data)

    ct_attributes = [
        "title",
        "project",
        "doi",
        "creator_name",
        "creator_url",
        "date_created",
        "platform",
        "sensor",
        "instrument_mode",
        "src_esa_l1b_file",
        "ascending_start_record",
        "descending_start_record",
        "geospatial_lat_min",
        "geospatial_lat_max",
        "geospatial_lon_min",
    ]

    for attr in ct_attributes:
        assert attr in dset.ncattrs()

    dset.close()
