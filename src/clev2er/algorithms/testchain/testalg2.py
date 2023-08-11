""" clev2er.algorithms.templates.alg_template"""

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
            # only continue with initialization if setting up shared memory
            if not config["chain"]["use_shared_memory"]:
                return
            if "_init_shared_mem" not in config:
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

        # Check for special case where we create a shared memory
        # version of the DEM's arrays. Note this _init_shared_mem config setting is set by
        # run_chain.py and should not be included in the config files
        init_shared_mem = "_init_shared_mem" in self.config

        # if  init_shared_mem, perform any specific shared memory initialization
        # in Dem or Mask classes.
        # ie thismask=Mask(...,store_in_shared_memory=init_shared_mem)
        #    thisdem=Dem(...,store_in_shared_memory=init_shared_mem)

        if init_shared_mem:  # remove this in real algorithm
            pass

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

        shared_dict["dummy"] = True  # example

        # Return success (True,'')
        return (True, "")

    def finalize(self, stage: int = 0):
        """Perform final clean up actions for algorithm

        Args:
            stage (int, optional): Can be set to track at what stage the
            finalize() function was called
        """

        log.debug("Finalize algorithm %s called at stage %d", self.alg_name, stage)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # Important : free any shared memory resources used here

        # --------------------------------------------------------
