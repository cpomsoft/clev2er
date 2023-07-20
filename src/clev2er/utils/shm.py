"""
A test of loading DEMs using shared memory
"""
import logging
from multiprocessing import Process

from clev2er.utils.dems.dems import Dem
from clev2er.utils.logging_funcs import get_logger


# task executed in a child process
def task():
    """
    child process
    """
    lats = [-77]
    lons = [106]
    print("In child")
    thisdem2 = Dem("rema_ant_1km", store_in_shared_memory=True)
    dem_elevs = thisdem2.interp_dem(lats, lons, xy_is_latlon=True)
    print("child: dem_elevs = ", dem_elevs)
    print(f"child: {thisdem2.name}")
    thisdem2.clean_up()


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

    thisdem = Dem("rema_ant_1km", store_in_shared_memory=True)

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

    thisdem.clean_up()

    # # close the shared memory
    # sm.close()
    # # release the shared memory
    # sm.unlink()
