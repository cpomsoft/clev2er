""" clev2er.algorithms.alg1 """
import logging
import time

from netCDF4 import Dataset  # pylint:disable=E0611

# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


class Algorithm:
    """Clev2er  algorithm"""

    def __init__(self, config):
        """initializes the Algorithm

        Args:
            config (dict): configuration dictionary
        """
        self.alg_name = __name__
        self.config = config

        log.debug(
            "Initializing algorithm %s",
            self.alg_name,
        )

    def process(self, l1b, working):
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            working (dict): working data passed between algorithms

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')
        """

        log.debug(
            "Processing algorithm %s",
            self.alg_name,
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            log.error("l1b parameter is not a netCDF4 Dataset type")
            return (True, "l1b parameter is not a netCDF4 Dataset type")

        # Modify the working dict

        working["lats"] = [1, 2, 3, 4]

        time.sleep(5)

        # Return success (True,'') or (Failure,'error string')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)
