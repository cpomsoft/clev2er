""" clev2er.algorithms.templates.alg_template"""

import logging
import os
import subprocess
import time
from datetime import datetime, timedelta  # date and time functions
from typing import Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.orbits.find_orbit_directions import find_orbit_directions
from clev2er.utils.time.grain import Grain

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements


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


def get_current_commit_hash(log: logging.Logger) -> str:
    """retrieve the current git commit version
       or None if not available

    Args:
        log (logging.Logger) : current log instance to use

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


class Algorithm(BaseAlgorithm):
    """Algorithm to write L2 CryoTEMPO output files

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

    **Contribution to shared dictionary**

    shared_dict['product_filename']: (str), path of L2 Cryo-Tempo product file created

    """

    # Note: __init__() is in BaseAlgorithm. See required parameters above
    # init() below is called by __init__() at a time dependent on whether
    # sequential or multi-processing mode is in operation

    def init(self) -> Tuple[bool, str]:
        """Algorithm initialization

        Add steps in this function that are run once at the beginning of the chain
        (for example loading a DEM or Mask)

        Returns:
            (bool,str) : success or failure, error string

        Raises:
            KeyError : keys not in config
            FileNotFoundError :
            OSError :

        Note: raise and Exception rather than just returning False
        """
        self.alg_name = __name__
        self.log.info("Algorithm %s initializing", self.alg_name)

        # -----------------------------------------------------------------
        #  \/ Place Algorithm initialization steps here \/
        # -----------------------------------------------------------------

        # Get leap seconds list

        if "leap_seconds" not in self.config:
            self.log.error("leap_seconds not in config dict")
            raise KeyError("leap_seconds not in config dict")

        self.leap_seconds_file = self.config["leap_seconds"]
        if not os.path.isfile(self.leap_seconds_file):
            self.log.error("leap_seconds file: %s not found", self.leap_seconds_file)
            raise FileNotFoundError(f"leap_seconds file {self.leap_seconds_file} not found")

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(self, l1b: Dataset, shared_dict: dict) -> Tuple[bool, str]:
        """Main algorithm processing function

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        **IMPORTANT NOTE:** when logging within the Algorithm.process() function you must use
        the self.log.info(),error(),debug() logger and NOT log.info(), log.error(), log.debug :

        `self.log.error("your message")`

        """

        # This is required to support logging during multi-processing
        success, error_str = self.process_setup(l1b)
        if not success:
            return (False, error_str)

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

        time_tai_dt = [(datetime(2000, 1, 1, 0) + timedelta(seconds=i)) for i in time_20_ku]
        time_utc_dt = [this_grain.tai2utc(i) for i in time_20_ku]
        diff_in_seconds = [
            (time_utc_dt[i] - time_tai_dt[i]).total_seconds() for i in range(len(time_tai_dt))
        ]
        time_utc_secs = time_20_ku + np.asarray(diff_in_seconds)

        start_month = time_utc_dt[0].month
        start_year = time_utc_dt[0].year

        self.log.info("start month %d %d", start_month, start_year)

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

        self.log.info("product dir: %s", product_dir)

        # ---------------------------------------------------------------------
        #  Make product directory
        # ---------------------------------------------------------------------

        if not os.path.isdir(product_dir):
            try:
                os.makedirs(product_dir)
            except OSError as exc:
                time.sleep(2)
                if not os.path.isdir(product_dir):
                    self.log.error("could not create %s : %s", product_dir, exc)
                    return (False, f"could not create {product_dir} {exc}")

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

        self.log.info("product filename=%s", os.path.basename(product_filename))
        self.log.info("product path=%s", product_filename)

        # -------------------------------------------------------------------
        # Open NetCDF file for write
        # -------------------------------------------------------------------

        try:
            dset = Dataset(product_filename, "w", format="NETCDF4")
        except OSError as exc:
            self.log.error(
                "Can not open netcdf file for write %s %s",
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

        measurement_start_time = datetime(2000, 1, 1, 0) + timedelta(seconds=time_utc_secs[0])
        measurement_end_time = datetime(2000, 1, 1, 0) + timedelta(seconds=time_utc_secs[-1])

        dset.time_coverage_start = f"{measurement_start_time}"
        dset.time_coverage_end = f"{measurement_end_time}"
        dset.cycle_number = cycle_number
        dset.rel_orbit_number = rel_orbit_number
        dset.abs_orbit_number = abs_orbit_number
        dset.product_baseline = self.config["baseline"]
        dset.product_version = np.int32(self.config["version"])
        dset.doi = "10.5270/CR2-3205d1e"

        # Record the GIT version of this software

        dset.sw_version = get_current_commit_hash(self.log)

        # Add CNES sub-cycle. Need to check what to do after orbit change in Jul 2020
        cnes_subcycle, cnes_track = cnes_cycle_to_subcycle(cycle_number, rel_orbit_number)
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
        nc_var.long_name = "latitude of measurement at POCA or nadir (if no POCA available)"
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
        nc_var.long_name = "longitude of measurement at POCA or nadir (if no POCA available)"
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
        nc_var = dset.createVariable("instrument_mode", np.byte, ("time",), fill_value=-128)
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
        nc_var[:] = shared_dict["height_filt"]  # use final filtered height

        # Backscatter (from sig0_20_ku)
        nc_var = dset.createVariable("backscatter", "double", ("time",))
        nc_var.units = "dB"
        nc_var.coordinates = "longitude latitude"
        nc_var.long_name = "backscatter coefficient"
        nc_var.standard_name = "surface_backscattering_coefficient_of_radar_wave"
        nc_var.comment = (
            "The measured backscatter from the surface, corrected for instrument effects, and "
            "including a system bias that calibrates the results against previous missions. "
            "The backscatter is computed from the amplitude of the waveform in Watts, "
            "as measured by the retracker. The measured power is used to solve the radar "
            "equation to recover the value for backscatter."
        )
        nc_var[:] = shared_dict["sig0_20_ku"]

        # surface_type
        nc_var = dset.createVariable("surface_type", np.byte, ("time",), fill_value=-128)
        nc_var.coordinates = "longitude latitude"
        nc_var.long_name = "surface type from mask"
        nc_var.flag_values = "0b, 1b, 2b, 3b, 4b"
        nc_var.valid_min = 0
        nc_var.valid_max = 4
        nc_var.flag_meanings = (
            "ocean grounded_ice floating_ice ice_free_land "
            "non_greenland_land(used for tracks over Greenland only)"
        )
        nc_var.comment = (
            "Surface type identifier, for use in discriminating different surfaces types "
            "within the Land Ice TDP domain; derived from the BedMachine Greenland version "
            "3 (Morlighem et al., 2017) and BedMachine Antarctica version 2 (Morlighem, 2020) "
            "datasets."
        )
        if shared_dict["hemisphere"] == "south":
            nc_var.source = "https://nsidc.org/data/nsidc-0756/versions/2"
        else:
            nc_var.source = "https://nsidc.org/data/idbmg4"
        nc_var[:] = shared_dict["cryotempo_surface_type"]

        # reference_dem
        nc_var = dset.createVariable("reference_dem", "double", ("time",))
        nc_var.units = "m"
        nc_var.coordinates = "longitude latitude"
        nc_var.long_name = "reference elevation from external Digital Elevation Model"
        nc_var.standard_name = "height_above_reference_ellipsoid"
        nc_var.comment = (
            "Reference elevation values at each measurement location, extracted from an "
            "auxiliary Digital Elevation Model (DEM). "
            "The 1km REMA v1.1 mosaic is used for Antarctica and the 1 km ArcticDEM v3 "
            "mosaic is used for Greenland."
        )
        nc_var[:] = shared_dict["dem_elevation_values"]

        # basin_id  : Zwally basins : values 0 (outside mask),
        # 1-27 (mask values for Antarctica), 1-19 (for Greenland)
        nc_var = dset.createVariable("basin_id", np.byte, ("time",), fill_value=-128)
        nc_var.units = "basin number"
        nc_var.long_name = "Glacialogical basin identification number"
        if shared_dict["hemisphere"] == "south":
            nc_var.comment = (
                "IMBIE glacialogical basin id number (Zwally et al., 2012) "
                "associated with each measurement. "
                "Values are : 0 (outside mask), 1-27 (basin values for Antarctica)"
            )
        else:
            nc_var.comment = (
                "IMBIE glacialogical basin id number (Zwally et al., 2012) "
                "associated with each measurement. "
                "Values 0 (outside mask), 1-19 (basin values for Greenland)"
            )
        nc_var.source = "IMBIE http://imbie.org/imbie-2016/drainage-basins/"
        nc_var[:] = shared_dict["basin_mask_values_zwally"]

        # basin_id2  :   Rignot basins : values 0 (outside mask), 1-19 Antarctica, 1-7 Greenland
        nc_var = dset.createVariable("basin_id2", np.byte, ("time",), fill_value=-128)
        nc_var.units = "basin number"
        nc_var.long_name = "Glacialogical basin identification number"
        if shared_dict["hemisphere"] == "south":
            nc_var.comment = (
                "IMBIE glacialogical basin id number (Rignot et al., 2016) associated "
                "with each measurement. Values are : 0 (unclassified), 1:Islands, "
                "2: West H-Hp, 3:West F-G, 4:East E-Ep, 5: East D-Dp, "
                "6: East Cp-D, 7: East B-C, 8: East A-Ap, 9: East Jpp-K, 10: West G-H,"
                " 11: East Dp-E, 12: East Ap-B, 13: East C-Cp, 14: East K-A, 15: West "
                "J-Jpp, 16: Peninsula Ipp-J, 17: Peninsula I-Ipp, 18: "
                "Peninsula Hp-I, 19: West Ep-F"
            )
        else:
            nc_var.comment = (
                "IMBIE glacialogical basin id number (Rignot et al., 2016) associated "
                "with each measurement. Values: 0 (unclassified), 1 (ice caps), "
                "2(NW Greenland), 3(CW Greenland), 4(SW Greenland), "
                "5(SE Greenland), 6(NE Greenland), 7(NO North Greenland)"
            )
        nc_var.source = "IMBIE http://imbie.org/imbie-2016/drainage-basins/"
        nc_var[:] = shared_dict["basin_mask_values_rignot"]

        # Uncertainty
        nc_var = dset.createVariable("uncertainty", "double", ("time",))
        nc_var.units = "m"
        nc_var.coordinates = "longitude latitude"
        nc_var.long_name = "uncertainty of elevation parameter"
        nc_var.standard_name = "elevation_uncertainty"
        nc_var.comment = (
            "Uncertainty associated with the ice sheet elevation measurement; defined as the "
            "precision measured at orbital cross-overs per 0.1 degree band of slope."
        )
        nc_var[:] = shared_dict["uncertainty"]

        # ----------------------------------------------------------------
        # Close netCDF dataset
        dset.close()

        shared_dict["product_filename"] = product_filename

        # Return success (True,'')
        return (True, "")


# No finalize() required for this algorithm
