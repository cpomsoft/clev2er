""" clev2er.algorithms.base.base_alg"""

import logging
from typing import Any, Dict, Tuple

from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class BaseAlgorithm:
    """**Algorithm to do...**.

    **Contribution to shared dictionary**

        - shared_dict['param'] : (type), param description
    """

    def __init__(self, config: Dict[str, Any], thislog: logging.Logger | None) -> None:
        """
        Runs init() if not in multi-processing mode
        Args:
            config (dict): configuration dictionary
            log (logging.Logger): initial log instance to use for this algorithm

        Returns:
            None
        """
        self.alg_name = __name__
        self.config = config
        if thislog is not None:
            self.log = thislog
        else:
            self.log = log
        self.filenum = 0
        self.initialized = False

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        # If using shared memory, then the init() is done at this stage (but in
        # separate Algorithm's that are not parallelized)
        if config["chain"]["use_multi_processing"]:
            # only continue with initialization if setting up shared memory
            if not config["chain"]["use_shared_memory"]:
                return
            if "_init_shared_mem" not in config:
                return

        _, _ = self.init()
        self.initialized = True

    def init(self) -> Tuple[bool, str]:
        """Algorithm initialization template

        Returns:
            (bool,str) : success or failure, error string

        Note: raise and Exception rather than just returning False
        """

        return (True, "")

    def set_log(self, thislog: logging.Logger) -> None:
        """function to set the logger to use within this algorithm

        Args:
            log (logging.Logger): assign the logging instance to use for this algorithm

        Returns: None

        """
        self.log = thislog

    def set_filenum(self, filenum: int) -> None:
        """set the current file number (0..(max_files-1))

        Args:
            filenum (int): current file number being processed

        Returns: None

        """

        self.filenum = filenum

    @Timer(name=__name__, text="", logger=None)
    def process_setup(self, l1b: Dataset) -> Tuple[bool, str]:
        """common pre-processor which tests the L1b Dataset is valid
           and also runs BaseAlgorithm.init() if in multi-processing mode
           This should be run as a first step inside Algorithm.process()

            `success, error_str = self.process_setup(l1b)`


        Args:
            l1b (Dataset): input l1b file dataset (constant)

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')
        """

        # When using multi-processing it is faster to initialize the algorithm
        # within each Algorithm.process(), rather than once in the main process's
        # Algorithm.__init__().
        # This avoids having to pickle the initialized data arrays (which is very slow)
        if self.config["chain"]["use_multi_processing"]:
            rval, error_str = self.init()
            if not rval:
                return (rval, error_str)
            self.initialized = True

        self.log.info(
            "Processing algorithm: %s",
            self.alg_name.rsplit(".", maxsplit=1)[-1],
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            self.log.error("l1b parameter is not a netCDF4 Dataset type")
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to be passed
        # \/    down the chain in the 'shared_dict' dict     \/
        # -------------------------------------------------------------------

        # Return success (True,'')
        return (True, "")

    def finalize(self, stage: int = 0) -> None:
        """Perform final clean up actions for algorithm

        Args:
            stage (int, optional): Can be set to track at what stage the
            finalize() function was called
        """
        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # Important : free any shared memory resources used here

        # --------------------------------------------------------
        self.log.info("Finalize run for %s at stage %d", self.alg_name, stage)
