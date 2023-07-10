""" clev2er.algorithms.templates.alg_template"""

import logging
import os
import subprocess
from datetime import datetime, timedelta  # date and time functions
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.orbits.find_orbit_directions import find_orbit_directions
from clev2er.utils.time.grain import Grain

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements

log = logging.getLogger(__name__)


def cnes_cycle_to_subcycle(cycle_number: int, rel_orbit_number: int) -> tuple[int, int]:
    """Calculate the CNES CS2 sub-cycle and track number number

    Args:
        cycle_number (int): ESA CS2 cycle number from L1b
        rel_orbit_number (int): CS2 relative orbit within ESA cycle

    Returns:
        tuple[int,int]: sub cycle number, track number
    """
    nb_tracks = 10688  # cycle of 368.24 days
    nb_sub_tracks = 840  # sub-cycle of 28.94 days

    absolute_tr = (cycle_number - 1) * nb_tracks + rel_orbit_number
    sub_cy = ((absolute_tr - 1) // nb_sub_tracks) + 1
    sub_tr = ((absolute_tr - 1) % nb_sub_tracks) + 1
    return sub_cy, sub_tr


def get_current_commit_hash() -> str:
    """retrieve the current git commit version
       or None if not available

    Returns:
        str: git commit hash, or '' if failed
    """
    try:
        # Execute the Git command to get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        commit_hash = result.stdout.strip()
        return commit_hash
    except subprocess.CalledProcessError as exc:
        # Handle the case when the command fails
        log.error("Could not get git commit hash, Error: %s", exc)
        return ""


class Algorithm:
    """**Algorithm to do...**.

    **Contribution to shared dictionary**

        None
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

        Raises:
            KeyError : keys not in config
            FileNotFoundError :
            OSError :

        Note: raise and Exception rather than just returning False
        """
        mplog.debug(
            "[f%d] Initializing algorithm %s",
            filenum,
            self.alg_name,
        )
        # -----------------------------------------------------------------
        #  \/ Place Algorithm initialization steps here \/
        # -----------------------------------------------------------------

        # Get leap seconds list

        if "leap_seconds" not in self.config:
            mplog.error("[f%d] leap_seconds not in config dict", filenum)
            raise KeyError("leap_seconds not in config dict")

        self.leap_seconds_file = self.config["leap_seconds"]
        if not os.path.isfile(self.leap_seconds_file):
            mplog.error(
                "[f%d] leap_seconds file: %s not found", filenum, self.leap_seconds_file
            )
            raise FileNotFoundError(
                f"leap_seconds file {self.leap_seconds_file} not found"
            )

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

        mplog.info(
            "[f%d] Processing algorithm %s",
            filenum,
            self.alg_name.rsplit(".", maxsplit=1)[-1],
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            mplog.error("[f%d] l1b parameter is not a netCDF4 Dataset type", filenum)
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to be passed
        # \/    down the chain in the 'shared_dict' dict     \/
        # -------------------------------------------------------------------

        # find the month and year of the start of the file

        # --------------------------------------------------------------------
        # Read time, which is TAI time in seconds since 1-Jan-2000
        # --------------------------------------------------------------------

        time_20_ku = l1b["time_20_ku"][:].data

        # --------------------------------------------------------------------
        # Convert Time from TAI->UTC
        # note: uses leap-seconds.list file which needs updating if new leap
        # seconds are added after 1-Jan-2017)
        # ---------------------------------------------------------------------

        this_grain = Grain(leap_second_filename=self.leap_seconds_file)

        time_tai_dt = [
            (datetime(2000, 1, 1, 0) + timedelta(seconds=i)) for i in time_20_ku
        ]
        time_utc_dt = [this_grain.tai2utc(i) for i in time_20_ku]
        diff_in_seconds = [
            (time_utc_dt[i] - time_tai_dt[i]).total_seconds()
            for i in range(len(time_tai_dt))
        ]
        time_utc_secs = time_20_ku + np.asarray(diff_in_seconds)

        start_month = time_utc_dt[0].month
        start_year = time_utc_dt[0].year

        log.info("start month %d %d", start_month, start_year)

        # ---------------------------------------------------------------------
        #  Form product directory path
        #    <base_dir>/<baseline>/<version:03>/LAND_ICE/<ANTARC,GREENL>/<YYYY>/<MM>
        # ---------------------------------------------------------------------

        zone_str = "GREENL"
        if shared_dict["hemisphere"] == "south":
            zone_str = "ANTARC"
        product_dir = (
            f"{self.config['product_base_dir']}/{self.config['baseline'].upper()}/"
            f"{self.config['version']:03d}/LAND_ICE/{zone_str}/{start_year}/{start_month:02d}"
        )

        log.info("product dir: %s", product_dir)

        # ---------------------------------------------------------------------
        #  Make product directory
        # ---------------------------------------------------------------------

        if not os.path.isdir(product_dir):
            try:
                os.makedirs(product_dir)
            except OSError as exc:
                mplog.error("[f%d] could not create %s : %s", filenum, product_dir, exc)
                return (False, "could not create {product_dir} {exc}")

        # ---------------------------------------------------------------------
        #  Form product filename
        #  Filename requirements: CS_OFFL_SIR_TDP_LI_<ANTARC,GREENL>_<STARTTIME>_
        #                        <ENDTIME>_<CC>_<OOOOO>_<BVVV>.nc
        #     <STARTTIME>, <ENDTIME>=yyyymmddThhmmss
        # ---------------------------------------------------------------------

        cycle_number = l1b.cycle_number
        abs_orbit_number = l1b.abs_orbit_number
        rel_orbit_number = l1b.rel_orbit_number

        # Form <STARTTIME> string
        start_seconds = time_utc_dt[0].second
        start_minutes = time_utc_dt[0].minute
        start_hours = time_utc_dt[0].hour
        start_microsecs = time_utc_dt[0].microsecond
        if start_microsecs > 500000:
            start_seconds += 1
            if start_seconds == 60:
                start_seconds = 0
                start_minutes += 1
                if start_minutes == 60:
                    start_minutes = 0
                    start_hours += 1

        start_time_str = (
            f"{time_utc_dt[0].year:4d}{time_utc_dt[0].month:02d}{time_utc_dt[0].day:02d}"
            f"T{start_hours:02d}{(start_minutes):02d}{start_seconds:02d}"
        )

        # Form <ENDTIME> string
        end_seconds = time_utc_dt[-1].second
        end_minutes = time_utc_dt[-1].minute
        end_hours = time_utc_dt[-1].hour
        end_microsecs = time_utc_dt[-1].microsecond
        if end_microsecs > 500000:
            end_seconds += 1
            if end_seconds == 60:
                end_seconds = 0
                end_minutes += 1
                if end_minutes == 60:
                    end_minutes = 0
                    end_hours += 1

        end_time_str = (
            f"{time_utc_dt[-1].year:4d}{time_utc_dt[-1].month:02d}{time_utc_dt[-1].day:02d}"
            f"T{end_hours:02d}{(end_minutes):02d}{end_seconds:02d}"
        )

        product_filename = (
            f"{product_dir}/CS_OFFL_SIR_TDP_LI_{zone_str}_{start_time_str}_{end_time_str}_"
            f"{cycle_number:02d}_{rel_orbit_number:05d}_"
            f"{self.config['baseline'].upper()}{self.config['version']:03d}.nc"
        )

        mplog.info(
            "[f%d] product filename=%s", filenum, os.path.basename(product_filename)
        )
        mplog.info("[f%d] product path=%s", filenum, product_filename)

        # -------------------------------------------------------------------
        # Open NetCDF file for write
        # -------------------------------------------------------------------

        try:
            dset = Dataset(product_filename, "w", format="NETCDF4")
        except OSError as exc:
            mplog.error(
                "[f%d] Can not open netcdf file for write %s %s",
                filenum,
                product_filename,
                exc,
            )
            return (
                False,
                f"Can not open netcdf file {product_filename} for write: {exc}",
            )

        # -----------------------------------------
        # Create Global Attributes
        # ------------------------------------------

        prod_longitudes = (shared_dict["longitudes"] + 180) % 360 - 180
        # convert to -180,180

        dset.title = "Cryo-TEMPO Land Ice Thematic Product"
        dset.project = "ESA Cryo-TEMPO"
        dset.creator_name = "ESA Cryo-TEMPO Project"
        dset.creator_url = "http://cryosat.mssl.ucl.ac.uk/tempo"
        now = datetime.now()
        dset.date_created = now.strftime("%d-%m-%Y %H:%M:%S")
        dset.platform = "CryoSat-2"
        dset.sensor = "SIRAL"
        if shared_dict["instr_mode"] == "LRM":
            dset.instrument_mode = "LRM"
        if shared_dict["instr_mode"] == "SAR":
            dset.instrument_mode = "SAR"
        if shared_dict["instr_mode"] == "SIN":
            dset.instrument_mode = "SARIN"

        dset.src_esa_l1b_file = os.path.basename(shared_dict["l1b_file_name"])

        # find start of ascending and descending parts of track
        asc_start, desc_start = find_orbit_directions(shared_dict["lats_nadir"])

        if asc_start is None:
            dset.ascending_start_record = "None"
        else:
            dset.ascending_start_record = np.int32(asc_start)
        if desc_start is None:
            dset.descending_start_record = "None"
        else:
            dset.descending_start_record = np.int32(desc_start)

        dset.geospatial_lat_min = f"{np.min(shared_dict['latitudes']):.4f}"
        dset.geospatial_lat_max = f"{np.max(shared_dict['latitudes']):.4f}"
        dset.geospatial_lon_min = f"{np.min(prod_longitudes):.4f}"
        dset.geospatial_lon_max = f"{np.max(prod_longitudes):.4f}"
        dset.geospatial_vertical_min = f"{np.nanmin(shared_dict['height_20_ku']):.4f}"
        dset.geospatial_vertical_max = f"{np.nanmax(shared_dict['height_20_ku']):.4f}"

        measurement_start_time = datetime(2000, 1, 1, 0) + timedelta(
            seconds=time_utc_secs[0]
        )
        measurement_end_time = datetime(2000, 1, 1, 0) + timedelta(
            seconds=time_utc_secs[-1]
        )

        dset.time_coverage_start = f"{measurement_start_time}"
        dset.time_coverage_end = f"{measurement_end_time}"
        dset.cycle_number = cycle_number
        dset.rel_orbit_number = rel_orbit_number
        dset.abs_orbit_number = abs_orbit_number
        dset.product_baseline = self.config["baseline"]
        dset.product_version = np.int32(self.config["version"])
        dset.doi = "10.5270/CR2-3205d1e"

        # Record the GIT version of this software

        dset.sw_version = get_current_commit_hash()

        # Add CNES sub-cycle. Need to check what to do after orbit change in Jul 2020
        cnes_subcycle, cnes_track = cnes_cycle_to_subcycle(
            cycle_number, rel_orbit_number
        )
        dset.cnes_subcycle = np.int32(cnes_subcycle)
        dset.cnes_track = np.int32(cnes_track)

        dset.Conventions = "CF-1.8"

        if shared_dict["hemisphere"] == "south":
            dset.zone = "Antarctica"
        else:
            dset.zone = "Greenland"

        # -----------------------------------------
        # Create Dimensions
        # ------------------------------------------

        _ = dset.createDimension("time", len(time_utc_secs))  # time_dim

        # -----------------------------------------
        # Create Variables
        #    - time
        #    - latitude
        #    - longitude
        #    - instrument_mode
        #    - elevation
        # ------------------------------------------

        # Time
        nc_var = dset.createVariable("time", "double", ("time",))
        nc_var.units = "UTC seconds since 00:00:00 1-Jan-2000"
        nc_var.coordinates = "time"
        nc_var.long_name = "utc time"
        nc_var.standard_name = "time"
        nc_var.comment = (
            "UTC time counted in seconds since 2000-01-01 00:00:00. Note that Cryo-TEMPO "
            "adjusts the TAI time found in CryoSat L1b products for leap seconds to "
            "produce UTC time"
        )
        nc_var[:] = time_utc_secs

        # Latitude
        nc_var = dset.createVariable("latitude", "double", ("time",))
        nc_var.units = "degrees north"
        nc_var.coordinates = "time"
        nc_var.long_name = (
            "latitude of measurement at POCA or nadir (if no POCA available)"
        )
        nc_var.standard_name = "latitude"
        nc_var.valid_min = -90
        nc_var.valid_max = 90
        nc_var.comment = (
            "Latitude of measurement in decimal degrees; a positive latitude indicates "
            "Northern hemisphere a negative latitude indicates Southern hemisphere. "
            "If the point of closest approach (POCA) can not be calculated by the SIRAL "
            "instrument in SARin mode or by LRM slope correction, then the nadir "
            "latitude is provided"
        )
        nc_var[:] = shared_dict["latitudes"]

        # Longitude
        nc_var = dset.createVariable("longitude", "double", ("time",))
        nc_var.units = "degrees east"
        nc_var.coordinates = "time"
        nc_var.long_name = (
            "longitude of measurement at POCA or nadir (if no POCA available)"
        )
        nc_var.standard_name = "longitude"
        nc_var.valid_min = -180
        nc_var.valid_max = 180
        nc_var.comment = (
            "Longitude of measurement in decimal degrees east (-180,180) relative to the "
            "Greenwich meridian. If the point of closest approach (POCA) can not be "
            "calculated by the SIRAL instrument in SARin mode or by LRM slope correction, "
            "then the nadir longitude is provided"
        )
        nc_var[:] = prod_longitudes

        # Instrument_mode
        nc_var = dset.createVariable(
            "instrument_mode", np.byte, ("time",), fill_value=-128
        )
        nc_var.coordinates = "longitude latitude"
        nc_var.long_name = "CryoSat SIRAL instrument operating mode"
        nc_var.flag_values = "1b, 2b, 3b"
        nc_var.valid_min = 1
        nc_var.valid_max = 3
        nc_var.flag_meanings = "lrm sar sarin"
        nc_var.comment = (
            "Identifier used to indicate which mode the SIRAL instrument was operating"
            " in at each measurement;"
            " either LRM, SAR or SARIn."
        )
        if shared_dict["instr_mode"] == "LRM":
            nc_var[:] = np.full_like(time_20_ku, 1, dtype="b")
        elif shared_dict["instr_mode"] == "SIN":
            nc_var[:] = np.full_like(time_20_ku, 3, dtype="b")
        else:
            nc_var[:] = np.full_like(time_20_ku, 2, dtype="b")

        # Elevation
        nc_var = dset.createVariable("elevation", "double", ("time",))
        nc_var.units = "m"
        nc_var.coordinates = "longitude latitude"
        nc_var.long_name = "ice sheet elevation (LMC Retracker)"
        nc_var.standard_name = "height_above_reference_ellipsoid"
        nc_var.comment = (
            "Elevation of the ice surface above the reference ellipsoid (WGS84) at the "
            "measurement location [longitude] [latitude]. "
            "All instrumental and appropriate geophysical corrections included. "
            "Corrected for surface slope via a slope model in LRM mode. Corrected for "
            "surface slope via phase information in SARIn mode. "
            "Where elevation can not be calculated, the value is set to Nan."
        )
        nc_var[:] = shared_dict["height_20_ku"]

        # ----------------------------------------------------------------
        # Close netCDF dataset
        dset.close()

        # Return success (True,'')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
