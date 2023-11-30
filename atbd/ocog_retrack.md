---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# OCOG retracking

This page describes OCOG retracking.

## TCOG Retrack

The following code creates a step-function waveform and performs a TCOG retrack upon it, with default settings.

```{code-cell}
import sys
sys.path.append("../src")
from clev2er.utils.cs2.retrackers.cs2_tcog_retracker import (
    retrack_tcog_waveforms_cs2,
)
import numpy as np
import matplotlib.pyplot as plt
from myst_nb import glue

wfs = np.zeros((1,128))
wfs[0,64:] = 65534.0
glue('wfs', wfs, display=False)

dr_bin_tcog,dr_meters_tcog,leading_edge_start,leading_edge_stop,pwr_at_rtrk_point_tcog,n_retracker_failures,retrack_flag=\
retrack_tcog_waveforms_cs2(waveforms=wfs,
                             retrack_threshold_lrm=0.2,
                             retrack_threshold_sin=0.5,
                             debug_flag=False,
                             plot_flag=0,
                             measurement_index=None)
print(dr_bin_tcog,dr_meters_tcog,leading_edge_start,leading_edge_stop,  n_retracker_failures)
glue('dr_bin_tcog', float(dr_bin_tcog), display=False)
glue('pwr_at_rtrk_point_tcog', float(pwr_at_rtrk_point_tcog), display=False)

fig, ax = plt.subplots()
plt.plot(wfs[0,:], color='red')
plt.axvline(x=64.0+dr_bin_tcog)
plt.axhline(y=pwr_at_rtrk_point_tcog)
ax.set_title("Annotated TCOG retrack")

glue("tcog_fig", fig, display=False)
# Closing the plot prevents it from being displayed as cell output and allows us to glue it in when we want
plt.close()

```

The retracking delta in bins was {glue:text}`dr_bin_tcog:.2f` and the power at the retracking point was {glue:text}`pwr_at_rtrk_point_tcog:.2f`.

If we annotate the step function with the retrack point and the retrack power, we get the figure below.

```{glue:figure} tcog_fig
:figwidth: 600px
:name: "fig-tcog"

The annotated TCOG retrack.
```

Referring to the included figure, it is {ref}`here <fig-tcog>`.

```{literalinclude} ../src/clev2er/utils/cs2/retrackers/cs2_tcog_retracker.py
:lines: 92-793
```

The end.