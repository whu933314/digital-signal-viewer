# -*- coding: utf-8 -*-
"""Dump the 10 distinct analyzer spectra that dsv_mask.scope_spectra() rebuilds from the captured input signals, as %.17g text
(one row per bin, one column per channel), tagged with the numpy version — so exact_periodogram.py can measure this FFT
implementation's rounding against the high-precision reference.  Usage (from the ui folder, any python with numpy):
    python dump_dsv_spectra.py <ref_dir=tests/matlab_ref> <out_dir>
Writes <out_dir>/dsv_numpy_<version>/<spectrum basename> for every entry of captures.json's stored_spectra."""
import json
import os
import sys

import numpy as np

ref_dir, out_dir = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.getcwd())
import dsv_mask as M   # noqa: E402

d = os.path.join(ref_dir, "scope", "spectral_mask")
with open(os.path.join(d, "captures.json"), encoding="utf-8") as fh:
    C = json.load(fh)
fs = float(C["fs"])
sig = {}
for ds, info in C["signals"].items():
    arrs = []
    for fn in info["files"]:
        m = np.loadtxt(os.path.join(d, "signals", fn))
        arrs.append((m[:, 0] + 1j * m[:, 1])[:, None] if info["complex"] else m)
    sig[ds] = arrs
tag = "dsv_numpy_" + np.__version__
od = os.path.join(out_dir, tag)
os.makedirs(od, exist_ok=True)
done = set()
for cap in C["captures"]:
    L, N, two = cap["window_length"], cap["spectral_averages"], cap["two_sided"]
    foff = float(cap["scope_props_requested"].get("FrequencyOffset", 0))
    _, Ss = M.scope_spectra(sig[cap["dataset"]], fs, L, N, two, foffset=foff)
    for c, S in zip(cap["calls"], Ss):
        rel = c["spectrum_identical_to"]
        if rel in done:
            continue
        done.add(rel)
        np.savetxt(os.path.join(od, os.path.basename(rel)), S, fmt="%.17g")
print(tag, len(done), "spectra ->", od)
