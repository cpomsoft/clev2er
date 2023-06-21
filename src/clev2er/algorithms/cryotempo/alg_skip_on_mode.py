""" clev2er.algorithms.cryotempo.alg_skip_on_mode """
import logging

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to find the instrument mode in a CS2 L1b file**

    if mode is LRM or SIN, shared_dict['instr_mode] is set to 'LRM' or 'SIN'

    if mode is SAR, return (False,"SKIP_OK...")

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

        # --------------------------------------------------------
        # \/ Add algorithm initialization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------

    @Timer(name=__name__, text="", logger=None)
    def process(self, l1b, shared_dict, mplog, filenum):
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog: multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')
        """

        mplog.debug(
            "[f%d] Processing algorithm %s",
            filenum,
            self.alg_name,
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            mplog.error(
                "[f%d] File %d: l1b parameter is not a netCDF4 Dataset type",
                filenum,
                filenum,
            )
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        try:
            if shared_dict["instr_mode"] == "SAR":
                mplog.info("[f%d] skipping as SAR mode not required", filenum)
                return (False, "SKIP_OK: SAR mode file not required")
        except KeyError:
            mplog.error("[f%d] instr_mode not in shared_dict", filenum)
            return (False, "instr_mode not in shared_dict")

        # --------------------------------------------------------

        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
