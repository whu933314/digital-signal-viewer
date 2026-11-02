# -*- coding: utf-8 -*-
"""English catalog for plotkit.i18n — merged from the part modules (keys are the Traditional Chinese source strings).

Parts: i18n_en_core (preferences / startup), i18n_en_plotkit (plotkit widgets, theme, interact, dialogs, clipboard, model),
i18n_en_dsv1 / i18n_en_dsv2 / i18n_en_dsv3 (signal_viewer.py, in source order), i18n_en_tools (the 2026-10 tool-gap batches). A key in a later part overrides an earlier one.
"""
import importlib

CATALOG = {}
for _part in ("core", "plotkit", "dsv1", "dsv2", "dsv3", "tools", "tools_d", "tools_e", "keys", "folder", "iq", "batch1", "batch2", "batch3", "batch4", "fix1", "fix2", "fix3", "i13", "axnames", "0913x", "0914p", "0915s"):
    try:
        _m = importlib.import_module(f"plotkit.i18n_en_{_part}")
        CATALOG.update(getattr(_m, "CATALOG", {}))
    except ImportError:
        pass
