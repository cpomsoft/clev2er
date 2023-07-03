""" clev2er.algorithms.cryotempo.algorithm_geolocate"""

# These imports required by Algorithm template
import logging
import os
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.cs2.geolocate.geolocate_lrm import geolocate_lrm
from clev2er.utils.cs2.geolocate.geolocate_sin import geolocate_sin
from clev2er.utils.dems.dems import Dem

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to geolocate measurements to the POCA (point of closest approach)**

    Also to calculate height_20_ku

    Different geolocation functions called for LRM and SIN

    ** Contribution to Shared Dictionary **

        - shared_dict["lat_poca_20_ku"] : np.ndarray (POCA latitudes)
        - shared_dict["lon_poca_20_ku"] : np.ndarray (POCA longitudes)
        - shared_dict["height_20_ku"]   : np.ndarray (elevations)

    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Runs init() if not in multi-processing mode
        Args:
            config (dict): configuration dictionary

        Returns:
            None
        """
        self.alg_name = __name__
        self.config = config

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        if config["chain"]["use_multi_processing"]:
            return

        _, _ = self.init(log, 0)

    def init(self, mplog: logging.Logger, filenum: int) -> Tuple[bool, str]:
        """Algorithm initialization template

        Args:
            mplog (logging.Logger): log instance to use
            filenum (int): file number being processed

        Returns:
            (bool,str) : success or failure, error string
        """
        mplog.debug(
            "[f%d] Initializing algorithm %s",
            filenum,
            self.alg_name,
        )

        # Check slope models file
        if not os.path.isfile(self.config["slope_models"]["model_file"]):
            mplog.error(
                "[f%d] slope model file: %s not found",
                filenum,
                self.config["slope_models"]["model_file"],
            )
            return (
                False,
                f'slope model file: {self.config["slope_models"]["model_file"]} not found',
            )

        # Get the DEMs for slope correction

        self.dem_ant = Dem("rema_ant_1km")
        self.dem_grn = Dem("arcticdem_1km")

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(
        self, l1b: Dataset, shared_dict: dict, mplog: logging.Logger, filenum: int
    ) -> Tuple[bool, str]:
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog (logging.Logger): multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        **IMPORTANT NOTE:** when logging within the Algorithm.process() function you must use
        the mplog logger with a filenum as an argument:

        `mplog.error("[f%d] your message",filenum)`

        This is required to support logging during multi-processing
        """

        # When using multi-processing it is faster to initialize the algorithm
        # within each Algorithm.process(), rather than once in the main process's
        # Algorithm.__init__().
        # This avoids having to pickle the initialized data arrays (which is extremely slow)
        if self.config["chain"]["use_multi_processing"]:
            rval, error_str = self.init(mplog, filenum)
            if not rval:
                return (rval, error_str)

        mplog.debug(
            "[f%d] Processing algorithm %s",
            filenum,
            self.alg_name,
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            mplog.error("[f%d] l1b parameter is not a netCDF4 Dataset type", filenum)
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        # --------------------------------------------------------------------
        # Geo-location (slope correction)
        # --------------------------------------------------------------------

        if shared_dict["instr_mode"] == "LRM":
            log.info("Calling LRM geolocation")
            height_20_ku, lat_poca_20_ku, lon_poca_20_ku = geolocate_lrm(
                l1b,
                self.config,
                shared_dict["cryotempo_surface_type"],
                shared_dict["range_cor_20_ku"],
            )
            log.info("LRM geolocation finished")

        elif shared_dict["instr_mode"] == "SIN":
            log.info("Calling SIN geolocation")
            height_20_ku, lat_poca_20_ku, lon_poca_20_ku = geolocate_sin(
                l1b,
                self.config,
                self.dem_ant,
                self.dem_grn,
                shared_dict["range_cor_20_ku"],
                shared_dict["ind_wfm_retrack_20_ku"],
            )
            log.info("SIN geolocation finished")
        else:
            mplog.error(
                "[f%d] mode %s not supported by alg_geolocate algorithm",
                filenum,
                shared_dict["instr_mode"],
            )
            return (
                False,
                f'instrument mode {shared_dict["instr_mode"]} must be LRM or SIN : ',
            )

        shared_dict["lat_poca_20_ku"] = lat_poca_20_ku

        np.seterr(under="ignore")  # otherwise next line can fail
        shared_dict["lon_poca_20_ku"] = lon_poca_20_ku % 360.0

        shared_dict["height_20_ku"] = height_20_ku

        # Return success (True,'')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
