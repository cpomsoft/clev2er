"""
A test of loading DEMs using shared memory
"""
import logging
from multiprocessing import Process

from clev2er.utils.logging_funcs import get_logger
from clev2er.utils.masks.masks import Mask


# task executed in a child process
def task():
    """
    child process
    """
    _lats = [-77, -60, 74.31]
    _lons = [106, 34, -40.61]
    _vals_inside = [1]
    print("In child")
    mask_name = "antarctica_bedmachine_v2_grid_mask"
    mask_name = "greenland_iceandland_dilated_10km_grid_mask"
    thismask2 = Mask(mask_name, store_in_shared_memory=True)

    _true_inside, _, _ = thismask2.points_inside(_lats, _lons, basin_numbers=_vals_inside)

    print("child: true_inside = ", _true_inside)
    print(f"child: {thismask2.mask_name}")
    thismask2.clean_up()


# protect the entry point
if __name__ == "__main__":
    # -------------------------------------------------------------------------
    # Setup logging
    #   - default log level is INFO unless --debug command line argument is set
    #   - default log files paths for error, info, and debug are defined in the
    #     main config file
    # -------------------------------------------------------------------------

    log = get_logger(
        default_log_level=logging.INFO,
        log_file_error="/tmp/errors.log",
        log_file_info="/tmp/info.log",
        log_file_debug="/tmp/debug.log",
        silent=False,
    )

    MASK_NAME = "antarctica_bedmachine_v2_grid_mask"
    MASK_NAME = "greenland_iceandland_dilated_10km_grid_mask"
    vals_inside = [1]

    thismask = Mask(MASK_NAME, store_in_shared_memory=True)

    lats = [-77, -60, 74.31]
    lons = [106, 34, 319.39]
    print("In parent")

    true_inside, _, _ = thismask.points_inside(lats, lons, basin_numbers=vals_inside)
    print("parent: true_inside = ", true_inside)
    print(f"parent: {thismask.mask_name}")

    # define the size of the numpy array
    # n = 10000
    # # bytes required for the array (8 bytes per value for doubles)
    # n_bytes = n * 8
    # # create the shared memory
    # sm = SharedMemory(name="MyMemory", create=True, size=n_bytes)
    # # create a new numpy array that uses the shared memory
    # data = ndarray((n,), dtype=numpy.double, buffer=sm.buf)
    # # populate the array
    # data.fill(1.0)
    # # confirm contents of the new array
    # print(data[:10], len(data))
    # create a child process

    child = Process(target=task)
    child2 = Process(target=task)
    # start the child process
    child.start()
    child2.start()

    # wait for the child process to complete
    child.join()
    child2.join()
    # check some data in the shared array
    # print(data[:10])

    thismask.clean_up()

    # # close the shared memory
    # sm.close()
    # # release the shared memory
    # sm.unlink()
