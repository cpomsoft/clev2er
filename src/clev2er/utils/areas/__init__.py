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

| Area Name| Background | Data Mask |
|--|--|--|
| antarctica |  	|
| greenland |       |

"""
