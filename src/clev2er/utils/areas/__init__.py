"""
# Area Definitions and Map Plotting

Contains utility classes to handle plotting of predefined polar (or other) areas

## Area Definitions

Area definitions define

 - Area projection
 - Area extent
 - Data mask applied when plotting data over the area
 - Plot background

Area definitions are each stored in a python dictionary within a separate file:

  $CLEV2ER_BASE_DIR/src/clev2er/utils/areas/definitions/**area_name.py**

The area naming convention used is as follows:

**area**&#95;*background*&#95;*datamask*.py  where *background* and *datamask* are optional.

| area_name | Background | Mask |
|--|--|--|
| antarctica |  basic_land	| None |
| antarctica_is | basic_land | antarctica_bedmachine_v2_grid_mask[2,4] == grounded ice sheet |
| antarctica_fi | basic_land | floating ice only : bedmachine mask|
| antarctica_hs_is | hillshade | antarctica_bedmachine_v2_grid_mask[2,4] == grounded ice sheet |
| antarctica_hs_fi | hillshade | floating ice only : bedmachine mask|
| greenland |  basic_land	| None |
| greenland_is | basic_land | antarctica_bedmachine_v2_grid_mask[2,4] == grounded ice sheet |
| greenland_fi | basic_land | floating ice only : bedmachine mask|
| greenland_hs_is | hillshade | antarctica_bedmachine_v2_grid_mask[2,4] == grounded ice sheet |
| greenland_hs_fi | hillshade | floating ice only : bedmachine mask|

"""
