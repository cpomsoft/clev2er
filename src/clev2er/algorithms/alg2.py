""" clev2er.algorithms.alg1 """
import logging

log = logging.getLogger(__name__)


class Algorithm:
    """Clev2er algorithm"""

    def __init__(self, config):
        """initializes the Algorithm

        Args:
            config (dict): configuration dictionary
        """
        self.alg_name = __name__
        log.info("Initializing algorithm %s", {self.alg_name})

    def process(self, l1b, working):
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            working (dict): working data passed between algorithms
            config (dict): configuration data

        Returns:
            Tuple : (rejected (bool), reason (str))
        """

        log.info("Processing algorithm %s", {self.alg_name})

        # Modify the working dict

        working["lats"] = [1, 2, 3, 4]

        return (True, "alg1 Failed")

    def finalize(self):
        log.info("Finalize algorithm %s", {self.alg_name})
