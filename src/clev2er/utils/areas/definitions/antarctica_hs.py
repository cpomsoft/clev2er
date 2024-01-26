"""
# Area definition

## Summary: 
Based on area: antarctica
**background_image: hillshade**

"""
area_definition = {
    "use_definitions_from": "antarctica",
    # --------------------------------------------
    #    mask from clev2er.utils.masks.Mask
    # --------------------------------------------
    "background_image": [
        "ibcso_bathymetry",
        "hillshade",
    ],
    "background_image_alpha": [0.14, 0.18],
    "background_color": "white",
}
