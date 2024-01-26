"""Create IBCAO background from

IBCAO_v4_2_400m.nc

gdalwarp IBCAO_v4_2_400m.tif IBCAO_v4_2_400m_3413.tif -s_srs EPSG:3996 -t_srs EPSG:3413

IBCAO_v4_2_400m_3413.tif

"""

import os
import sys

import numpy as np
import rasterio  # to extract GeoTIFF extents
from rasterio.errors import RasterioIOError
from tifffile import imread  # to support large TIFF files

from clev2er.utils.masks.masks import Mask


def get_geotiff_extent(fname: str):
    """Get info from GeoTIFF on its extent

    Args:
        fname (str): path of GeoTIFF file

    Raises:
        ValueError: _description_
        IOError: _description_

    Returns:
        tuple(int,int,int,int,int,int,int): width,height,top_left,top_right,bottom_left,
        bottom_right,pixel_width
    """
    try:
        with rasterio.open(fname) as dataset:
            transform = dataset.transform
            width = dataset.width
            height = dataset.height

            top_left = transform * (0, 0)
            top_right = transform * (width, 0)
            bottom_left = transform * (0, height)
            bottom_right = transform * (width, height)

            pixel_width = transform[0]
            pixel_height = -transform[4]  # Negative because the height is
            # typically negative in GeoTIFFs
            if pixel_width != pixel_height:
                raise ValueError(f"pixel_width {pixel_width} != pixel_height {pixel_width}")
    except RasterioIOError as exc:
        raise IOError(f"Could not read GeoTIFF: {exc}") from exc
    return (
        width,
        height,
        top_left,
        top_right,
        bottom_left,
        bottom_right,
        pixel_width,
    )


INPUT_FILE = "/cpdata/RESOURCES/backgrounds/IBCAO_v4_2_400m_3413.tif"

(
    ncols,
    nrows,
    top_l,
    top_r,
    bottom_l,
    _,
    binsize,
) = get_geotiff_extent(INPUT_FILE)

zdem = imread(INPUT_FILE)
if not isinstance(zdem, np.ndarray):
    raise TypeError(f"Input dem {INPUT_FILE} type read by imread not supported")

# Set void data to Nan
void_data = np.where(zdem == 9999)
if np.any(void_data):
    zdem[void_data] = np.nan

xdem = np.linspace(top_l[0], top_r[0], ncols, endpoint=True)
ydem = np.linspace(bottom_l[1], top_l[1], nrows, endpoint=True)
ydem = np.flip(ydem)
mindemx = xdem.min()
mindemy = ydem.min()

zdem = imread(INPUT_FILE)

SAMPLING = 16
RESOLUTION = "low"

xdem = xdem[::SAMPLING]
ydem = ydem[::SAMPLING]
zdem = zdem[::SAMPLING, ::SAMPLING].astype(float)  # type: ignore

thismask = Mask("greenland_bedmachine_v3_grid_mask")

print("masking dem...")
xp = []
yp = []
for x in xdem:
    for y in ydem:
        xp.append(x)
        yp.append(y)

inmask, _ = thismask.points_inside(xp, yp, basin_numbers=[0], inputs_are_xy=True)
print("masking done...")
ii = 0
for i, x in enumerate(xdem):
    for j, y in enumerate(ydem):
        if not inmask[ii]:
            zdem[j, i] = np.nan
        ii += 1


X, Y = np.meshgrid(xdem, ydem)


# Save DEM as .npz file
bgfile = f'{os.environ["CPDATA_DIR"]}/resources/backgrounds/IBCAO_v4.2_bathymetry_{RESOLUTION}.npz'

try:
    np.savez(
        bgfile,
        X=X,
        Y=Y,
        zdem=zdem,
        name="ibcso_bed_topo",
        src_tiff="IBCAO_v4_2_400m.tif",
        southern_hemisphere=True,
    )
except OSError as e:
    sys.exit(f"Error, Could not save .npz file {bgfile}: {e}")

print(f"New .npz file generated : {bgfile}")
