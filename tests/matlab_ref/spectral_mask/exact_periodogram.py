# -*- coding: utf-8 -*-
"""High-precision reference for the analyzer spectrum model (rounding + window budget of the spectral-mask selftest).

For each of the 10 distinct displayed spectra captured from the R2025a spectrumAnalyzer (tests/matlab_ref/scope/spectral_mask/
captures.json: stored_spectra), the model "Hann periodic window, NFFT = max(1024, WL), 'power' = |FFT(w.x)|^2 / sum(w)^2 (x2 on
interior one-sided bins), running average lambda = (N-1)/(N+1) (double), dBm = 10 log10 + 30" is evaluated with mpmath at 40 digits
(mixed-radix DFT, exact window sum, exact averaging) and rounded to double once at the end -- TWICE, with two sets of window doubles:
  dsvwin   dsv_spectrum.design_window('hann', L) = 0.5 - 0.5 cos(2 pi n / L) evaluated in double by numpy (what DSV multiplies by)
  mwin     MATLAB R2025a hann(L, 'periodic') doubles (hann_periodic_{L}.txt written by hann_periodic_ref.m; what the scope and
           w4000_fft_ref.m multiply by). The two differ at the ulp level (round 6 review), which shifts the exact model value of
           every bin by up to window_effect.max_abs_diff_dB -- so part of the scope-vs-model residual is the window, not the FFT.
Every available double-precision implementation of the same model is then compared bin by bin (|impl - exact| in double) with the
exact values of ITS OWN window:
  scope         the analyzer's own displayed spectrum (stored capture files)       -- mwin;   platform independent, pinned
  matlab_fft    MATLAB fft(w.*x) periodogram (w4000_fft_call{k}.txt, WL 4000 only)  -- mwin;   platform independent, pinned
  dsv_numpy_*   dsv_mask.scope_spectra() dumped by dump_dsv_spectra.py under one numpy version each (sampled FFT implementations)
                                                                                     -- dsvwin; platform dependent, sampled
Per WindowLength the JSON then gives the rounding + window bound used by the selftest:
  bound = delta_scope (max |scope - exact_mwin|) + delta_window (max |exact_mwin - exact_dsvwin|) + delta_dsv (max over the sampled
          numpy versions of |DSV - exact_dsvwin|)          -- by the triangle inequality every sampled |DSV - scope| <= bound
  tol   = 2 * bound rounded up to two significant digits    -- the selftest TOL (2x margin for other numpy / FFT implementations)
This is a mathematical ground truth computed by mpmath, NOT a MATLAB measurement; the MATLAB numbers are the stored files.
Usage (relative paths; run from anywhere with a python that has numpy and mpmath):
    python exact_periodogram.py <ref_dir> <ui_dir> <out_json> [<dsv_dump_dir> ...]
e.g. from tests/matlab_ref/spectral_mask:  python exact_periodogram.py .. ../../.. fft_rounding_ref.json <dumps>/dsv_numpy_2.4.6 ..."""
import hashlib
import json
import math
import os
import platform
import sys
import time

import numpy as np
import mpmath as mp

mp.mp.dps = 40
ref_dir, ui_dir, out_json = sys.argv[1], sys.argv[2], sys.argv[3]
dump_dirs = sys.argv[4:]
sys.path.insert(0, ui_dir)
import dsv_spectrum as SP   # noqa: E402  (only for the double Hann window DSV multiplies by)

_TW = {}


def tw(n, e):
    e %= n
    key = (n, e)
    if key not in _TW:
        _TW[key] = mp.expjpi(mp.mpf(-2 * e) / n)
    return _TW[key]


def fft_mp(a):
    """Mixed-radix decimation-in-time DFT of a list of mpc (any length)."""
    n = len(a)
    if n == 1:
        return a[:]
    p = 2
    while n % p:
        p += 1
    m = n // p
    subs = [fft_mp(a[r::p]) for r in range(p)]
    out = [None] * n
    for k in range(m):
        t = [subs[r][k] * tw(n, r * k) for r in range(p)]
        for q in range(p):
            s = mp.mpc(0)
            for r in range(p):
                s += t[r] * tw(p, r * q)
            out[k + m * q] = s
    return out


def to_double(v):
    return float(mp.nstr(v, 30))          # correctly rounded (Python's float parsing), not mpmath's round-down to_float


def ceil_2sig(v):
    """Round up to two significant digits (built from a decimal string so it is bit-identical to the constant written in dsv_mask.py)."""
    e = math.floor(math.log10(v))
    scale = float(f"1e{e - 1}")
    return float(f"{math.ceil(v / scale)}e{e - 1}")


def periodogram_exact(x, w, nfft, onesided):
    """|FFT(w.x, nfft)|^2 / sum(w)^2 in mp, arranged like dsv_spectrum.arrange (onesided: x2 interior; centered: Nyquist at the positive end)."""
    sw = mp.fsum(mp.mpf(float(v)) for v in w)
    a = [mp.mpc(mp.mpf(float(np.real(xi))) * mp.mpf(float(wi)), mp.mpf(float(np.imag(xi))) * mp.mpf(float(wi))) for xi, wi in zip(x, w)]
    a += [mp.mpc(0)] * (nfft - len(a))
    X = fft_mp(a)
    P = [(z.real ** 2 + z.imag ** 2) / sw ** 2 for z in X]
    if onesided:
        h = nfft // 2 + 1
        out = P[:h]
        hi = h - 1 if nfft % 2 == 0 else h
        return [v * 2 if 1 <= i < hi else v for i, v in enumerate(out)]
    sh = nfft // 2 - 1 if nfft % 2 == 0 else (nfft - 1) // 2
    return [P[(j - sh) % nfft] for j in range(nfft)]


def ulp_diff(a, b):
    """|a - b| in units of the spacing of the larger magnitude (0 where equal)."""
    sp = np.spacing(np.maximum(np.abs(a), np.abs(b)).clip(min=np.finfo(float).tiny))
    return np.abs(a - b) / sp


d = os.path.join(ref_dir, "scope", "spectral_mask")
sm = os.path.join(ref_dir, "spectral_mask")
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
with open(os.path.join(sm, "w4000_fft_ref.json"), encoding="utf-8") as fh:
    W4 = json.load(fh)
fft_files = {c["scope_spectrum_file"]: c["fft_file"] for c in W4["calls"]}
with open(os.path.join(sm, "hann_periodic_ref.json"), encoding="utf-8") as fh:
    HR = json.load(fh)
hann_rows = {int(r["L"]): r for r in HR["windows"]}

# distinct (dataset, L, N, two_sided) groups -> their stored spectra per call
groups = {}
for cap in C["captures"]:
    key = (cap["dataset"], int(cap["window_length"]), int(cap["spectral_averages"]), bool(cap["two_sided"]))
    files = tuple(c["spectrum_identical_to"] for c in cap["calls"])
    groups.setdefault(key, set()).add(files)
assert all(len(v) == 1 for v in groups.values()), groups

# the two window double sets and how far apart they are
windows = {}
win_diff = {}
for L in sorted({k[1] for k in groups}):
    w_d = SP.design_window("hann", L)
    assert np.array_equal(w_d, 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(L) / L)), "design_window is not the plain formula"
    w_m = np.loadtxt(os.path.join(sm, hann_rows[L]["file"]))
    assert w_m.shape == w_d.shape == (L,)
    windows[L] = {"dsvwin": w_d, "mwin": w_m}
    u = ulp_diff(w_m, w_d)
    nz = w_m != 0
    win_diff[str(L)] = {
        "n_values": L, "n_differ": int((w_m != w_d).sum()), "max_abs_diff": float(np.max(np.abs(w_m - w_d))),
        "max_ulp_diff": float(u.max()), "max_rel_diff": float(np.max(np.abs(w_m[nz] - w_d[nz]) / np.abs(w_m[nz]))),
        "argmax_abs_diff_n": int(np.argmax(np.abs(w_m - w_d))),
        "fsum_dsvwin": math.fsum(w_d.tolist()), "fsum_mwin": math.fsum(w_m.tolist()), "matlab_sum_reported": hann_rows[L]["sum"],
        "symmetric_2_to_end_dsvwin": bool(np.array_equal(w_d[1:], w_d[1:][::-1])),
        "symmetric_2_to_end_mwin": bool(np.array_equal(w_m[1:], w_m[1:][::-1])),
        "sha256_dsvwin_17g": hashlib.sha256("\n".join(f"{v:.17g}" for v in w_d).encode()).hexdigest(),
        "sha256_mwin_file": hashlib.sha256(open(os.path.join(sm, hann_rows[L]["file"]), "rb").read()).hexdigest()}
    print(f"window L={L}: {win_diff[str(L)]['n_differ']}/{L} values differ, max |diff| {win_diff[str(L)]['max_abs_diff']:.3g} "
          f"({win_diff[str(L)]['max_ulp_diff']:.0f} ulp at n={win_diff[str(L)]['argmax_abs_diff_n']}, rel {win_diff[str(L)]['max_rel_diff']:.2g}); "
          f"fsum dsv {win_diff[str(L)]['fsum_dsvwin']!r} vs matlab {win_diff[str(L)]['fsum_mwin']!r} (MATLAB sum() {hann_rows[L]['sum']!r})")

REF_WIN = {"scope": "mwin", "matlab_fft": "mwin"}      # dsv_numpy_* -> dsvwin
spectra_out = []
delta = {}       # L -> {"scope": max|scope-exact_mwin|, "matlab_fft": ..., "window": max|exact_mwin-exact_dsvwin|, "dsv_by_impl": {name: max|dsv-exact_dsvwin|}}
pair = {}        # (impl, L) -> max |impl - scope|
t0 = time.time()
for (ds, L, N, two), files in sorted(groups.items()):
    files = next(iter(files))
    nfft = max(1024, L)
    lam = (N - 1.0) / (N + 1.0)                   # the implementations' double lambda (0.6 for N = 4; exact 3/5 would differ by ~1e-17 relative)
    cplx = bool(C["signals"][ds]["complex"])
    onesided = not (two or cplx)
    num = {"dsvwin": None, "mwin": None}
    den = mp.mpf(0)
    dl = delta.setdefault(L, {"scope": 0.0, "matlab_fft": None, "window": 0.0, "dsv_by_impl": {}})
    for k, rel in enumerate(files, 1):
        x = sig[ds][k - 1]
        nch = x.shape[1]
        nseg = x.shape[0] // L
        for i in range(nseg):
            for wn, w in windows[L].items():
                P = [periodogram_exact(x[i * L:(i + 1) * L, ch], w, nfft, onesided) for ch in range(nch)]
                if num[wn] is None or lam == 0.0:
                    num[wn] = P
                else:
                    num[wn] = [[mp.mpf(lam) * a + b for a, b in zip(num[wn][ch], P[ch])] for ch in range(nch)]
            den = mp.mpf(1) if (den == 0 or lam == 0.0) else mp.mpf(lam) * den + 1

        def exact(wn, ch, b):
            return 10 * mp.log10(num[wn][ch][b] / den) + 30

        E = {wn: np.array([[to_double(exact(wn, ch, b)) for b in range(nfft // 2 + 1 if onesided else nfft)] for ch in range(nch)]).T
             for wn in num}                                                                  # (nbins, nch) each
        nbins = E["mwin"].shape[0]
        # window effect: exact difference in mp, then max; also as a double value for the JSON
        WD = np.array([[to_double(exact("mwin", ch, b) - exact("dsvwin", ch, b)) for b in range(nbins)] for ch in range(nch)]).T
        iw = int(np.argmax(np.abs(WD)))
        wb, wch = divmod(iw, nch)
        base = os.path.basename(rel)
        impls = {"scope": np.loadtxt(os.path.join(d, rel))}
        if base in fft_files:
            impls["matlab_fft"] = np.loadtxt(os.path.join(sm, fft_files[base]))
        for dd in dump_dirs:
            p = os.path.join(dd, base)
            if os.path.isfile(p):
                impls[os.path.basename(os.path.normpath(dd))] = np.loadtxt(p)
        impls = {n: (S[:, None] if S.ndim == 1 else S) for n, S in impls.items()}
        peak = int(np.argmax(E["mwin"].max(axis=1)))
        pk_ch = int(np.argmax(E["mwin"][peak]))
        rows = {}
        pinned = {(peak, pk_ch), (wb, wch)}
        for name, S in impls.items():
            assert S.shape == E["mwin"].shape, (name, S.shape, E["mwin"].shape)
            wn = REF_WIN.get(name, "dsvwin")
            D = np.abs(S - E[wn])
            i = int(np.argmax(D))
            b, ch = divmod(i, nch)
            pinned.add((b, ch))
            rows[name] = {"reference_window": wn, "max_abs_diff_dB": float(D[b, ch]), "bin": b, "ch": ch + 1, "impl_dBm": float(S[b, ch]),
                          "exact_dBm_at_bin": mp.nstr(exact(wn, ch, b), 30), "level_rel_peak_dB": float(E[wn][b, ch] - E["mwin"][peak, pk_ch]),
                          "bit_identical_bins": int((S == E[wn]).sum()), "numel": int(S.size)}
            other = "dsvwin" if wn == "mwin" else "mwin"
            rows[name][f"max_abs_diff_vs_{other}_dB"] = float(np.max(np.abs(S - E[other])))      # informational: against the other window's exact
            if name in REF_WIN:
                dl[name] = max(dl[name] or 0.0, float(D[b, ch]))
            else:
                dl["dsv_by_impl"][name] = max(dl["dsv_by_impl"].get(name, 0.0), float(D[b, ch]))
                pair[(name, L)] = max(pair.get((name, L), 0.0), float(np.max(np.abs(S - impls["scope"]))))
        dl["window"] = max(dl["window"], float(abs(WD[wb, wch])))
        spectra_out.append({"file": rel, "dataset": ds, "window_length": L, "nfft": nfft, "averages": N, "two_sided": two,
                            "complex_input": cplx, "k": k, "segments_so_far": sum(sig[ds][j].shape[0] // L for j in range(k)),
                            "nbins": nbins, "nch": nch, "peak_bin": peak, "peak_ch": pk_ch + 1,
                            "peak_dBm_exact_mwin": mp.nstr(exact("mwin", pk_ch, peak), 30),
                            "peak_dBm_exact_dsvwin": mp.nstr(exact("dsvwin", pk_ch, peak), 30),
                            "window_effect": {"max_abs_diff_dB": float(abs(WD[wb, wch])), "signed_diff_dB_mwin_minus_dsvwin": float(WD[wb, wch]),
                                              "bin": wb, "ch": wch + 1, "level_rel_peak_dB": float(E["mwin"][wb, wch] - E["mwin"][peak, pk_ch]),
                                              "n_bins_where_double_values_differ": int((E["mwin"] != E["dsvwin"]).sum()), "numel": int(E["mwin"].size)},
                            "pinned_bins": [{"bin": b, "ch": ch + 1, "exact_dBm_mwin": mp.nstr(exact("mwin", ch, b), 30),
                                             "exact_dBm_dsvwin": mp.nstr(exact("dsvwin", ch, b), 30)} for b, ch in sorted(pinned)],
                            "impl": rows})
        print(f"{base}: window effect {abs(WD[wb, wch]):.3e} @bin {wb} ch{wch + 1}; " +
              "; ".join(f"{n} {r['max_abs_diff_dB']:.3e} @bin {r['bin']} ch{r['ch']} ({r['level_rel_peak_dB']:.1f} dB rel peak, "
                        f"{r['bit_identical_bins']}/{r['numel']} identical, vs {r['reference_window']})" for n, r in rows.items()),
              f"[{time.time() - t0:.0f}s]")
summary = {}
for L, dl in sorted(delta.items()):
    d_dsv = max(dl["dsv_by_impl"].values())
    bound = dl["scope"] + dl["window"] + d_dsv
    vs_scope = {n: v for (n, l_), v in pair.items() if l_ == L}
    assert max(vs_scope.values()) <= bound, (L, vs_scope, bound)       # triangle inequality must hold for every sampled implementation
    summary[str(L)] = {"delta_scope_dB": dl["scope"], "delta_matlab_fft_dB": dl["matlab_fft"], "delta_window_dB": dl["window"],
                       "delta_dsv_dB": d_dsv, "delta_dsv_by_impl_dB": dl["dsv_by_impl"], "bound_dB": bound, "tol_dB": ceil_2sig(2 * bound),
                       "max_abs_diff_vs_scope_dB": vs_scope,
                       "margin_tol_over_max_sampled_residual": ceil_2sig(2 * bound) / max(vs_scope.values())}
    print(f"WL {L}: delta scope {dl['scope']:.3e} + window {dl['window']:.3e} + dsv {d_dsv:.3e} = bound {bound:.4e} -> TOL {ceil_2sig(2 * bound)!r}; "
          f"sampled |DSV - scope| {vs_scope} (margin {summary[str(L)]['margin_tol_over_max_sampled_residual']:.2f}x)")
out = {"note": __doc__, "precision_digits": mp.mp.dps,
       "windows": {"dsvwin": "dsv_spectrum.design_window('hann', L) = 0.5 - 0.5*cos(2*pi*n/L), n = 0..L-1, numpy double (sampled platform below)",
                   "mwin": f"MATLAB {HR['matlab_version']} hann(L, 'periodic') doubles: hann_periodic_<L>.txt (hann_periodic_ref.m)",
                   "diff": win_diff},
       "reference_window_per_implementation": {**REF_WIN, "dsv_numpy_*": "dsvwin"},
       "matlab_version_of_captures": C["matlab_version"], "w4000_fft_matlab_version": W4["matlab_version"], "hann_matlab_version": HR["matlab_version"],
       "implementations": sorted({n for s in spectra_out for n in s["impl"]}),
       "sampled_dsv_platform": f"{platform.system()} {platform.machine()} (the dsv_numpy_* rows and the dsvwin doubles; scope and matlab_fft rows are file-derived)",
       "summary": summary, "spectra": spectra_out}
with open(out_json, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("wrote", out_json, f"in {time.time() - t0:.0f}s")
