"""
# Algorithms for the cryotempo land ice chain

Contains  algorithms for the ESA CryoTEMPO Project's land ice
theme. Algorithms are usually implemented in the order shown in the diagram below
(although the actual order is specified in the algorithm list 
used i.e. `$CLEV2ER_BASE_DIR/config/algorithm_lists/cryotempo.yml`).

Click on the algorithm names in the Submodules section to the left to view further
details on each Algorithm.

```mermaid
graph LR;
    AA(L1b)-->A
    A[alg_identify_file]-->B[alg_skip_on_mode]
    B-->C[alg_skip_on_area_bounds]
    C-->D[alg_dilated_coastal_mask]
```
```mermaid
graph LR;
    E[alg_cats2008a_tide_correction]-->F[alg_fes2014b_tide_correction]
    F-->G[alg_geo_corrections]
    G-->H[alg_waveform_quality]
```
```mermaid
graph LR;
    I[alg_retrack]-->J[alg_backscatter]
    J-->K[alg_geolocate_lrm]
    K-->L[alg_geolocate_sin]
    L-->M[alg_basin_ids]
    M-->N[alg_ref_dems]
    N-->O[alg_product_output]

```


"""
