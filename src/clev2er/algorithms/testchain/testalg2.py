""" clev2er.algorithms.cryotempo.alg_template"""

import logging
from typing import Any, Dict, Tuple

from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to do...**.

    **Contribution to shared dictionary**

        - shared_dict['param'] : (type), param description
    """

    def __init__(
        self, config: Dict[str, Any], process_number: int, alg_log: logging.Logger
    ) -> None:
        """
        Args:
            config (dict): configuration dictionary
            process_number (int): process number used for this algorithm (0..max_processes)
                                  similar but not the same as the os pid (process id)
                                  for sequential processing this would be 0 (default)
            alg_log (logging.Logger) : log instance to use for logging within algorithm

        Returns:
            None
        """
        self.alg_name = __name__
        self.config = config
        self.procnum = process_number
        self.log = alg_log

        _, _ = self.init()

    def init(self) -> Tuple[bool, str]:
        """Algorithm initialization template

        Returns:
            (bool,str) : success or failure, error string

        Raises:
            KeyError : keys not in config
            FileNotFoundError :
            OSError :

        Note: raise and Exception rather than just returning False
        Logging: use self.log.info,error,debug(your_message)
        """
        self.log.debug("Initializing algorithm %s", self.alg_name)

        # Check for special case where we create a shared memory
        # version of the DEM's arrays. Note this _init_shared_mem config setting is set by
        # run_chain.py and should not be included in the config files
        # typical usage in init() function for Dem and Mask objects:
        #    thismask=Mask(...,store_in_shared_memory=init_shared_mem)
        #    thisdem=Dem(...,store_in_shared_memory=init_shared_mem)
        init_shared_mem = "_init_shared_mem" in self.config

        # -----------------------------------------------------------------
        #  \/ Place Algorithm initialization steps here \/
        # -----------------------------------------------------------------

        if init_shared_mem:  # dummy statement to avoid lint warnings
            pass  # remove in real algorithm

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(
        self, l1b: Dataset, shared_dict: dict, filenum: int
    ) -> Tuple[bool, str]:
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        **IMPORTANT NOTE:**

        Logging: must use self.log.info,error,debug(your_message)

        """

        self.log.info(
            "Processing algorithm %s for file %d",
            self.alg_name.rsplit(".", maxsplit=1)[-1],
            filenum,
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            self.log.error(
                "l1b parameter is not a netCDF4 Dataset type for file %d",
                filenum,
            )
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to be passed
        # \/    down the chain in the 'shared_dict' dict     \/
        # -------------------------------------------------------------------

        shared_dict["dummy"] = True  # example

        # Return success (True,'')
        return (True, "")

    def finalize(self, stage: int = 0):
        """Perform final clean up actions for algorithm

        Args:
            stage (int, optional): Can be set to track at what stage the
            finalize() function was called
        """

        self.log.info(
            "Finalize algorithm %s called at stage %d",
            self.alg_name,
            stage,
        )

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # Important : free any shared memory resources used here

        # --------------------------------------------------------
