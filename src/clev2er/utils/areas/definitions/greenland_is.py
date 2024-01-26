"""
# Area definition

## Summary: 
Based on area: greenland
**Data mask: grounded ice from bedmachine v3**

"""
area_definition = {
    "use_definitions_from": "greenland",
    # --------------------------------------------
    #    mask from clev2er.utils.masks.Mask
    # --------------------------------------------
    "apply_area_mask_to_data": True,  # filter data using areas clev2er.utils.masks.Mask
    "maskname": "greenland_bedmachine_v3_grid_mask",  # from  clev2er.utils.masks.Mask
    "masktype": "grid",  # mask is a polar stereo grid of Nkm resolution
    "basin_numbers": [2],  # [n1,n2,..] if mask allows basin numbers
    # for bedmachine v3, 2=grounded ice, 3=floating
    "show_polygon_mask": False,  # show mask polygon
    "polygon_mask_color": "red",  # color to draw mask polygon
}
