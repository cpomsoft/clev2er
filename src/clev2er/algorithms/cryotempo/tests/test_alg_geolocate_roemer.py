"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_geolocate_roemer.py
"""
import logging
import os

import numpy as np
import pytest
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction import (
    Algorithm as Cats2008a,
)
from clev2er.algorithms.cryotempo.alg_dilated_coastal_mask import (
    Algorithm as CoastalMask,
)
from clev2er.algorithms.cryotempo.alg_fes2014b_tide_correction import (
    Algorithm as Fes2014b,
)
from clev2er.algorithms.cryotempo.alg_geo_corrections import Algorithm as GeoCorrections
from clev2er.algorithms.cryotempo.alg_geolocate_roemer import Algorithm
from clev2er.algorithms.cryotempo.alg_identify_file import Algorithm as IdentifyFile
from clev2er.algorithms.cryotempo.alg_retrack import Algorithm as Retracker
from clev2er.algorithms.cryotempo.alg_skip_on_area_bounds import Algorithm as SkipArea
from clev2er.algorithms.cryotempo.alg_skip_on_mode import Algorithm as SkipMode
from clev2er.algorithms.cryotempo.alg_surface_type import Algorithm as SurfaceType
from clev2er.algorithms.cryotempo.alg_waveform_quality import (
    Algorithm as WaveformQuality,
)
from clev2er.utils.config.load_config_settings import load_config_files

# Similar lines in 2 files, pylint: disable=R0801
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements

log = logging.getLogger(__name__)


def distance_between_latlon_points(latitudes1, longitudes1, latitudes2, longitudes2):
    """
    Calculate the great-circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(
        np.radians, [latitudes1, longitudes1, latitudes2, longitudes2]
    )

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    aaa = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    ccc = 2 * np.arcsin(np.sqrt(aaa))
    radius = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return ccc * radius


@pytest.mark.parametrize(
    "l1b_file, l2i_file",
    [
        (
            "CS_LTA__SIR_LRM_1B_20200930T235609_20200930T235758_E001.nc",  # LRM L1B over GRN
            "CS_LTA__SIR_LRMI2__20200930T235609_20200930T235758_E001.nc",  # LRM L2i over GRN
        ),
        # (
        #     "CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc",  # SIN L1B within AIS
        #     "CS_OFFL_SIR_SINI2__20190504T122546_20190504T122726_D001.nc",  # SIN L2i within AIS
        # ),
        (
            "CS_OFFL_SIR_LRM_1B_20200911T023800_20200911T024631_D001.nc",  # LRM L1B within AIS
            "CS_OFFL_SIR_LRMI2__20200911T023800_20200911T024631_D001.nc",  # LRM L2I within AIS
        ),
    ],
)
def test_alg_geolocate_roemer(l1b_file, l2i_file) -> None:
    """test of clev2er.algorithms.cryotempo.alg_geolocate_roemer.py"""

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    # Load merged config file for chain
    config, _, _, _, _ = load_config_files("cryotempo", baseline="C", version=70)

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise the Algorithms
    try:
        thisalg = Algorithm(config, log)  # no config used for this alg
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    try:
        identify_file = IdentifyFile(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize IdentifyFile algorithm {exc}"

    try:
        surface_type = SurfaceType(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize SurfaceType algorithm {exc}"

    try:
        skip_mode = SkipMode(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize SkipMode algorithm {exc}"

    try:
        fes2014b = Fes2014b(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize Fes2014b algorithm {exc}"

    try:
        cats2008a = Cats2008a(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize Cats2008a algorithm {exc}"

    try:
        geo_corrections = GeoCorrections(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize GeoCorrections algorithm {exc}"

    try:
        skip_area = SkipArea(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize SkipArea algorithm {exc}"

    try:
        coastal_mask = CoastalMask(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize CoastalMask algorithm {exc}"

    try:
        waveform_quality = WaveformQuality(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize WaveformQuality algorithm {exc}"

    try:
        retracker = Retracker(config, log)
    except KeyError as exc:
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
    shared_dict = {}

    # ----------------------------------------------------------
    # setup dummy shared_dict results from other algorithms
    # ----------------------------------------------------------

    shared_dict["l1b_file_name"] = l1b_file  # set by run controller

    # ----------------------------------------------------------

    # Run previous CryoTEMPO algorithms.process() to generate required parameters

    success, _ = identify_file.process(l1b, shared_dict)
    assert success, "identify_file algorithm should not fail"

    success, _ = skip_mode.process(l1b, shared_dict)
    assert success, "skip_mode algorithm should not fail"

    success, _ = skip_area.process(l1b, shared_dict)
    assert success, "skip_area algorithm should not fail"

    success, _ = surface_type.process(l1b, shared_dict)
    assert success, "surface_type algorithm should not fail"

    success, _ = coastal_mask.process(l1b, shared_dict)
    assert success, "coastal_mask algorithm should not fail"

    success, _ = cats2008a.process(l1b, shared_dict)
    assert success, "cats2008a algorithm should not fail"
    success, _ = fes2014b.process(l1b, shared_dict)
    assert success, "fes2014b algorithm should not fail"

    success, _ = geo_corrections.process(l1b, shared_dict)
    assert success, "geo_corrections algorithm should not fail"

    success, _ = waveform_quality.process(l1b, shared_dict)
    assert success, "waveform quality algorithm should not fail"

    success, _ = retracker.process(l1b, shared_dict)
    assert success, "retracker algorithm should not fail"

    # Run this algorithm's  process() function
    success, _ = thisalg.process(l1b, shared_dict)
    if shared_dict["instr_mode"] == "SIN":
        assert success, "Should succeed with SIN file, but do nothing"

    if shared_dict["instr_mode"] == "LRM":
        assert success, "algorithm should not fail"

        # Test outputs from algorithm
        assert "lat_poca_20_ku" in shared_dict, "lat_poca_20_ku not in shared_dict"
        assert "lon_poca_20_ku" in shared_dict, "lon_poca_20_ku not in shared_dict"
        assert "height_20_ku" in shared_dict, "height_20_ku not in shared_dict"
        assert "roemer_slope_ok" in shared_dict, "roemer_slope_ok not in shared_dict"

        # Compare to POCA locations from ESA L2i of same track

        log.info(
            "Roemer slope calculated from DEM ok:  %.2f %%",
            np.mean(shared_dict["roemer_slope_ok"]) * 100.0,
        )

        l2i_file = f"{base_dir}/testdata/cs2/l2ifiles/{l2i_file}"
        try:
            l2i = Dataset(l2i_file)
            log.info("Opened %s", l2i_file)
        except IOError:
            assert False, f"{l2i_file} could not be read"

        if shared_dict["instr_mode"] == "SIN":
            l2i_height_20_ku = l2i["height_1_20_ku"][:].data
        if shared_dict["instr_mode"] == "LRM":
            l2i_height_20_ku = l2i["height_3_20_ku"][:].data

        l2i_lat_poca_20_ku = l2i["lat_poca_20_ku"][:].data
        l2i_lon_poca_20_ku = l2i["lon_poca_20_ku"][:].data

        distances = distance_between_latlon_points(
            shared_dict["lat_poca_20_ku"],
            shared_dict["lon_poca_20_ku"],
            l2i_lat_poca_20_ku,
            l2i_lon_poca_20_ku,
        )

        np.seterr(all="ignore")  # Stops FP errors when very small numbers are involved

        mean_distance = np.nanmean(distances)
        stdev_distance = np.nanstd(distances)
        max_distance = np.nanmax(distances)
        min_distance = np.nanmin(distances)

        assert (
            stdev_distance < 3.0
        ), "StDev of distances between L2i locations and POCA > 3km"
        assert (
            mean_distance < 2.0
        ), "Mean of distances between L2i locations and POCA > 2km"

        log.info("Mean distance %.2f km", mean_distance)
        log.info("Standard deviation distance %.2f  km", stdev_distance)
        log.info("Max distance %.2f  km", max_distance)
        log.info("Min distance %.2f  km", min_distance)

        # Compare heights with those from ESA L2i of same track

        height_diffs = l2i_height_20_ku - shared_dict["height_20_ku"]

        mean_height_diffs = np.nanmean(height_diffs)
        stdev_height_diffs = np.nanstd(height_diffs)

        log.info("Mean height diffs %.2f  m", mean_height_diffs)
        log.info("Std height diffs %.2f  m", stdev_height_diffs)

        if shared_dict["instr_mode"] == "LRM":
            assert np.abs(mean_height_diffs) < 2.2
            assert stdev_height_diffs < 6.0
        if shared_dict["instr_mode"] == "SIN":
            assert np.abs(mean_height_diffs) < 5.0
            assert stdev_height_diffs < 30.0
