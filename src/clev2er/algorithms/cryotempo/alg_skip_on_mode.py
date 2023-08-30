""" clev2er.algorithms.cryotempo.alg_skip_on_mode """

from typing import Tuple

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm

# Similar lines in 2 files, pylint: disable=R0801


class Algorithm(BaseAlgorithm):
    """**Algorithm to find the instrument mode in a CS2 L1b file**

    if mode is LRM or SIN, shared_dict['instr_mode] is set to 'LRM' or 'SIN'

    if mode is SAR, return (False,"SKIP_OK...")

    **Contribution to shared dictionary**

    None

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)
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
            if shared_dict["instr_mode"] == "SAR":
                self.log.info("skipping as SAR mode not required")
                return (False, "SKIP_OK: SAR mode file not required")
        except KeyError:
            self.log.error("instr_mode not in shared_dict")
            return (False, "instr_mode not in shared_dict")

        # --------------------------------------------------------

        return (True, "")

    # No finalize() required by algorithm
