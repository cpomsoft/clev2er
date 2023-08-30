""" clev2er.algorithms.cryotempo.alg_template """

# These imports required by Algorithm template
from typing import Tuple

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """Algorithm to **identify L1b file**,

    1. find the instrument mode
    2. find the number of records

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)
    **Contribution to shared dictionary**

    - shared_dict["instr_mode"]
    - shared_dict["num_20hz_records"]

    """

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

        # Add initialization steps here

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

        try:
            number_20hz_records = l1b["lat_20_ku"].size
        except KeyError:
            self.log.error("lat_20_ku could not be read")
            return (False, "lat_20_ku could not be read")

        shared_dict["num_20hz_records"] = number_20hz_records

        error_str = ""
        try:
            if "LRM" in l1b.sir_op_mode:
                shared_dict["instr_mode"] = "LRM"
            elif "SARIN" in l1b.sir_op_mode:
                shared_dict["instr_mode"] = "SIN"
            elif "SAR" in l1b.sir_op_mode:
                shared_dict["instr_mode"] = "SAR"
            else:
                error_str = (
                    f"Invalid mode attribute .sir_op_mode in L1b file {l1b.sir_op_mode}"
                )
        except AttributeError:
            error_str = "Missing attribute .sir_op_mode in L1b file"

        if error_str:
            self.log.error("%s", error_str)
            return (False, error_str)

        return (True, "")

    # No finalize() required
