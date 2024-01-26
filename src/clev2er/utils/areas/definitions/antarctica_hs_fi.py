"""
# Area definition

## Summary: 
Based on area: antarctica
**background_image: hillshade**
**Data mask: floating ice from bedmachine v2**

"""
area_definition = {
    "use_definitions_from": "antarctica_hs",
    # --------------------------------------------
    #    mask from clev2er.utils.masks.Mask
    # --------------------------------------------
    "apply_area_mask_to_data": True,  # filter data using areas clev2er.utils.masks.Mask
    "maskname": "antarctica_bedmachine_v2_grid_mask",  # from  clev2er.utils.masks.Mask
    "masktype": "grid",  # mask is a polar stereo grid of Nkm resolution
    "basin_numbers": [3],  # [n1,n2,..] if mask allows basin numbers
    # for bedmachine v2, 2=grounded ice, 3=floating, 4=vostok
    "show_polygon_mask": False,  # show mask polygon
    "polygon_mask_color": "red",  # color to draw mask polygon
}
