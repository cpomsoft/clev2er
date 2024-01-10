"""fastsmooth() : smoothing function port from Matlab"""
import numpy as np


def fastsmooth(input_array, smoothwidth):
    """
    port of Matlab fastsmooth function, Copyright (c) 2012, Thomas C. O'Haver
    https://uk.mathworks.com/matlabcentral/fileexchange/19998-fast-smoothing-function?s_tid=srchtitle
    with taper=1, edge=1 preset

    :param input_array:   input 1-d array to be smoothed
    :param smoothwidth: smoothing width
    :return: smoothed 1-d array
    """

    if smoothwidth == 0 or smoothwidth > len(input_array):
        return input_array
    length = len(input_array)
    if smoothwidth >= length:
        smoothwidth = length - 1

    width = np.around(smoothwidth)
    sum_points = np.sum(input_array[0:width])
    sss = [0 for i in range(len(input_array))]
    halfw = int(np.around(width / 2))

    for kkk in range(0, length - width):
        sss[kkk + halfw - 1] = sum_points
        sum_points = sum_points - input_array[kkk]
        sum_points = sum_points + input_array[kkk + width]

    sss[kkk + halfw] = np.sum(input_array[length - width + 1 : length])
    smoothed_input_array = sss / width

    # Taper the ends of the signal
    startpoint = int((smoothwidth + 1) / 2)

    smoothed_input_array[0] = (input_array[0] + input_array[1]) / 2.0
    for kkk in range(1, startpoint):
        smoothed_input_array[kkk] = np.sum(input_array[0 : (kkk * 2) + 1]) / ((kkk * 2) + 1)
        smoothed_input_array[length - 1 - kkk] = np.mean(
            input_array[length - 1 - (2 * kkk) + 1 : length - 1]
        )
    return smoothed_input_array
