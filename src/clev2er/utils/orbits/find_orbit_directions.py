"""
find direction of track from nadir latitudes
"""
from __future__ import annotations

import numpy as np


def find_orbit_directions(lats: np.ndarray) -> tuple[int | None, int | None]:
    """
    Returns index of the start of ascending orbit and/or desc orbit
    or None
    Args:
        lats (np.ndarray) : array of latitude values
    """
    asc_start = None
    desc_start = None

    n_vals = len(lats)

    # find direction at start of track

    if n_vals < 2:
        return None, None

    if lats[1] > lats[0]:
        asc_start = 0
    else:
        desc_start = 0

    index = 1
    while index < n_vals - 1:
        if lats[index + 1] > lats[index]:
            if asc_start is None:
                asc_start = index
                break
        if lats[index] > lats[index + 1]:
            if desc_start is None:
                desc_start = index
                break
        index += 1

    return asc_start, desc_start
