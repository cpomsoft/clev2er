""" clev2er.algorithms.cryotempo.alg_template """

# These imports required by Algorithm template
import logging

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
    """Algorithm to **identify L1b file**,

    1. find the instrument mode
    2. find the number of records

    **Contribution to shared dictionary**

    - shared_dict["instr_mode"]
    - shared_dict["num_20hz_records"]

    """

    def __init__(self, config) -> None:
        """initializes the Algorithm

        Args:
            config (dict): configuration dictionary

        Returns: None
        """
        self.alg_name = __name__
        self.config = config

        log.debug(
            "Initializing algorithm %s",
            self.alg_name,
        )

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        if config["chain"]["use_multi_processing"]:
            return

        self.init()

    def init(self) -> None:
        """Algorithm initialization

        Returns: None
        """

    @Timer(name=__name__, text="", logger=None)
    def process(self, l1b, shared_dict, mplog, filenum):
        """Algorithm to set:

        shared_dict["num_20hz_records"]
        shared_dict["instr_mode"]

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog: multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        > **IMPORTANT NOTE**: when logging within this function you must use the mplog logger
        with a filenum as an argument as follows:
            `mplog.error("[f%d] your message",filenum)`
        This is required to support logging during multi-processing
        """

        # When using multi-processing it is faster to initialize the algorithm
        # within each Algorithm.process(), rather than once in the main process's
        # Algorithm.__init__().
        # This avoids having to pickle the initialized data arrays (which is extremely slow)
        if self.config["chain"]["use_multi_processing"]:
            self.init()

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

        try:
            number_20hz_records = l1b["lat_20_ku"].size
        except KeyError:
            mplog.error("[f%d] lat_20_ku could not be read", filenum)
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
            mplog.error("[f%d] %s", filenum, error_str)
            return (False, error_str)

        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
