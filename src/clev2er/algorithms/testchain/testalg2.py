""" clev2er.algorithms.testalg2 """
import logging

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


class Algorithm:
    """Clev2er  algorithm"""

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

        self.testdata = 2

        # --------------------------------------------------------

    @Timer(name=__name__)
    def process(self, l1b, working, mplog, filenum):
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            working (dict): working data passed between algorithms
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
            mplog.error("[f%d] l1b parameter is not a netCDF4 Dataset type", filenum)
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'working' dict
        # ie working["lats"] = [1, 2, 3, 4]
        # -------------------------------------------------------------------

        working[self.alg_name] = [self.testdata]

        # --------------------------------------------------------

        # Return success (True,'') or (Failure,'error string')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
