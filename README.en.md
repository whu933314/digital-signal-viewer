# Digital Signal Viewer v1.0.1 User Guide

Single-file desktop program `signal_viewer.py`: view the waveforms of several digital / ADC signals on one shared time axis,
and run difference comparison, despike (spike suppression), spectrum and GFSK analysis. It only needs Python 3.10+, numpy, matplotlib ≥ 3.7 (the UI uses tkinter),
plus, in the same folder, the `plotkit/` package (the interactive plotting features; it can also be used on its own in other Python programs, see `docs/plotkit.md`)
and DSV's own modules: `dsv_*.py` (bus display, keyboard shortcuts, measurements, panner, spectrum, preprocessing with its filter / clean / convert helpers,
channel measurements, ACPR, distortion, spectral mask), `matfile.py` (.mat reader) and `wavfile.py` (WAV / .npy / .npz). Without any one of them the program does
not start, and the start-up error names the missing one (the exe / .app bundles bring them all along).

```
python signal_viewer.py                # open the GUI; the last session is restored automatically (~/.signal_viewer_last.json)
python signal_viewer.py D:\captures    # restores the last session too, then adds the arguments: a folder becomes the root folder, a data file opens a new panel (0.9.13, the drag-and-drop rule)
python signal_viewer.py --selftest     # no GUI: run the core-logic checks; prints SELFTEST OK and exits 0 when all pass
```

## Supported Formats

### Text files (.txt / .dat / .log)
- One value per line. Blank lines and comment lines starting with `#`, `%`, `//` are skipped; only the first token of each line is used (split on whitespace, comma or semicolon).
- Read formats: `AUTO` (auto-detect), `DEC` (decimal; `0x` and `0b` prefixes are also accepted), `HEX` (unsigned),
  `HEXS` (signed two's complement, bit width = number of characters × 4, e.g. `FFFFF800` → -2048).
- AUTO rule: take the first 400 tokens; the file is judged HEX only when all of them are pure hex characters of the same width AND contain A–F or have width ≥ 4; otherwise DEC
  (so values like `292`, `0`, `1` are not mistaken for hex).
- Values that cannot be parsed are filled with the previous valid value (hold fill).

### CSV
- The delimiter is auto-detected (`,` `;` Tab), encoding `utf-8-sig`. If the first row is not all numbers it is treated as the header.
- Time column: a column whose name contains `time`, or is called `t` / `timestamp`; without a header, the first column is also treated as the time column when it is "number + time unit" (e.g. `125 ns`).
  The time column is never treated as a signal, but it can be used to estimate the sample rate and as the offset start.
- Every other column can become a signal of its own; the signal key is `file;;column`, and a text file's key is `subfolder/filename`.
- Numbers may be written as `1,5` (= 1.5), `1,000` (= 1000), full-width digits, `0x10`.

### Import CSV dialog (.mat uses the same one)
MATLAB .mat files (`save` -v6 / -v7, no scipy needed) are handled like CSV: the folder tree lists every variable as a column, "Import CSV / MAT…" accepts .mat directly,
complex variables become `real(x)` / `imag(x)`, N×M matrices become `x(:,1)`…, structs expand to `s.field`, cells to `c{1}`; an increasing vector named `t` / `time` is the time column (seconds) used to estimate the sample rate.
-v7.3 (HDF5) is not supported yet; the app tells you to re-save with `save(...,'-v7')`. Example: `samples/mat/demo_v7.mat`.
- **WAV** (PCM 8/16/24/32-bit, IEEE float 32/64; one column per channel ch1, ch2…, the sample rate is taken from the header) and **NumPy .npy/.npz**
  (1-D = one column, 2-D = one column per column, complex split into real()/imag()): they appear in the folder tree and the import dialog like CSV, and can be dropped in.
- **Drag and drop**: drag files (CSV/MAT/WAV/NPY/TXT/DAT/LOG) from Finder/Explorer into the main window to add and plot them directly, with no root folder and no dialog.
  **Drop on a panel in the plot = add to that panel** (while dragging, that panel gets a frame and the status bar says "Release to add to P2");
  **drop on the blank area below the last panel** (under its x tick labels) = **new panel** (that area gets a dashed frame, status bar "Release to create P3");
  drop anywhere else (the list, the folder panel, the toolstrip…) or when there are no panels yet = new panels (one per text file; the columns of one CSV stay together).
  **Files / columns in the Folder panel can be dragged onto the plot too** (same target rules: a panel = add to it, the blank area below the last panel = new panel;
  outside the plot = cancel), and so can lines from the AM/PM/FM analysis window (see below). Before 2026-10-24 the target was always the nearest panel, so
  every drop landed in the same panel and a new panel could not be created by dragging.
  The new signals are selected and the plot scrolls to their panel. A file already in that panel is skipped (the status bar says so and selects it; the same file dropped through a symbolic link or a path differing only in case counts as the same file, 0.9.14 — it used to be added again); another panel may get its own copy;
  files with the same name from different folders are not mistaken for one another. ⌘Z / Ctrl+Z undoes.
  Dropping a folder makes it the root folder and scans it. On macOS you can also drop files on the Dock icon (new panels). Without tkinterdnd2 only the Dock-icon route remains.
  **Files or folders given on the command line (`python signal_viewer.py <files or folders…>`) and files dropped onto the Windows exe follow the same rule** (0.9.13;
  the last session is restored first, see "Settings and Auto-restore"): the status bar says "Start-up arguments: added 2 signal(s) to P3", ⌘Z undoes.
- **Right-click to recolor**: right-click a signal on the plot or in the list → Color → click a swatch (the current style's color order), Auto, or Custom… for the color chooser; Ctrl+Z undoes.

1. **1. Select Columns**: each row shows Add / Column name / Apply shift & scale / Despike / Min / Max / Median / Suggested shift.
   Columns with more than 2 distinct values are treated as analog columns and have shift & scale and despike checked by default. Click a cell to toggle it.
2. **Values and sample rate**: displayed value = (raw value + shift) × scale. "Use Suggested" fills in the suggested shift
   (when the value range lies within [0, 2^b) and the median is close to 2^(b-1), −2^(b-1) is suggested, e.g. −512 for a 10-bit ADC).
   Sample rate accepts `64M`, `1.5G`, `500k` and is converted live to SPS = fs / symbol rate; "Use Estimate" estimates it from the first and last values of the time column.
3. **Despike parameters**: longest spike run 1/2/3, threshold × noise, minimum deviation.
4. **Other options**: plot the checked columns merged in one panel; use the start time of the Time column as the offset.

When the same key is already in the list, adding it again only updates its parameters and does not create a duplicate. The last settings are remembered.

## Main Window (v3.4: layout and colors follow the MATLAB R2025a desktop)

The layout and colors were measured against MATLAB R2025a on this Mac (`docs/matlab-ui-spec.md` gives the source of every value).
The default is the **dark theme** (the user's MATLAB desktop theme); "View → Appearance → Theme" switches to light, and since 1.0.0 also to the six
Sony (black / deep blue) and Apple (light / dark / dark, graphite / dark, black) looks (see "Preferences" below); Windows and macOS look the same.
When a settings file from an older version (v3.3 or older, settings-file version ≤ 5) is loaded, the theme is set to dark and the plot style to the theme's MATLAB style (settings-file version raised to 6).

- **Toolstrip**: the tab row at the top (blue in the MATLAB themes; the other looks use their own colours), **Home / Signals / Preprocess / Style / Analyze / Measurements / View / Export**; each tab is divided into sections,
  the main actions are large buttons with the icon on top, secondary actions are small buttons in three rows; each section has a small caption underneath. The quick-access area at the top right has Export Settings, Undo, Redo, Help.
  Double-click a tab to collapse the toolstrip to just the tab row (as in MATLAB).
  - Home: File (Import…, Export…) | Folder (Browse, Rescan, Add Selected, Add All Shown) | Session (Export Settings, Import Settings, Auto-restore Last Session) | Environment (Preferences, Collapse Folders on Open) | Help (Help, Diagnostics).
  - Signals: Edit (Remove, Clear, Select All, Undo, Redo) | Order (Move Up, Move Down, Sort by Name) | Panel (Merge into One Panel, Split into Panels) | **Parameters** (SPS, fs → SPS, Offset, shift/scale, read format, plot type — the same settings as the Signal Properties panel).
  - Preprocess: Filter (Lowpass, Highpass, Bandpass, Bandstop) | Clean (Smooth, Detrend) | Convert (Resample, Envelope), after MATLAB Signal Analyzer's PREPROCESS tab; see "Preprocess" below.
  - Style: Lines (Color, Line Width, Marker Size, Reset Style, Plot Type ▾) | Digital Display (format, radix, bit width).
  - Signal (continued): Despike (On, Off, Mark Fixed Points, Parameters…) | Compare (Highlight Diff Regions, Dashed, Tolerance…, Previous / Next Difference, Error Rate… — batch 4, see "Error Rate" below) | Transitions (Previous / Next) —
    these three sections moved here from Analyze on 2026-10-23: despiking repairs glitches in dump patterns, and comparison and transitions are about the signals themselves.
    k / minimum deviation / threshold and the tolerance live in the Signal Properties panel ("Parameters…" / "Tolerance…" open it).
  - Analyze: Analysis Windows (Spectrum, GFSK, Constellation, AM/PM/FM Analysis — since 2026-10-24 AM/PM and FM are one button and one window; Eye Diagram — batch 4, see "Eye Diagram" below).
  - Measurements: Measurements panel | Data Cursors (▾, Snap to data, Lock cursor spacing, Cursors into View, Horizontal Cursors) | Data Tips (toggle, Tip Content…, Export Tips…).
  - View: Show (Grid, Legend, Sample markers, Normalize Y) | Interaction (Crosshair, Wheel Zoom, Keep x Range) | Zoom (Show All, x from/to) | Axes (the **current panel's** x unit, Symbol rate, y unit and Link Time; panel height, Fit all in window, y stack offset) | Layout | Appearance.
  - Export: Figure Windows (Copy Signals, Copy to New Figure Window, New Figure Window, Paste into Figure Window) | Image File (Copy Figure to Clipboard, Copy as Vector, Save Figure As…).
  Default layout: the left column holds Folder and Plotted Signals, the plot fills the rest; the Signal Properties panel is hidden by default (its settings live on the toolstrip) and can be brought back from View → Layout —
  but only for the current session: **it is hidden again on every start** (whatever the saved layout says; since 2026-10-24 — before, a settings file saved after pressing "Parameters…" brought it back every time).
  The Measurements panel sits **below the plot** (center column) and likewise does not appear by default and is hidden on every start: it opens when you press
  Measurements → **Measurements** (or turn on any measurement group) and closes when you press it again
  (requested by the user on 2026-10-24; up to 0.9.6 it was in the right column — an older saved layout moves it below the plot and keeps the other panels and column widths).
- **Address bar**: root folder path, Up, Browse…, Rescan (Enter also rescans).
- **Panels** (drag the dividers to resize; the ⌄ at the right of a title bar collapses the panel to its title bar and gives the space to the other panels in the column; clicking a title bar selects the panel; every panel can be moved to another column, reordered, maximized or hidden). The default layout is **Folder and Plotted Signals in the left column, the plot filling the rest**:
  - **Folder** (= MATLAB's Current Folder, following R2025a's columns, menus and behavior):
    - Columns **Name | Size | Date Modified | Type**; the top level is the contents of the current folder, **folders always come before files**,
      click a column heading to sort (click again to reverse; the heading shows ▲ / ▼), right-click a heading to choose the visible columns; folders, CSV / .mat, WAV and
      text files have their own icons, and **files that cannot be plotted are listed too, in gray**. Subfolders expand in place with ▸; CSV / .mat / WAV / .npy files
      expand into their columns (pick a column to plot — a DSV extra).
    - **Double-click a folder to enter it** (it becomes the current folder and the address bar follows); double-click a file or column to open it (plot it; CSV opens
      the import dialog); double-click a file that cannot be plotted to open it in the system default app. Enter does the same as double-click, **F2 renames**.
    - The address bar has **Back / Forward / Up One Level**, and the path field's drop-down lists the **recent folders** (up to 20, saved in the settings file).
    - **Right-click**: Open, Open Outside DSV, Show in Finder (Windows: Show in Explorer), Open Current Folder in Finder, Copy Path, Rename…, Add Selected / Add All Shown,
      Show (columns), Sort By, Rescan. A file used by plotted signals cannot be renamed (remove those signals first); name checks follow MATLAB (blank, slash, duplicate,
      hidden names). **Deleting files is not offered**: Delete in the Folder panel does not delete files on disk (MATLAB can, but a waveform viewer should not risk
      losing data — use Finder / Explorer).
    - **Details** at the bottom (MATLAB's Details, collapsed by default; click the heading): type, size and date of the selected file; table files also list their data
      and time columns; folders show the item count.
    - **Auto-refresh**: files added, deleted or renamed in the folder show up within about 3 seconds (expanded folders, selection and scroll position are kept; the plot is
      not redrawn). Preferences → Folder can turn it off and can turn on "Show hidden files and folders".
    - The search box filters live (folders, file names, CSV column names); the double arrows ⌄⌄ / ›› in the title bar expand / collapse all folders; "Add All Shown"
      adds every listed file that can be plotted (CSV adds all columns; SPS is estimated from the time column when present); below are the defaults for new signals (SPS, read format).
  - **Plotted Signals** (= MATLAB's Workspace): the table Show / # / Signal / Panel / SPS / Offset / N / Fmt, alternating background per panel,
    the signal name is drawn in the line colour; the title bar has "Remove" and "Sort by Name".
  - **Plot**: the plot toolbar on top, ordered like MATLAB's axes toolbar (save, copy figure to clipboard, copy as vector (PDF), data tips, pan, zoom | restore view | previous / next view | crosshair, with the cursor position at the right);
    **Pan is the default mode on start** (user's choice, 2026-10-24; turn Data Tips on yourself — that is remembered in the settings file as `view.tips`),
    the scrollable plot below (each sub-plot has a fixed height; many panels scroll).
  - Hidden by default (View → Layout opens them): **Signal Properties** (three tabs — Signal Parameters / Despike / View & Diff — the same settings also live on the toolstrip),
    **Measurements** (below the plot; Measurements → Measurements or any measurement group opens it too; hidden on every start), see "Measurements, transitions, Normalize Y" below; **Cursor Measurements** (shown automatically when data cursors are on), see "Data cursors and data tips" below.
- **Status bar**: N signals / M panels / total samples, number of despike-corrected points, difference segment count and ratio for each panel.
- The plot style follows the theme by default: the dark theme uses the colors of MATLAB `figure(Theme="dark")` (figure #212121, axes #121212, 7-color order),
  the light theme uses MATLAB's factory defaults; "Style → matplotlib" switches back to matplotlib's own look. The Spectrum and GFSK windows use the same style.

### Plotted Signals table
- Double-click a Signal / Panel / SPS / Offset cell to edit it in place; Enter edits SPS, Delete removes; click the ☑ in the first column to toggle show / hide.
- Right-click menu: edit each column, read format, style (color, line width, line style, marker, plot type, Y axis), despike on/off, merge, split, Spectrum, GFSK, Constellation, AM/PM/FM Analysis, Eye Diagram, Error Rate, Export to TXT, Remove.
  At the bottom there is also "Reload Signals with Missing Files" (0.9.13; enabled while the list holds placeholders — files missing, or present but unreadable — see "Opening while a source file is temporarily missing" under "Settings and Auto-restore").
  Right-clicking empty space with nothing selected grays out the items that need a selection (edit fields, styles, show/hide, copy, remove).
- **With a selection, actions apply only to the selected rows; with no selection they apply to all.**

### Signal Properties → Signal Parameters
- SPS (samples per symbol): entry, quick menu 1/2/4/8/16/32/64, ×2, ÷2.
- Sample rate: enter fs and it is converted to SPS = fs / symbol rate.
- Offset: entry, unit symbol or sample, ±1 / ±10 / ±100 nudges, slider (applied about 150 ms after release).
- Value shift / scale; read format (changing it re-reads the file).
- Plot type: Line / Stairs / Stem, applied to the selected signals on selection (see "Plot Type, AM/PM/FM Analysis" below).

### Signal Properties → Digital Display (Logic Analyzer bus)
After MATLAB Logic Analyzer DisplayChannelFormat / DisplayChannelRadix. At the bottom of the Signal Parameters tab, or Display Format / Radix /
Bit Width… in the list or plot right-click menu; applies to the selected signals, can be undone (Ctrl+Z) and is saved in the settings (old settings = all Analog).
- **Format**: Analog (default) / Digital, chosen manually only — the program never decides on its own. Digital draws each run of constant
  value as a hexagon-ended box (a bus) with the value written inside; 0/1-only signals stay a logic-level line, as in MATLAB.
- When a panel (one y side) holds only buses they get one row each, top to bottom, with no y ticks; mixed with analog lines, a bus box spans that
  signal's own min..max. Put buses in their own panel (right-click → Split into Panels).
- Values that do not fit in a box are hidden (zoom in to see them); zooming re-lays out immediately, panning about 0.1 s after you stop. Only the
  visible transitions are processed, one crossing per pixel when denser than the pixels, so 1e6 samples stay smooth; at most 300 values per bus.
- **Radix**: Auto / Hexadecimal / Binary / Octal / Signed decimal / Unsigned decimal. Once chosen it is used by the bus values, the crosshair,
  data tips (including the Y row of Tip Content…), Max / Min / Peak to Peak in the Measurements panel and y1 / y2 in Cursor Measurements
  (readouts get 0x / 0b / 0o); Δy, Mean and the other measurements and exported data tips stay decimal. Auto keeps readouts decimal; bus values are
  hexadecimal for files read as HEX / HEXS, decimal otherwise. Fractional values are always decimal.
- **Bit Width**: empty or 0 = auto (HEX token digits × 4 or the value range, whichever is larger); sets the zero padding and the two's complement
  for Signed decimal (8-bit FF = −1). Values wider than the bit width keep the low bits (like a fixed-width wave).
- Clicking, hover and data tips still work: clicking anywhere inside a box hits that signal; the tip snaps to the nearest sample, sits on the box's
  center line and shows the true sample value.
- **Copy to a figure window** (Ctrl+C / Copy to New Figure Window): a digital bus is drawn as hexagon boxes with values in the figure window too
  (radix and bit width as in the main plot; when the window holds only buses they get one row each with no y ticks); clicking inside a box selects it, tips sit on
  the box's center line and use the radix; saving the figure JSON keeps it (`series[].disp / radix / bits`).
- In the **Spectrum window** a bus signal is still analysed as a spectrum of its sample values (no boxes): the bus is only a way of displaying the values.

### Signal Properties → Despike
Fixes the single-point or brief jumps to 0 / full scale that are common in FPGA captures:
for every candidate interval of length 1..k, a straight line is drawn through the one point before and the one point after the interval; it counts as a spike only when every point inside the interval deviates from that line by more than the threshold;
threshold = max(minimum deviation, factor × 1.4826 × median). For length ≥ 2 a curvature compensation is subtracted so that smooth peaks are not flattened.
Corrected points are replaced by the linear interpolation and marked × on the plot, and the ylabel shows `[N spike fixed]`. On / off is on the toolstrip's "Analyze" tab.

### Each panel has its own axes: Link Time, x / y units (user-reported item 8, 2026-10-25)
- Every panel has its own x range, **x unit**, **Symbol rate** and **y unit** (the y label reads `P1 [V]`). As in MATLAB Signal Analyzer, every display has
  **Link Time** (on by default in MATLAB and switchable per display; R2025a toolstrip tooltip: "Link time span with other linked displays").
  - On (default): the panel **zooms and pans together** with the other linked panels **over the same time span**; with every panel linked and the same units
    zooming and panning are exactly as before (since item 11 every panel has its own x tick labels and x label, see the next section). Panels with different
    symbol rates can be linked too: their x is converted to the same time span (e.g. P2 at 2M and P1 at 1M: P2's symbol range is twice P1's).
  - Off: this panel **zooms and pans on its own** (wheel, drag, zoom mode, arrow keys and Home only move it).
- Where to set it: **View → Axes** on the toolstrip (it reads "Current P1": it edits the current panel), **Signal Properties → View / Diff**, and a
  **panel's right-click → Axes (P1)** (Link Time, x-axis unit, Symbol rate…, y-axis unit…, "Apply X Unit and Symbol Rate to All Panels"); **Ctrl+U / ⌘U** toggles
  the current panel's Link Time (Ctrl+U in MATLAB too). The x unit and Symbol rate under Preferences → Plot are global: changing them applies to every panel.
  A new panel takes the current panel's x unit and symbol rate and is linked.
- **Current panel** (MATLAB's "selected display"): click a panel on the plot (any mode, left or right mouse button) to make it current; with two or more panels it gets a
  thin frame (on screen only, never in exported figures); before any click it is the top panel. The toolstrip Axes fields, the panner and x from/to act on it;
  AM/PM/FM, Constellation and GFSK analyze its I/Q, Eye Diagram plots its signals, and Error Rate compares its signals by default (see below);
  the Plotted Signals list selects its signals (see the next section).
- Per panel as well: the x of data tips and the crosshair uses that panel's unit (the crosshair is drawn only on panels linked to the one under the mouse);
  "Current x view" in the Measurements panel is each signal's own panel view; previous / next transition and difference move that panel (linked ones follow);
  Extract Signals uses each panel's range and the new panel takes its source panel's axes settings; fs → SPS and the FM fs use the symbol rate of the signal's panel.
- Settings file: `panels` (`{"1": {"link", "xunit", "symbol_rate", "yunit", "xlim"}, …}`); an older file without it gives every panel `view.xunit` /
  `view.symbol_rate`, all linked (as before). Deleting a panel and pressing Ctrl+Z brings its axes settings back too.

### Panel names and titles, and a figure title (new feature, 2026-10-26)
The user asked: "I want to name the x and y axes of every panel myself and give them titles, like MATLAB". Built as decided from the menus on 2026-10-26
(`audit/2026-10-26-branch-pause/decisions/decisions_u26.md`, item 3).
- **Where**: right-click an empty spot of a panel, its x-axis area (x tick labels or x-axis label) or its handle on the left → "Axes (P1)" →
  **Title… / Subtitle… / X-Axis Name… / Y-Axis Name… / Right Axis Name…**. The **figure title** belongs to no panel: it is in the same right-click menu,
  outside "Axes (P1)": **Figure Title…**. The dialog works like "y-axis unit…": it shows the current value (the full text), **blank = remove**
  (back to the usual label), Cancel = no change. In **pan and zoom modes** a right-click on the axes or the x-axis area opens MATLAB's mode menu
  (U5, U7b; on lines too in zoom mode) with MATLAB's items kept on top, and **below a separator it now also has "Axes (P1)" and "Figure Title…"**
  (the user's second menu decision of 2026-10-27, chosen knowing this differs a little from U5 "only MATLAB's menu"); the handle's right-click has them in
  all four modes.
- **Name + automatic unit, the P number stays**: y axis "≡ P1 Voltage [V]" (the unit follows the y unit; [norm] with Normalize Y; the spike note as before);
  x axis "Time [us]" (the name replaces "x", the unit follows the x unit). A blank name gives "≡ P1 [V]" and "x [us]" as before. This differs from MATLAB
  (there the typed text replaces the whole label and you type the unit yourself); the user chose it. Right axis: blank = "Right Axis" as before; when the panel
  has no right axis yet the name is kept and shows once a signal is on the right axis (the status line says so).
- **Text is shown as typed**: rx_data stays rx_data and a^b stays a^b (MATLAB's default tex interpreter would make sub/superscripts; the user chose this too).
  Only text inside $…$ is math, as with the y unit, e.g. `$V_{in}$`. An odd `$` or invalid math (`$x^$`, `$\foo$`, `$$`) is shown as typed with a hint
  on the status line, and drawing never fails. The same holds for the y unit, hint included (in 0.9.9 an invalid math y unit stopped the whole plot from
  drawing — see the note under "Saved" below).
  Chinese text next to math uses a font that has Chinese glyphs (matplotlib draws math strings with a single font; Arial would show boxes).
- **Title and subtitle** sit above each panel, the title on top and the subtitle below it (MATLAB's subtitle, R2020b and later); the **figure title** sits above
  all panels, centered over the axes (MATLAB sgtitle).
- **Font sizes** follow MATLAB's ratios (DSV's matlab styles): axis names = axes font × 1.1; title × 1.1 bold; subtitle × 1.1 normal; figure title × 1.1 normal
  (R2025a documents sgtitle's FontWeight default as normal; no public definition of its size was found, so it uses the title size). Theme and plot font
  size changes follow; the matplotlib default style keeps its own settings (× 1.0, normal).
- **Layout**: a panel with a title or subtitle gets extra room above it, so they never overlap the previous panel's x-axis label, tick labels or legend; a figure
  title gets its own room at the top. When the plot scrolls the canvas grows and every panel keeps "panel height"; when it fits in the window the titles take
  their room from the visible height (like the x-label gaps; a panel never drops below "panel height"). When the plot scrolls to a panel after a paste,
  adding files or Extract Signals, the panel's title and subtitle come into view too (a title belongs to the panel below it).
  - Item 11 is unchanged: every panel draws its x axis. When a smaller save size cannot fit them, the export labels only the bottom panel as before and says so;
    **titles, subtitles and the figure title are never hidden** (if even that does not fit, the title room shrinks together with the label gaps and the status
    line asks for more height).
  - **Tall x names** (math such as `$\frac{\sum_i a_i}{N}$` that is taller than one line of text): every x-label gap grows to fit the tallest one (the room
    is found the same way as for titles: when the plot scrolls the canvas grows and every panel keeps "panel height"), so the label never overlaps the next
    panel's axes, legend or title, and the bottom one stays above the drop strip.
  - **Collapsed rows** still show only "≡ P1": no name, no title, no title room (they come back when expanded). A collapsed bottom row's x label still uses the x name.
  - **Long names**: a y-axis or right-axis name longer than its panel's height is shortened with "…" (the P number and unit stay, nothing spills into other
    panels); x names, titles and subtitles longer than the axes width, and a figure title wider than all the axes, likewise (titles and subtitles also
    keep clear of the y axis exponent, e.g. the "1e6" at the top-left corner of a panel with large values). It is recomputed on every draw
    at the current size (also for exports of another size); the full text is kept and shown in the dialog. When a panel is too short even for "…", the name
    is left out (the label is the old "≡ P1 [V]", so a name never makes a label longer than in 0.9.9). Math is only cut outside $…$.
  - Names and titles keep at most 200 characters (the rest is dropped and the status line says so); line breaks and tabs become spaces (names are one line).
- **Export**: Save as image and copying the figure (PNG / PDF) take everything on screen; **Export This Panel Only…** takes that panel's title, subtitle and
  names but **not the figure title** (it belongs to the whole figure; MATLAB `exportgraphics(ax)` leaves out the sgtitle too; confirmed by the user in the
  third menu decision of 2026-10-27). New figure window / Paste to figure window copy only the signals, as before.
- **Undo**: renaming, titles and the figure title can be undone with Ctrl+Z / ⌘Z and redone with Ctrl+Y / ⌘Y; they never change any panel's x or y range
  (a manual y range stays). Units and Link Time still cannot be undone (unchanged).
- **They follow the panel** (same rule as the axes settings): reordering keeps them with the panel; delete a panel and Ctrl+Z brings them back; merging keeps the
  target panel's; moving signals away empties a panel and drops its names (Ctrl+Z restores them); Extract Signals copies the source panel's settings, names
  and titles included.
  - **Every new panel made from another one follows the same rule: it takes the source panel's axes settings, names, title and subtitle** (the user's second
    and third menu decisions of 2026-10-27): Extract Signals; a copy of a whole panel pasted back into that panel (item 13, see "Copying and pasting signals
    with ⌘C / ⌘V"); a whole panel cut with ⌘X and pasted with ⌘V; and **Split** — every panel split out takes the settings of the panel its signal came from.
    Splitting everything (no selection) gives every signal a new number (P1, P2… in list order) and the settings travel with the signals, so they never stay
    on a panel number and end up over another group's signals (before, P2's title and units landed on the signal split out of P1); the time span a panel was
    showing (when Link Time is off) travels too, and so do **the collapsed state and the legend position** (the user's fourth menu decision of 2026-10-27: with
    P2 collapsed and P3's legend dragged somewhere, splitting everything collapses the panels split out of P2 and gives the panel split out of P3 that legend
    position, not whichever other group's signals received the numbers 2 and 3; panels that are not split are left alone). **Different from 0.9.9**: on Split the
    axes settings (x / y unit, Symbol rate, Link Time), the collapsed state and the legend position also follow the source panel (0.9.9 left them on the panel
    numbers, so names and units would no longer match). Ctrl+Z undoes a split completely (every panel's settings, names, visible time span, collapsed state and
    legend position); Ctrl+Y splits again.
  - Pasting into a panel that already has names or titles leaves them unchanged.
  - **The collapsed state and the legend position follow the same rule** (the user's sixth menu decision of 2026-10-27): a copy of a whole panel pasted as a
    new panel (copy or cut, then ⌘V) and the new panel made by Extract Signals take the source panel's collapsed state and legend position, as Split does;
    cutting or deleting a whole panel, or moving all its signals away with Merge into One Panel or Edit Panel…, clears the collapsed state and legend position
    stored under its number, so a later panel that receives the same number no longer starts collapsed or with the old legend position (0.9.9 left them on the
    number); Ctrl+Z brings the panel back with both (also after Merge or emptying it, as in 0.9.9; fixed in the third review round on 2026-10-28).
  - **A whole-panel copy records the panel as it was when copied (or cut)** (the user's seventh menu decision of 2026-10-27; MATLAB copyobj): changing the source
    panel's axes settings, names, title, subtitle, collapsed state or legend position after copying and before pasting does not affect the pasted panel — copy and
    cut behave the same (before, a copy used the source panel's settings as they were when pasted). Values typed into the toolbar's Axes fields but not applied
    yet: typed before the copy they are committed to the source panel at copy time and travel with the copy; typed after the copy they only reach the source panel.
- **Clear** (remove all signals) **also removes the figure title** (like MATLAB clf; the user's third menu decision of 2026-10-27) and the status line says
  "Cleared n signals and the figure title"; Ctrl+Z / ⌘Z brings it back together with the signals and every panel's names. Before, the figure title stayed and was
  drawn again over the next, unrelated files. Deleting the signals one by one (not Clear) still keeps the figure title.
- **Saved** in settings, the autosave and exported settings: every entry of `panels` gains `title`, `subtitle`, `xname`, `yname`, `yname_right`, and the top
  level gains `figure_title`; an older file without them = blank. **Note: once an older version (0.9.9) opens the file and autosaves, these names and titles are
  lost** (it does not know the new keys); and **if a y unit contains invalid $…$ math, 0.9.9 cannot open the session at all** (it fails at startup and starts
  empty, keeping the whole session in `.signal_viewer_last.bad.json` — fix the unit before going back to 0.9.9, or import that backup with the new version).
  With "Auto-restore Last Session" off, closing saves only the preferences: the figure title, every panel's names and titles and the collapsed state are not
  carried over, just like the signals (the user's fifth menu decision of 2026-10-27; before, the figure title stayed in the file and was drawn over whatever
  file was added at the next start).
- **English UI**: menus, dialogs and the status line are in English; text typed by the user is never translated.
- Dropping a file on a panel's title adds it to that panel. Clicking or right-clicking a title itself does nothing (use the three right-click menus above).

### Clicking a panel: the list follows, a line click selects that line, every panel has an x axis, the panner follows (user-reported items 10, 11 and 12, 2026-10-25)
- **Click a panel on the right and the Plotted Signals list on the left selects all of that panel's signals** (hidden ones included; it replaces the previous
  selection and the list scrolls to the first selected row; below this is called "following"):
  - In Pan, Zoom and Data Tips mode, **clicking** an empty area or the legend of a panel (press and release moving less than 10 pixels) makes the list follow it;
    in Zoom mode the click still zooms in at that point. The status bar reads "Current panel: P2; its 2 signal(s) are selected in the list…", followed by
    "Ctrl+V / ⌘V pastes the n signal(s) on the clipboard" when the clipboard holds signals (also after a copy or cut; when the clipboard holds a copy of this
    whole panel it reads "Ctrl+V/⌘V pastes the copy of the whole P2 as a new panel", see "Copying and pasting signals with ⌘C / ⌘V" below).
  - **With no toolbar mode** (Pan, Zoom and Data Tips all off) a click on empty space **clears the list selection** (followed or your own), as in 0.9.8 and MATLAB's
    plot edit mode, and a click on the legend leaves the list alone; in this mode only a **click on the grip area** and a **right-click on empty space** (or on
    that panel's x tick labels or x label) make the list follow a panel.
  - A left click on a panel's **own x tick labels or "x [unit]" label** counts as a click on that panel's empty space (same rules; the panel becomes current on
    release); dragging there works as before (in Data Tips and no toolbar mode it pans that panel's x along the x ruler; in Pan and Zoom mode it does nothing, as
    in 0.9.8). A **right-click** on a panel's own x tick labels or label counts as a **right-click on that panel's empty space** in the same toolbar mode (since
    2026-10-25): the panel becomes current as soon as the button is pressed, the list follows it by the right-click rule (if you had picked some of that panel's
    signals yourself they stay selected and the menu acts on them) and the same menu appears — MATLAB's Pan-mode menu in Pan mode, MATLAB's Zoom-mode menu in
    Zoom mode ("Zoom Out" zooms about that panel's centre; both mode menus end with that panel's "Axes (P1)" and "Figure Title…" since 2026-10-27), the
    panel's own menu in Data Tips and no toolbar mode (Paste into the panel, analysis, reference
    lines…); the menu's "Insert Vertical / Horizontal Reference Line" and "Insert Text…" use the point straight above the pointer on the bottom edge of the axes.
    A right-click on the grip area or the × still opens the grip-area menu.
  - A click inside the axes (or on a panel's data tip box, text annotation or legend; either button, any mode) makes that panel the **current panel** (frame,
    panner, the toolstrip's Axes fields, AM/PM/FM) as soon as it is pressed, and **Ctrl+V / ⌘V pastes into it** (also after the current panel was cut or deleted,
    or right after start before any click: clicking the top panel then pastes into it instead of opening a new one; a copy of this whole panel is pasted as a new
    panel, as in MATLAB — see "Copying and pasting signals with ⌘C / ⌘V" below).
  - **Dragging never changes the list**: panning, zoom boxes, dragging with no toolbar mode, dragging a legend or the x ruler keep the list as it is (the dragged
    panel still becomes current). If the list is already following a panel, it follows the dragged panel (data cursors included), so the current-panel frame, the
    panner and the list agree.
  - A followed selection **only highlights the rows; the lines are not drawn thicker** (a click or a pan does not change how the waveforms look, nor saved or
    copied figures). Signals you select yourself in the list or on a line are still drawn thicker.
  - A **right-click on empty space** counts as well (all four modes): the list switches to that panel's signals; if you already selected some signals of **the same**
    panel in the list they are kept and the context menu acts on them. A right click on the grip area does the same (the menu, the frame, the panner and the list all
    show that panel). A right-click on one of the followed rows in the list keeps the whole selection and its menu acts on the panel (Remove asks "Delete P2").
- **A click on a line selects just that line** (in Pan, Zoom and no toolbar mode alike; since 2026-10-25 — Pan / Zoom used to select the whole panel): it is your own
  selection — drawn thicker, **⌘C / Ctrl+C copies only it**, Delete / ⌫ / Remove remove only it (no panel question), Shift+click adds / removes — and its panel becomes
  current. For example "click a signal in P3 → ⌘C → click an empty spot of P1 → ⌘V" pastes that one signal into P1. In Data Tips mode a click on a line pins a data tip
  (Shift+click selects the line).
  - It must be a click (release within 10 px); a drag that starts on a line still pans or draws a zoom box and keeps the list.
  - A followed selection is not your selection: after a panel click, **Shift+click on a line selects just the line you clicked** (as after clicking empty space in
    0.9.8); further Shift+clicks add / remove. On a panel with a single signal, clicking (or right-clicking) its line after the list followed the panel also makes it
    your own selection.
  - With a single line selected, AM/PM/FM, Constellation and GFSK analyze the **current panel** (the panel of the clicked line; one line is not an I/Q pair — item 9).
  - A right-click on a line opens that line's menu (Delete this signal, colour, line width…; the list then holds just that line) in Pan, Data Tips and no toolbar mode;
    **Zoom mode** keeps MATLAB's zoom-mode menu (Zoom Out, Restore View, zoom direction; "Axes (P1)" and "Figure Title…" added at the bottom) for every
    right-click, on lines too.
  - Clicking a data tip, annotation, reference line or data cursor works as before (in Data Tips and no toolbar mode it selects that object). While the list follows
    another panel, **clicking or right-clicking a data tip, annotation or reference line of this panel first clears the followed selection** (all four modes; the
    Pan / Zoom right-click menus stay as they are), and the frame and panner move to this panel, so Delete never offers to delete the other one.
    A data tip box, text annotation or legend belongs to **its own panel**, also when it is drawn outside the axes (a tip pinned at a peak often sits above the top
    edge; a legend can be dragged out) or overlaps another panel.
- **Delete / ⌫** while the list follows a panel **deletes that panel**, asking first per "Confirm before clearing" ("Delete P2 (2 signals)?") like the grip area +
  Delete and the ×, and undoable (after Ctrl+Z it asks again), so a single click never makes a whole panel vanish without a question. **Every entry point behaves the
  same**: all four modes, with the focus on the main plot, the list, the panner or the main window; the toolbar's Remove, the Plotted Signals panel's remove button and
  the list's right-click Remove also delete that panel after asking; **Ctrl+X / ⌘X** asks "Cut P2 (2 signals)?" before cutting the whole panel. Signals you select
  yourself are removed without a question: **signals picked on the plot** (a click, Shift+click or right-click on a line) in all four modes and wherever the focus is
  (in Pan / Zoom mode with the focus on the plot too, U1); **signals you picked in the list** (clicking rows, ⌘A) with the focus on the list, the panner or the main
  window, or on the plot in Data Tips / no toolbar mode, while in Pan / Zoom mode with the focus on the plot Delete / ⌫ leave them alone as in 0.9.8 (a drag on the
  plot followed by Delete never wipes out a ⌘A selection). "Wherever the focus is" above means the main plot, the list, the panner and the main window: with the focus
  in a **text field** or in the **Folder** file tree the keys belong to that widget (the field deletes or cuts characters; the file tree's Delete / ⌫ still only
  explains that it never deletes files on disk, and ⌘X only explains that it cuts no signal), so no signal is deleted or cut; ⌘C / ⌘V still copy the highlighted
  signals and paste into the current panel.
  With nothing highlighted in the list **⌘X cuts nothing** (only a selected data tip cuts its signal; ⌘C still copies the signal of the latest data tip).
- **Deleting removes exactly the highlighted or named signals** (2026-10-25): no entry point (the ×, grip area + Delete, a followed selection + Delete / ⌫ / Remove / ⌘X,
  your own list selection + Delete, a line's right-click "Delete this signal") takes along **derived signals** that were not selected (I/Q magnitude / phase / FM;
  from 0.9.10 also Preprocess results), **whichever panel they are in** (the same panel as their source too — results chained on them keep following them):
  they stay and **become independent signals** (their current data is kept and the link to the sources is dropped; the data is stored as .npy in
  `~/Library/Application Support/SignalViewer/frozen` on macOS or `%LOCALAPPDATA%\SignalViewer\frozen` on Windows, and the autosave keeps that path; the same
  data is stored only once, so repeated delete / ⌘Z does not pile up files; files nothing uses any more are deleted automatically, see the next item); the status bar
  says "the 2 derived signal(s) in P4, P5 stay as independent signals"; **Ctrl+Z brings back the sources and the links**. Every question names
  exactly what is removed. **Exception: Preprocess results that could not be computed go with their source** (0.9.13, user decision B4 of 2026-10-28): a result
  with 0 samples (Fmt = error in the list: the source is too short, has NaN, its own source could not be computed…) is removed together with its source
  (every entry point, Cut too), and so are results chained on it; it does not become a 0-sample independent signal and no empty .npy appears in the frozen
  folder. The status bar continues the sentence above with "; the 1 Preprocess result(s) in P2 that could not be computed were removed with it", the
  confirmation question gets an extra line "The 1 Preprocess result(s) in P2 that could not be computed will be removed with it" (the clipboard holds only
  the selected signals); **Ctrl+Z restores everything** (sources, results and links). Results that have data stay as independent signals as before.
  Deleting a placeholder whose file is missing (see "Opening while a source file is temporarily missing") works the same way: the Preprocess results waiting
  for it have no data and are removed with it (same status sentence, Ctrl+Z restores everything); its I/Q magnitude / phase / FM (a placeholder somewhere in their
  source chain, no data right now) **are removed with it too** (user decision of 2026-10-28: nothing to keep means nothing is pretended; no more U8 freezing into a
  0-sample empty .npy): the status bar adds "; the 1 I/Q derived signal(s) in P2 waiting for data were removed with it", the question gets "The 1 I/Q derived
  signal(s) in P2 waiting for data will be removed with it", every entry point (line right-click delete, Cut…) behaves the same, Ctrl+Z restores everything (links
  back, still waiting for the source); an I/Q derived signal waiting for data is handled this way whenever any of its sources is removed. Once the file is back,
  deleting the source follows the rule above for results with data (independent signal).
  Deleting never resets the y range you set by hand on another panel (every panel zooms on its own, item 8); Ctrl+Z restores the view of
  every panel exactly. Undo / redo of adding, moving or deleting a data tip or annotation keeps every panel's x and y range as it is now (a y range set by hand is
  not reset).
- **If the frozen folder cannot be written, nothing is deleted** (2026-10-25): before a deletion turns derived signals into independent signals (previous item),
  their data is saved in the frozen folder and read back to confirm it is identical bit for bit, and only then is anything removed (after you answer "Yes" when
  "confirm before clearing" is on). If the folder is read-only, the disk is full, a file or folder with the same name is in the way, or any other write error
  occurs, **the whole deletion (or cut) is cancelled**: nothing is removed, the derived signals stay linked to their sources, and the undo / redo history and the
  clipboard are unchanged; an error dialog names the derived signals that could not be saved, the folder path and the reason (e.g. "no permission to write
  ([Errno 13] Permission denied)"; a full disk or the file-size limit reads "not enough disk space" / "the file exceeds the size limit ([Errno 27] File too
  large)"), and the status bar says "Delete P2 (2 signal(s)): cancelled…". Every deletion entry point (the ×, grip area + Delete,
  a followed selection + Delete / ⌫ / Remove / ⌘X, your own list selection + Delete, a line's right-click "Delete this signal") and Cut behave the same. This also
  applies when the data is already in the folder and nothing needs to be written (e.g. after a deletion was undone with ⌘Z): if the folder cannot be written
  (read-only, no permission) the deletion is cancelled (a window opened while the folder is read-only cannot register in it, and another DSV could later clean
  those files up as unused). Make the folder writable and do it again; the files that were already saved are not used by anything and are cleaned up automatically later (next item). An old file
  with the right name but the wrong content (e.g. damaged by another program) is first rewritten with the correct data instead of being used as it is.
- **If the frozen folder cannot be written, nothing is pasted** (2026-10-26): when you cut or copied a derived signal (in the main window, or with "Copy Signals" /
  ⌘C / line right-click "Copy" in the AM/PM/FM window) whose sources were deleted afterwards, pasting it (⌘V, the axes right-click "Paste to Pn", the grip area
  right-click "Paste Signals to Pn", ⌘V inside the AM/PM/FM window, dragging a line from that window onto the main plot) turns it into an independent signal with
  the data it had when copied, and that data is first saved in the frozen folder and read back as well. If this window cannot register in the folder or the folder cannot be written
  (read-only — also when the data is already in the folder —, full disk, a file with the same name in the way, any write error), **the whole paste is cancelled**:
  nothing is pasted, the clipboard and the undo history are unchanged; the error dialog "Paste cancelled" names the signals, the folder path and the reason, and the
  status bar says "Paste into P3 (1 signal(s)): cancelled…". Make the folder writable and paste again (before, an empty derived signal was pasted silently and was
  gone after a restart). "Import Settings" of a file that carries independent signals' data is likewise cancelled as a whole, see "Settings and Auto-restore".
  **No window ever pastes an empty signal silently** (2026-10-26, round 10, U16): the main window and the AM/PM/FM window both copy derived signals with their
  whole data (computed from the current sources first when it was not computed yet; the AM/PM/FM window used to copy no data, so pasting after the sources were
  deleted gave an empty 0-sample signal); if a derived signal in the clipboard has no sources any more and no data (it could not be computed), the paste is
  likewise cancelled as a whole and the error dialog "Paste cancelled" names those signals; the clipboard and the undo history are unchanged (undo with ⌘Z to
  bring the sources back and paste again, or copy again while the sources exist).
  **"The sources still exist" means the same signals** (2026-10-26, round 11): copying records which two signals the I and Q sources are (file, column,
  extracted range); when the signal with that number has been replaced by another one at paste time (e.g. "Import Settings" replaced the whole session and the
  numbers in the settings file start at 1 again), the sources count as gone and the rules above apply: the copied data becomes an independent signal (if it
  cannot be saved, or there is no data, nothing is pasted). Before, only the number was compared, so the derived signal silently attached itself to unrelated
  signals and showed their data. Sources brought back by ⌘Z are the same signals and are linked again.
- **The data files of independent signals (the frozen folder above) are deleted automatically once nothing uses them** (since 2026-10-25): DSV cleans up **at
  start-up** and **every time the autosave has been written** (closing the app, ⌘Q, the restart after an update, changing the language in Preferences; nothing
  is cleaned when the autosave could not be written). "Something
  uses it" means any of: the current signals, undo / redo (every step Ctrl+Z / Redo can still reach), the signal clipboard (⌘V after ⌘C / ⌘X) and the **autosave**
  (the last session, restored at the next start; with "Auto-restore Last Session" off the autosave keeps no signals, so after closing the app nothing uses them and they are deleted at the
  next start — at the moment of closing the current signals and the undo history still exist) and the version backups next to the autosave (since 0.9.13; since 0.9.14
  one per version, the latest 3 versions kept, every one of them counts — see "Settings and Auto-restore"). While another DSV window is open nothing is cleaned (its signals and undo history cannot be seen, so DSV would
  rather keep the files; the only exception is a window that was opened before the frozen folder existed and has never used it, since it cannot be using any of
  those files — importing a settings file that only records the paths, or adding a file from that folder in the Folder panel, also counts as using it), and nothing
  is cleaned when the autosave cannot be read (damaged, wrong structure, no read permission, or the autosave is a symbolic link whose target is missing —
  e.g. an external disk not connected; round 11: a missing link target used to count as "no autosave", and start-up deleted every data file the last
  session used);
  **as long as any backup kept when the autosave could not be read (or had signals that could not be restored) exists next to the autosave** (`.signal_viewer_last.bad*.json`, see
  "Settings and Auto-restore"; copies or renamed ones you made count too, e.g. ".signal_viewer_last.bad copy.json") **no file is deleted at all**;
  the normal clean-up resumes only after you delete all the backups (2026-10-26, decision
  U15; before, only the files named in the backup's text were kept, so when the damaged file was cut off before "signals" or was all NUL bytes, the files the last
  session used were deleted at the first close and the repaired backup could not be imported any more). Two independent signals whose names differ only in letter case and that hold the same data share one
  file on macOS and Windows (file names ignore case there); it is kept while either of them uses it. Only DSV's own `<name>_<20-digit hash>.npy` files (and temporary files
  a crash left half-written) are deleted; any other file in that folder is never touched. **The JSON written by "Export Settings" carries the data of these
  independent signals inside the file** (`frozen_data`, compressed float64 that reads back bit for bit), so an exported file is complete on its own: it still
  imports correctly after the frozen files were cleaned up, or on another computer ("Import Settings" writes the data back into that computer's frozen folder).
  The autosave does not carry the data (the files it uses are never cleaned up). 0.9.8 had no independent signals, so older settings files are not affected.
- **Cutting (or copying) derived signals together with their sources and pasting them** (e.g. "click P2 → ⌘X → click P3 → ⌘V" moves I, Q and the phase kept in P2):
  the pasted derived signals point at the pasted sources and keep their data (they used to point at the cut originals and came out empty); a derived signal copied
  on its own whose sources were deleted before pasting becomes an independent signal with the data it had when copied (if that data cannot be saved in the frozen
  folder, nothing is pasted, see above). Preprocess results work the same way (added when merging 0.9.9): a result pasted on its own while its source still exists
  keeps following that source (it is recomputed when the source changes and does not become an independent signal); a chain (bandpass, then envelope) pasted
  together with its source points at the pasted copies all the way down.
- When the list's right-click "Split into Panels" or "Edit Panel…" (or "Merge into One Panel") moves the followed signals to other panels, or Preprocess "Apply" adds
  results to that panel (its membership changed), the list no longer stands for "that panel": it becomes your own selection (lines drawn thicker, AM/PM/FM says
  "list selection (P2/P4)"), exactly as if you had picked those rows by hand. So after Apply, Delete / ⌫, the toolbar Remove and ⌘X **no longer ask** "Delete P1…":
  they remove just those source signals (the results stay as independent signals; ⌘Z brings the links back), and Delete with the keyboard focus on the plot in pan /
  zoom mode removes nothing, as in 0.9.8 (user decision 2026-10-27: keep the 0.9.9 rule).
- **Esc** clears a followed selection (any mode; the current panel stays); a selection you made yourself in the list is kept. Once the list changes (Esc, picking
  rows in the list, clicking a line or a data tip) the status bar no longer says "its N signal(s) are selected"; it goes back to "Current panel: P2 (…)"; after
  Esc or picking rows following a grip-area selection it no longer says "P2 selected: Delete removes this panel…" either.
- Undoing a panel deletion (⌘Z) brings back the followed selection and makes that panel current again (frame, panner, AM/PM/FM).
- Clicking the **grip area at the left of a panel** (the "≡ P1" area) selects the panel (blue frame) and the list selects all its signals; **Delete / ⌫ deletes the
  whole panel** (asking per "Confirm before clearing"; derived signals that were not selected stay as above, whichever panel they are in); **Esc** cancels both (Delete then removes nothing); selecting
  other signals in the list deselects the panel. **All four modes behave the same** (since 2026-10-25): a click selects, **dragging reorders**, **double-clicking
  collapses / expands**, the cursor over the grip is a hand (also after panning or drawing a zoom box) and the status bar offers "drag to reorder"; the grip is
  outside the axes, so it never conflicts with panning or zooming. Click and drag are told apart as in the axes: a drag starts after moving 10 pixels.
  Double-clicking the × at the top left deletes just that panel (with "Confirm before clearing" off, the second click no longer collapses the panel that moved up).
- The reverse direction (selecting signals in the list makes their panel current) is not done; there is no keyboard shortcut for switching panels on the plot
  (← → pan / move data tips; "both buttons count" means the left and right mouse buttons).
- Actions that use "the selection, or everything when nothing is selected" (Export TXT, Spectrum, Extract Signals, the Measurements panel, glitch suppression…)
  act on that panel's signals after a panel click; to get everything back press **Esc** (or ⌘A / Ctrl+A to select all; with no toolbar mode a click on empty space also
  clears the selection). **The Measurements panel measures all signals when nothing is selected** (since 2026-10-25, the same "all" as Export TXT and Spectrum, up to 8
  columns; 0.9.8 showed nothing). While the list follows a panel click, AM/PM/FM, Constellation and GFSK analyze that panel (the title says P2); two signals you
  select yourself in the list still take priority and the title says "list selection (P2)" (item 9).
- MATLAB reference (R2025a Signal Analyzer): after the selected display changes, Signal Analyzer only tells the MATLAB side the display number; what happens next
  on the MATLAB side cannot be compared (the Signal table's own handling of a changed selected plot acts only in the Simulation Data Inspector's browse mode and does
  nothing in Signal Analyzer). The direct precedent for "the table switches to all signals of that plot" is SDI's browse mode: it takes every signal of the current
  axes and marks those rows as selected in the table. DSV's list shows it by selecting those rows.
- **Every panel draws its x axis** (x tick labels and an x label such as `x [ns]` or `x [symbol]`) whatever the units and Link Time, as the default (0.9.8 labelled only
  the bottom one of linked panels with the same units). Collapsed bars stay unlabelled (the bottom one is still labelled).
  - The layout is computed in inches: the gap below a labelled panel fits its tick labels and x label (computed from the plot font size, so a larger plot font in
    Preferences gets a larger gap) and never covers the next panel's axes or legend; **collapsed bars get no extra gap below them** (as in 0.9.8).
  - Panel heights: the canvas gets the panel height plus the label gaps. **When the canvas is taller than the window (it scrolls), every panel is as tall as in
    0.9.8** (the label gaps make the canvas taller); when it fits the window the panels stretch to fill it and never drop below the panel height, but the label gaps
    and the 0.25 in drop strip at the bottom come out of the visible height, so they are somewhat shorter than in 0.9.8 (more so with a larger plot font, about a
    fifth at 20 pt).
  - When a legend is taller than its panel (a panel with many signals, a very small panel height or a large plot font) **only that panel** grows to fit its legend
    (so a legend never covers its own x tick labels); the other panels keep their height. The legend height is measured from the drawn legend (CJK and accented
    capital labels make each row taller than ASCII ones, so an estimate from the entry count is not enough).
  - **Fit all in window** shares the visible height without scrolling; every panel's axes stays at least 0.5 in tall, a panel whose legend does not fit grows by itself
    and the others share what is left; the plot scrolls only when they cannot get 0.5 in. Because every gap holds x labels, many panels start scrolling earlier than
    in 0.9.8.
  - **Save as image with another width / height**: every draw lays the figure out again for its current size, so the labels still clear the next panel and the bottom
    one is not cut off. **The plot on screen, images saved at the current size (at any DPI) and copied figures always label every panel** (the on-screen layout).
    At another size **that export falls back to the 0.9.8 labelling** (of consecutive linked panels with the same units only the bottom one is labelled) when any of
    these holds — the rule does not depend on the style or font size, and the result never looks worse than the 0.9.8 labelling: (1) labelling every panel does not
    fit (legends, tick labels and labels exceed the height); (2) an expanded panel would be shorter than its own x-label gap; (3) a normal panel would be more than a
    third shorter than with the 0.9.8 labelling; (4) there are collapsed bars and every expanded panel is held up by its legend minimum (labelling every panel
    would leave the panels at their legend minimum). At another size a collapsed bar is always at least 0.22 of the shortest expanded panel (the 0.9.8
    proportion; also after falling back, so bars are never squashed and their titles never overlap). For example 3 panels at 6.4×4.8 in and 8 panels at 16×9 in
    label every panel; 5 panels at 8×4 in and 8 panels at 1920×1080 px (150 dpi) fall back. **After saving, the status bar says so**: "This size cannot fit
    x-axis labels on every panel, so this export labels only the bottom panel; make it taller to label every panel" (when units or Link Time differ and some
    middle panels keep labels: "…labels linked panels with the same units only on the bottom one of each run…"). When even the 0.9.8 labelling does not fit
    (or the legends would leave no gap between panels) the export uses the 0.9.8 proportions, so as in 0.9.8 a legend may spill over, and the status bar
    says both things ("This size cannot fit x-axis labels on every panel, so this export labels only the bottom panel; it is still too short, so legends and
    x-axis labels may overlap the next panel; make it taller"; when there is no labelling to fall back to — e.g. every panel has different units — it only
    says "This size is too short…").
    **"Export This Panel Only…"** (panel right-click): the width / height are still those of the whole figure, and the exported panel always keeps its own x tick
    labels and x label (only that panel counts; no fallback).
  - When the rightmost tick sits exactly at the right edge (e.g. x from 0 to 3000) the right margin grows so its label is not cut off by the figure edge; the right
    margin always fits half of a four-digit tick label (larger plot fonts included).
  - The crosshair read-out box is clipped to its axes (on a very short panel it does not cover the panel's own x tick labels).
  - Dropping a file on the tick labels or the "x [unit]" label under a panel adds it to that panel (the label belongs to the panel above; the bottom panel too, at any
    plot font size); the on-screen canvas keeps a 0.25 in blank strip at the very bottom (not in exported or copied figures), and dropping there (below the bottom
    panel's labels) means "new panel".
  - Cost: every panel draws one more set of tick labels, so redraws are slower than in 0.9.8: with 8 panels and 10 signals (1600×940, MATLAB dark, 10 pt) each redraw
    takes about 40 % longer (median canvas.draw about 85 ms in 0.9.8 and 116–123 ms now, +37 % to +45 %; the canvas is also taller, 1418 vs 1290 px in this case).
    Tick labels are digits only, so they use just the first font and skip the CJK fallback list (pixel-for-pixel the same), which saves about 7 % (alternating
    measurements in one process: 115 vs 124 ms).
- **The panner shows only the current panel's signals**: clicking another panel switches it at once to that panel's signals, full range and x unit (e.g. P1 in ns,
  P2 in symbol); a collapsed current panel still has its signals in the panner. Dragging the panner's zoom window moves the current panel, and linked panels follow
  through Link Time (different symbol rates are converted to the same time span); unlinked panels stay put. MATLAB reference: Signal Analyzer's panner is an axes of
  each display, and the panners of all displays are kept in sync.

### Copying and pasting signals with ⌘C / ⌘V (user-reported item 13, 2026-10-26)
- **Why nothing happened before** (measured with a copy of the user's autosave and real Tk events):
  - The user's P1 already held a copy of P2's q pasted earlier (key `…q#2`). Clicking P2's q → ⌘C → clicking P1 → ⌘V skipped the whole paste because "that
    source is already in that panel" (up to 0.9.9); the only feedback was the status bar "P1 already has these signals; nothing pasted". The click **did** make
    P1 the current panel and the keyboard focus **was** on the plot, so neither of those was the cause.
  - With the **Zhuyin (Bopomofo) input source**, Tk 8.6.13 translates keys with the current keyboard layout (`com.apple.keylayout.ZhuyinBopomofo`): the V key becomes
    "ㄒ", which has no keysym (`??`), so ⌘C and ⌘V (and ⌘Z, ⌘A… every ⌘ / ⌃ shortcut) matched nothing: nothing happened and the status bar did not change.
  - **One key press never pasted twice**: Tk's default macOS Edit menu does take the ⌘V key equivalent, but it sends the paste action with the menu itself as the
    sender (not a menu item), so Tk generates no `<<Paste>>` (measured); only choosing Edit ▸ Paste with the mouse sends `<<Paste>>`.
- **The rules now** (MATLAB plot edit's Paste; the user's menu decisions of 2026-10-26):
  - **⌘V / Ctrl+V pastes into the current panel** (the last one clicked) and **does not check for duplicates**: if that panel already has the same signal (an earlier
    #2 copy) another copy is pasted and its key gets the next number (#3…; copying `q#2` and pasting gives `q#3`, not `q#2#2`).
  - A **single line** (selected by clicking it, or your own list selection) **pasted back into its own panel** adds another copy to that panel.
  - A **whole panel** (selected by clicking the panel's empty area or its grip — the list "follows" it) **copied and pasted back into the same panel** is **pasted as a
    new panel**, added at the bottom (like every other new panel); hidden signals stay hidden and **the panel's axes settings (x / y unit, Symbol rate, Link
    Time), names, title, subtitle, collapsed state and legend position are all copied** — the same rule as Extract Signals and Split (the user's second and sixth
    menu decisions of 2026-10-27; before, the names and titles were left blank), and **as recorded on the clipboard at copy time**: changing the original panel
    after copying and before pasting does not affect the pasted panel (the seventh menu decision; MATLAB copyobj; copy and cut behave the same); the current
    panel stays the original one, so pressing ⌘V again pastes another new panel (as pasting copied axes again does in MATLAB).
    Status bar: on copy "Copied the whole of P2 (2 signal(s)): press Ctrl+V (macOS ⌘V)
    now to paste it as a new panel…", on clicking that panel "Ctrl+V/⌘V pastes the copy of the whole P2 as a new panel", after pasting "Pasted the 2 signal(s)
    of the whole P2 as the new P4…"; the right-click menu item (plot and grip) reads "Paste as a New Panel (Copy of the Whole P2)".
  - **A whole panel cut with ⌘X and pasted with ⌘V** works like cutting and pasting axes in MATLAB (the user's third menu decision of 2026-10-27): the clipboard
    keeps that panel's settings (axes settings, names, titles, collapsed state, legend position; values typed into the toolbar's Axes fields but not applied yet
    are taken too), and ⌘V pastes it as a new panel at the bottom with all of them (before, it got the new-panel defaults and lost them); the collapsed state and
    legend position stored under the cut panel's number are cleared (the sixth menu decision), so the rebuilt panel behaves the same whether it gets the same
    number or a new one. The rebuilt panel becomes the current panel and from then on
    counts as "the panel it was copied from": **⌘V again pastes another new panel** (as for a copied whole panel) and **never into the rebuilt one** (before, the
    second ⌘V put a #2 copy into it); clicking another panel and pressing ⌘V still pastes into that panel. If nothing else was clicked after the cut (the
    current panel is gone), ⌘V also pastes a new panel with the settings.
  - A whole panel copied and **pasted after clicking another panel goes into the clicked panel** (the user's 2026-10-22 request "click P3's signals, copy, click
    the P1 pane, paste").
  - The right-click "Paste to Pn", the grip right-click "Paste Signals to Pn" and ⌘V inside the AM/PM/FM window follow the same rules. **Dragging a line from the
    AM/PM/FM window onto the main plot** is unchanged: a pair already in that panel is not added again (the status bar says to use Ctrl+C/Ctrl+V for another copy;
    the user confirmed this on 2026-10-27 and a GUI test now covers the rule and its message).
  - **One key press pastes once**: if a key press ever delivers both the key event and `<<Paste>>` (another Tk version or platform), the same action from one key
    event and one virtual event less than 50 ms apart, the second arriving within 1 s after the first finished, counts as one key press and runs once; pressing
    twice pastes twice; choosing **Edit ▸ Paste with the mouse** (only `<<Paste>>`) **still pastes**. ⌘C, ⌘X, ⌘Z and ⌘A work the same way, and so do ⌘C / ⌘V in
    the Plotted Signals list and in the AM/PM/FM window.
  - **A successful paste's message is never overwritten**; when nothing is pasted the reason is given: the clipboard is empty (an information box), the frozen
    folder cannot be written (U11, error dialog), a derived signal's sources are gone and there is no data (U16, error dialog), the dragged pair is already in that
    panel (status bar).
  - **Zhuyin and other non-Latin input sources**: while ⌘ or ⌃ is held, keys are recognised by their physical position (ABC layout), so ⌘C copies and ⌘V pastes,
    as in other Mac apps — every ⌘ / ⌃ shortcut of the main window, the Plotted Signals list, and ⌘C / ⌘V of the AM/PM/FM window. Since 2026-10-27 figure windows,
    every analysis window, the measurement and cursor tables, text fields and dialogs, and the plain `[` / `]` / ⇧`[` / ⇧`]` / `-` keys work the same way (see
    "Zhuyin, Russian, Greek and other non-Latin input sources" under Keyboard Shortcuts).
  - U11, U16 and "derived signals point to the sources pasted with them" are unchanged.

### Signal Properties → View / Diff
- The internal x unit is always symbol; the display unit can be symbol / ns / us / ms, converted with the Symbol rate (default 1 MHz) — **for the current panel**,
  see "Clicking a panel"; y unit and Link Time; panel height.
- x range "from … to …" and "Show All".
- Difference: when a panel has 2 or more signals, they are sampled at the step of the highest SPS, and wherever the values differ by more than the tolerance a semi-transparent red range is drawn;
  tolerance, y-stack offset and the Normalize Y check box are here; Highlight Diff Regions, Dashed Lines, Previous Diff / Next Diff are on the toolstrip's "Analyze" tab.
- The crosshair shows the x value and each signal's value at that position; when the signals in one panel differ there, "≠" is prepended.

## Edit Lines and Overlay Them in a Figure Window, MATLAB-style (v3.2)
- **On start the plot toolbar is in Pan mode and Data Tips are off** (user's choice, 2026-10-24; turning Data Tips on is remembered in the settings file as `view.tips`,
  an old file without that key means Pan). In Pan mode a right-click **on a line** still opens the signal's menu (Delete this signal, colour, line width…); a right-click on empty space is MATLAB's pan-mode menu; in Zoom mode every right-click is MATLAB's zoom-mode menu (both mode menus now end with "Axes (P1)" and "Figure Title…", the user's 2026-10-27 decision).
  With Data Tips on, **click a line directly on the plot** to pin a data tip (as in MATLAB R2025a; see "Data tips" below); **Shift + click a line** to select that signal
  (the list selects it too and the line is drawn thicker), Shift + click again to multi-select or deselect. With the "Data Tips" button turned off a plain click on a
  line selects it, **in Pan and Zoom mode too** (since 2026-10-25, see "Clicking a panel" above). A click on an empty area: with no toolbar mode it deselects (as in
  0.9.8); in Pan, Zoom and Data Tips mode the list selects all signals of that panel (press Esc to deselect). Tips are not pinned while the toolbar's zoom / pan mode is on.
- **Double-click a line** (with "Data Tips" off) to open the color dialog; the **right-click** menu (it selects the line first) has: Color…, Line Width ▸ (MATLAB's fixed line-menu values
  0.5, 1.0 … 12.0, plus "Custom…"), Line Style ▸ (auto / solid - / dash -- / dot : / dash-dot -. / none), Marker ▸ (MATLAB's 14: none + o * . x s d v ^ > < p h),
  Marker Size ▸ (2 4 5 6 7 8 10 12 18 24 48, plus "Custom…"), Reset Style, Copy Signals, Copy to New Figure Window. The list's right-click menu and the buttons below it offer the same functions.
- Line color, width and style are saved in the settings JSON and restored on import; the text color of a signal name in the list is its current line color.
- **Copy into another panel (like pasting a line into another MATLAB axes)**: select signals (in the list or Shift+click on the plot), press Ctrl+C (⌘C on macOS),
  click inside the target panel's axes in the main plot and press Ctrl+V (⌘V): the signals are copied into that panel (the right-click menu on empty space also has "Paste Signals into Pn");
  Ctrl+X (⌘X) cuts, so pasting moves them; as in MATLAB there is no duplicate check: a source already in that panel is pasted again (key with #2, #3…), and a
  copy of a whole panel pasted back into that panel becomes a new panel (item 13, 2026-10-26, see "Copying and pasting signals with ⌘C / ⌘V"; before, sources
  already in that panel were skipped), and a whole panel cut and pasted with ⌘V also becomes a new panel with that panel's settings and names (like cutting
  axes in MATLAB); Ctrl+Z undoes.
- **Copy-paste overlay**: after Ctrl+C, press Ctrl+V (⌘V) in a figure window to overlay, or press "Copy to New Figure Window" to do it in one step.
- **Figure window**: all pasted signals are overlaid in one plot; the list on the left allows multi-select, clicking a line on the plot pins a data tip, Shift + click selects, and the right-click menu works as in the main window;
  it has Color / Line Width / Line Style / x shift / y shift / Rename / Delete / Clear; selected lines can be copied again into another figure window.
  What is pasted is a snapshot of the data as displayed at that moment (x already converted to the display unit in use); later changes in the main window do not affect it;
  the toolbar's save button saves it as an image file (export dialog: format, DPI, background, size); Ctrl+W (macOS ⌘W) closes the window. Figure windows are not saved in the settings file.

- **Every plot panel is movable too**: move the mouse onto the **whole "≡ P1" area at the left of a panel** (including the y tick labels; the cursor becomes a hand) and simply **drag** to reorder the panels; in the main window the y tick area is this grab handle, so ruler-drag panning applies to the x ruler only; right-click on a panel or its handle also offers "Move panel up", "Move panel down" and "Delete this panel" (delete removes all signals of that panel in one Undo step; confirmation follows the "confirm before Clear" preference);
  **right-click on a line also offers "Delete this signal (name)"**: only that signal (derived signals that were not selected stay as independent signals, whichever panel they are in), the same as Remove in the list, undoable (added 2026-10-24); while dragging a panel a blue line shows where it will land;
  **double-click** there to collapse the panel to a thin bar (no lines drawn, data tips kept; double-click the bar to expand); the right-click menu has Move Up / Move Down / Collapse / Hide This Panel's Signals / Paste Signals.
  Dragging to reorder, double-clicking to collapse, a click to select and the right-click menu **work in all four modes** (Pan, Zoom, Data Tips and no toolbar mode; the grip is outside the axes; since 2026-10-25). Esc cancels a drag.
  Each panel has an **×** at its top-left: it turns red on hover and deletes the panel when clicked (asks first per "Confirm before clearing", undo with Ctrl+Z / ⌘Z;
  the × is an on-screen button and is never saved or copied with the figure). **Click** the grip area once (without dragging) to **select the panel** (a blue frame
  appears and the list selects all its signals; in every mode); then **Delete / ⌫ deletes the whole panel**, Esc cancels (the list selection too);
  clicking inside a plot or selecting other signals in the list deselects the panel. Delete order: selected data tip →
  selected annotation → selected panel → a list selection that follows a panel click (= delete that panel, asking per "Confirm before clearing") →
  signals you selected in the list; with nothing selected, Delete removes nothing.
  The order is undoable with Ctrl+Z and the collapsed state is kept in the autosave.
- **Adjustable layout**: **drag a panel by its title bar** to another column (a blue line shows where it will land; dropping at the far left / right edge opens that empty column; Esc cancels),
  or use the ▾ at the right of the title bar (or a right-click on it) to move the panel to the left column, the center column (below the plot) or the right column,
  move it up or down, maximize it (double-clicking the title bar works too) or hide it; the dividers between columns and between panels in a column can be dragged.
  "View → Layout" has "Default Layout", "Plot Only" and a show/hide switch for each panel; the layout is kept in the autosave file and restored on the next start.
  While a panel is maximized, moving, reordering or hiding from the menu first restores the layout (the dock never goes empty); Move Up / Down counts only visible panels.

## v3.3: Interactions Added to Match MATLAB (provided by plotkit)
- **Wheel**: when the plot fits the window, the wheel over the plot zooms both axes around the cursor, 1.1x per notch and zooming out stops at the original range (MATLAB default); when there are **more panels than fit** (a scrollbar appears on the right),
  a plain wheel **scrolls** the plot area to reach the lower panels, and ⌘ (Ctrl on Windows)+wheel zooms instead.
  Shift+wheel zooms x only, ⌘/Ctrl+Shift+wheel zooms y only, Alt / Option+wheel always scrolls; outside the axes (between panels, in the margins, on the scrollbar) the wheel scrolls too.
  Wheel zoom can be turned off on the "View" tab; or tick "Fit all in window" under "Signal Properties → View / Diff" so every panel shares the visible height and nothing scrolls (each axes stays at least 0.5 in tall and tall enough for its legend; it scrolls only when they do not fit).
  macOS trackpad: a two-finger vertical swipe zooms (the amount follows the duration of the swipe — a light swipe is about 2×, never thousands of times);
  pinch-to-zoom is not supported (Tk 8.6 does not pass that gesture to the program) — use the magnifier on the toolbar above the plot for box zoom.
- **Drag to pan**: left-drag anywhere on the plot (on a line too; it becomes a drag only after the pointer moves 10 px, less than that is a click); dragging an x/y ruler (the tick labels) pans along that axis only (the pointer becomes a left-right / up-down double arrow); the arrow keys pan by 5 px per press (as in MATLAB).
  **Reset View**: double-click an empty area, the Home key, the plot toolbar's Home or the right-click menu return to the view before the first zoom/pan
  (MATLAB's Restore View; a range set in the x-range fields counts as that view; before any zoom/pan it shows all). "Show All" is what shows the whole data.
  While the toolbar's zoom / pan mode is on, dragging goes to the toolbar and data tips pause (the wheel still zooms); a click on a line still selects just that line and a click on empty space makes the list follow that panel (see "Clicking a panel"); in pan mode the arrow keys still pan, double-click resets the view, right-click opens the menu and right-drag does not zoom. Zoom mode follows MATLAB: click = zoom in 1.5x around the point,
  Shift+click = zoom out, drag a box = zoom to it (a side under 15 px zooms the other direction only), Esc while dragging = cancel, double-click = reset, right-click = mode menu, ↑/↓ or +/− keys 1.1x.
  The box is a 1 px blue solid line (it appears after a 10-pixel drag; a thin box becomes a 15 px band). Cursor: crosshair in zoom mode, an open hand in pan mode (a hand on Windows); redraws do not flash a wait cursor.
- **Data tips**: click a line to pin a tip (signal name, x, y; "Data Tips" is **off by default and the toolbar starts in Pan mode** — user's choice, 2026-10-24; turning it on is remembered;
  with it on a click pins a tip as in MATLAB, with it off a click selects the line instead); several are allowed and they can be dragged; click a tip and press Delete,
  or right-click to delete / clear all; with a tip selected, →/↑ move it to the next sample and ←/↓ to the previous one (this takes priority over arrow-key panning and can be undone). After a redraw or parameter change the tips stay on the same sample point; they are saved in the settings file.
  As in MATLAB R2025a, **moving the pointer onto a line** (within ±2 px of it) changes the cursor to a crosshair and marks the nearest sample; after 200 ms a temporary tip appears, it goes away when you move off, and a click pins it (temporary tips are not in Undo).
  The tip shows "signal name / X value unit / Y value", with numbers in MATLAB's auto format (6 significant digits, exponent only when |value| < 1e-4 or ≥ 1e15, e.g. 1234570, 1.23457e-05).
  The look follows MATLAB: a square box with no leader line, the axes background color and a grey border; **the selected tip has a blue border**. The box sits at the upper right of the point, moves below it when there is no room above and to the left when there is no room on the right,
  and is re-placed after panning / zooming (tips you dragged stay put); when the point leaves the view the whole tip is hidden until it comes back.
- **Double-click the legend to rename**: double-click a legend entry to rename it in place (Enter confirms, Esc cancels); this also works in the Spectrum window (recomputing the spectrum goes back to the signal names).
  Double-clicking inside the legend box but not on a label (line sample, blank space) does nothing (as in MATLAB); it does not restore the view.
- **Drag the legend** (as in MATLAB, no mode needed): press on the legend (label or box) and drag to move it; the axes do not pan; Esc while dragging cancels; it can be dragged outside the axes.
  **Each main-window panel's legend position (the dragged coordinates or the position chosen from the right-click menu) is also saved in exported settings files and
  in the autosave** (since 0.9.11; the `legend_loc` key, panel number → loc name or coordinates) and comes back on import and on "Restore last session" at start-up;
  panels whose legend was never moved are not written (= top right). With "Restore last session" off only preferences are saved, so it is not kept — like the collapsed
  state, names and signals (the fifth menu decision, item 1); programs older than 0.9.11 ignore the key, files older than 0.9.11 have none (= all top right), and a
  hand-edited value that is not valid is skipped without breaking the plot. Split, pasting a whole panel as a new panel and Extract Signals still carry it with the
  signals; deleting the panel clears it and ⌘Z brings it back.
  The main window remembers the position per panel and keeps it on redraw; the Spectrum window keeps it when recomputing; in figure windows the position is saved in the JSON and can be undone with Ctrl+Z.
- **Right-click the legend** for the legend's own menu (like MATLAB's legend context menu): "Delete legend", "Location ▸ Northeast / Northwest / Southeast / Southwest / Best"; no line-style items.
  In the main window "Delete legend" turns the "Legend" switch off (for all panels).
- **Show / hide**: click the ☑ in the first column of the list to toggle; hidden signals are not drawn, not compared and not in the legend, but stay in the list (grey text). Also in the right-click menu.
- **Marker and size**: right-click menu "Marker ▸" and "Marker Size ▸"; lines with more than 50,000 points get no markers (the status bar says so).
- **Dual y axes**: right-click "Right Axis" draws the signal on that panel's right axis; difference comparison is only done between signals on the same side.
- **Annotations**: right-click an empty area for "Insert Vertical Reference Line (x here) / Horizontal Reference Line / Text…"; text can be dragged; right-click an annotation to edit / delete. x is saved in the settings file in symbol units.
  Click an annotation (text or reference line) to select it (the text frame / the line gets thicker); Delete removes it (Ctrl+Z undoes), Esc deselects; right-click selects it first too.
  Annotation, data-tip and signal selections are mutually exclusive; Delete removes the selected data tip → the selected annotation → the selected signals, in that order (like selecting an object in MATLAB plot edit and pressing Delete).
  The look follows MATLAB R2025a's xline / yline / text defaults: solid line, width 0.5, alpha 0.7, 10 pt text; a vertical line's label runs along the line (rotated 90°),
  on its right side, 5 px below the top of the axes; a horizontal line's label sits at the right end above the line; when the line leaves the axis range its label disappears too.
- **Undo / Redo**: Ctrl+Z / Ctrl+Y (macOS ⌘Z / ⌘Y also work) or the ↶ ↷ at the top right of the toolstrip; covers style, list, parameters, despike, annotations, data tips, import;
  consecutive slider and drag actions within 2 seconds count as one entry. **Keyboard** zoom and pan (+ / −, arrow keys) are undoable too: Ctrl+Z first undoes
  the view, a held key counts as one entry (MATLAB figures do the same: keyboard pan/zoom goes into Edit > Undo on key release); in the Spectrum / GFSK / Constellation / Eye Diagram
  windows Ctrl+Z / Ctrl+Y undo and redo keyboard zoom and pan. Wheel, drag and selection are not undoable. In the main window Ctrl+S (⌘S) = Export Settings and
  Ctrl+O (⌘O) = Import Settings (MATLAB File > Save / Open); on macOS F2 / F3 / F4 no longer act as Cut / Copy / Paste (a Tk legacy Sun-keyboard mapping MATLAB does not have).
- **MATLAB style**: since v3.4 the MATLAB style is the default (following the theme: dark / light; the other looks use their own matching plot styles); "View → Appearance → Style → matplotlib" switches back to the matplotlib look.
  The values were taken from MATLAB R2025a (`docs/matlab-ui-spec.md`).
- **Copy Figure to Clipboard**: button or right-click menu; the whole figure is put on the system clipboard as PNG (PowerShell on Windows, osascript on macOS),
  ready to paste into Word / PowerPoint; on failure the status bar gives the PNG path. The temporary PNG is deleted only after a successful copy, once PowerShell /
  osascript has finished (a file that is still being read is never deleted); on failure (including being stopped after 20 seconds) it is kept for you and later copies
  do not delete it either; on Windows every time you close DSV it reminds you where such files are, until you deal with them yourself (user decision of 2026-10-30:
  keep them, but say on every close where something is left to handle; see "A reminder of unhandled files when closing" under "Settings and Auto-restore". The first
  0.9.14 build deleted the files earlier DSV runs had left before the next copy; that is gone).
  **Copy as Vector Graphic (PDF)** (toolbar, Export → Image File, right-click): MATLAB's axes toolbar Export → Copy as vector graphic;
  puts a PDF on the clipboard (macOS «class PDF », Linux xclip / wl-copy application/pdf). Windows has no usable vector format (MATLAB uses EMF),
  so on Windows this button and menu item are greyed out and the tooltip points to Copy Figure to Clipboard or Save Figure As… (PDF / SVG).
- The **figure window** is now plotkit's window: it has a menu bar (File: Open / Save JSON As…, Save Figure As…, Copy Figure; Edit; View; Insert),
  a signal list on the left and the same interactions; a file saved with "Save As JSON" can be reopened on its own with `python -m plotkit figure.json`.

## Measurements, Transitions, Normalize Y (after MATLAB Time Scope / Signal Analyzer / Logic Analyzer)
- **Measurements panel** (Measurements → Measurements; View → Layout → Measurements; below the plot by default and hidden on every start until you press it; it can be moved and collapsed like the other panels, and a moved panel keeps its place): computed for the signals **selected**
  in Plotted Signals (**all signals when nothing is selected**, the same "all" as Export TXT and Spectrum; up to 8, one column each; since 2026-10-25 — it used to stay
  empty without a selection) over the **Range**. The Measurements tab has Statistics / Peaks / Bilevel sections (Time Scope's STATISTICS / PEAKS / BILEVEL)
  with a switch for each group, and the table is grouped by the groups that are on; by default only Signal Statistics and Cycles are on (Time Scope also starts with Peaks, Transitions and Aberrations off):
  - **Signal Statistics** (Time Scope Signal Statistics / Signal Analyzer Measurements): samples, Max and Min (with the x of the first occurrence), Peak to Peak, Mean,
    Variance and Standard Deviation (N−1, like MATLAB `var` / `std`), Median, RMS, Mean Square. NaN / inf are ignored.
  - **Peaks** (Measurements → Peaks → **Peak Finder**; Time Scope Peak Finder): finds the **Num Peaks** highest peaks in the range (default 3); the table lists "value @ x" for P1…PN
    and the plot marks them with ▼ in the line color (tick **Label Peaks** to add P1… labels). Parameters follow MATLAB `findpeaks`: **Threshold** (default 0; above 0 a peak must exceed
    both neighbors by that much, so plateaus do not count), **Min Height** (blank = no limit; the peak must be greater), **Min Distance** (default 1 sample; of peaks closer than that only the higher one stays).
    A plateau counts at its first sample, the end points are never peaks, and the values are sorted in descending order.
  - **Bilevel** (Measurements → Bilevel: **Transitions**, **Aberrations**, **Cycles** switches plus **Bilevel Settings…**; Time Scope Bilevel Measurements). The definitions follow MATLAB
    `statelevels`, `risetime`, `falltime`, `slewrate`, `overshoot`, `undershoot`, `settlingtime`, `midcross`, `pulsewidth`, `pulseperiod` and `dutycycle`, and were compared value by value
    with numbers computed by MATLAB R2025a (reference data in `tests/matlab_ref/`, generating scripts in `tools/matlab_ref/`; `--selftest` compares them every time):
    - State levels: the most populated bin of the lower and the upper half of a 100-bin histogram, at the bin center (a 0/1 digital signal gives 0.005 / 0.995); or turn auto off in Bilevel Settings… and type High / Low.
    - Transition: the signal leaves one state's tolerance band (State Level Tol., default 2 % of the amplitude) and then enters the other's; runts that never reach the other side do not count.
    - **Transitions** group: + / − Edges, Rise / Fall Time (first lower-reference crossing to last upper-reference crossing, default 10 % / 90 %, linearly interpolated), + / − Slew Rate.
    - **Aberrations** group (% of the amplitude): + / − Preshoot (before the transition), Overshoot / Undershoot (largest deviation above / below the final state within 3 rise times after it),
      Settling Time (from the mid-reference crossing to the last exit from the tolerance band, looked for over Settle Seek, default 0.02 s; — when the data is too short or another transition starts first).
    - **Cycles** group: + / − Pulses, Period (spacing of consecutive mid crossings in the same direction), Frequency, + / − Pulse Width (between mid crossings), + / − Duty Cycle (width / period of each pulse, averaged).
    - The table shows the average over the transitions / pulses; the edge and pulse counts are totals (as in Time Scope). Times are in x-axis units, converted to seconds with the Symbol rate
      in parentheses when the x unit is symbol; frequency is in Hz (= Symbol rate / period). The bilevel settings (Auto State Level, High, Low, State Level Tol. (%), Upper / Mid / Lower Ref. Level (%),
      Settle Seek (s)) are saved in the settings.
  - **Range**: "Current x view" = the x range the main plot shows now; recomputed after zoom, pan, a new selection or a redraw (about 150 ms after things stop, not on every drag step).
    Nothing is computed while the panel is hidden.
  - **Items…** (or right-click the table): the five group switches on top, then the measurements to list, plus All Items / Statistics Only / Bilevel Only; saved in the settings (`view.meas_rows`; range source `view.meas_range`).
  - **Copy** (the copy button in the title bar, ⌘C / Ctrl+C in the table): puts the table on the clipboard as TSV (header, rows, range), ready to paste into Excel.
- **Previous / Next Transition** (Analyze → Transitions, shortcuts **`[`** / **`]`**; ← → already pan 5 px / move data tips, hence the brackets):
  moves the view to the nearest value change (a sample that differs from the previous one) of the selected signals (several = combined) left / right of the view center, centered, same zoom;
  with the crosshair on, the crosshair is drawn there too. Pressing again walks one transition at a time; the jumps go into Previous / Next View. `[` / `]` still type normally in entry fields.
- **Normalize Y** (View → Show; also a check box in Signal Properties → View / Diff): every line in a panel is divided by its own peak absolute value before drawing (Signal Analyzer's Normalize Y),
  so signals of very different size can be overlaid to compare shapes; works together with the y-stack offset, the y label gets `[norm]`. Display only: the data, the crosshair and data-tip values,
  measurements and exports keep the original values. Saved in the settings (`view.normalize`).

## Panner and Extract Signals (after MATLAB Signal Analyzer's Panner and Extract Signals)
- **Panner** (View → Zoom → **Panner**; hidden by default, as in MATLAB): a strip under the plot shows the **current panel's** displayed signals over their entire duration
  (MathWorks: "The panner renders signals in their entire duration"; since user-reported item 12, 2026-10-25, only the current panel: clicking another panel switches
  to it and its x unit — it used to overlay every panel); **the zoom window is the current panel's x range** and follows zoom and pan.
  As documented: **click the panner and drag to create a zoom window**, **drag its edges to resize it**, **drag its middle to slide it** along the signal (it stays inside the signal range);
  Esc cancels a drag; a click without dragging changes nothing. Releasing puts the range into Previous View (like zooming and panning the main plot with the mouse it is not a Ctrl+Z undo step; use Previous View or Home to go back). Dragging the zoom window moves the current panel; linked panels follow through Link Time.
  Each signal is scaled to the same height (a DSV choice: signals in one panel can differ in size by a factor of a thousand) and the area outside the zoom window is dimmed. The on/off state is saved in the settings (`view.panner`).
- **Extract Signals** (View → Region of Interest → **Extract Signals ▾**; also on the plot's right-click menu; MATLAB Display tab → REGION OF INTEREST → Extract Signals):
  - **Between Time Limits** = the current x range; **Between Time Cursors** = between the two data cursors (turn on two cursors first; the item is grayed out otherwise, as in MATLAB).
  - With signals selected only those are extracted, otherwise every displayed signal; on the plot, right-click a line to extract just that line, or an empty spot of a panel to extract that panel's displayed signals.
  - Every source gives one new signal named after it plus **_ROI** (MATLAB's naming; _ROI2… when taken) holding the samples in the range (both ends included), with the source's read format,
    glitch suppression, shift / scale and style. Signals extracted from one panel share one new panel added at the bottom (MATLAB adds them at the bottom of the Signal table);
    the new signals are selected and the plot scrolls to them.
  - **Preserve Start Time** (MATLAB Preserve Start Time, off by default): on = the new signals start at their original x; off = they start at 0 (handy for overlaying several regions),
    and if the current x range cannot show them it moves to the new signals.
  - A signal with fewer than two data points in the range is not extracted, with MATLAB's warning ("Unable to extract signal regions. Regions must contain at least two data points within the time limits.").
  - Extracted signals do not depend on their source (deleting the source keeps them) and are saved in the settings (`roi` = the sample range of the source data); glitch suppression runs on
    the whole source and is then cut, so the values equal that part of the source exactly. ⌘Z / Ctrl+Z undoes.

## Preprocess (after MATLAB Signal Analyzer's PREPROCESS tab)
The **Preprocess** toolstrip tab follows the FUNCTIONS gallery of MATLAB R2025a Signal Analyzer's PREPROCESS tab: three sections, **Filter**
(Lowpass / Highpass / Bandpass / Bandstop), **Clean** (Smooth / Detrend) and **Convert** (Resample / Envelope), one big button each (MATLAB also has
Denoise (Wavelet Toolbox), Fill Missing and custom functions, which DSV does not implement). A button opens the **Function Parameters** panel (one panel,
as in MATLAB; another button swaps its content): the header ("Lowpass Parameters", …), panes, field order, defaults, unit lists, show/hide rules and validation
messages follow MATLAB (the English text MATLAB shows in its interface), with **Apply / Restore Defaults / Help**. Empty text fields show MATLAB's placeholders ("Enter Value" for
Passband Frequency / Stopband Attenuation / Sample Factor, "Specify comma-separated values" for Piecewise Breakpoints); what was last typed for each function is remembered for the
session (on a function swap, Apply, Restore Defaults, and when the panel is closed with Esc or the close button). Every control has a tooltip and all eight functions are
keyboard-assignable actions (category "Preprocess").
- **Results are derived signals** (user decision 2026-10-24: MATLAB overwrites the selected signals and offers Undo Preprocessing; DSV adds a new row and keeps the original):
  **Apply** adds one result for every signal selected in Plotted Signals (MATLAB also applies to the signals selected in its signal table), named after the function MATLAB's
  generated code would call: `lowpass(name)`, `smoothdata(name)`, `detrend(name)`, `resample(name)`, `upperEnvelope(name)` / `lowerEnvelope(name)`, placed right after the source
  in the same panel, with the function name in the list's Fmt column. The parameters are stored on the signal (settings `signals[].derive` = pp_lowpass … pp_envelope_lower,
  `src` = the source uid, `pp` = the parameter dict: frequencies in Hz, times in seconds, plus the display units) and **the result is recomputed whenever the source changes**
  (shift / scale / glitch suppression, SPS, offset, reload). Selecting a result lists its function, source and parameters in the status bar.
  After pressing Apply on a Preprocess result, or extracting one with Extract Signals, the status bar keeps "…: added … derived signal(s) …" / "Extracted … signals …"
  (fixed in 0.9.11; before, the parameter description of the selected result replaced it at once — the list-selection event queued behind the action no longer
  overwrites the success message, as with Paste; clicking the result afterwards still lists its parameters). One ⌘Z / Ctrl+Z undoes the whole
  Apply; a source that already has a result with identical parameters is skipped; a result can be a source itself (bandpass, then envelope);
  removing only the source keeps the results that were not selected along with it and **turns them into independent signals** (current data kept, link to the source
  dropped; results chained on them keep following them; Ctrl+Z restores the links) — the same rule as for I/Q derived signals (user decision U8 of 2026-10-25, see
  "Deleting removes exactly the highlighted or named signals" under "Clicking a panel"; before the 0.9.9 merge they were removed together); deleting the whole panel
  (or selecting them too) removes them. **A result that could not be computed (0 samples, Fmt = error) is removed together with its source instead** (0.9.13 B4,
  see the same section: status bar note, named in the question, Ctrl+Z restores everything; before, it became a 0-sample independent signal).
  Copy and paste: see "Clicking a panel" — a result pasted on its own while its source exists keeps following the source.
  Clicking a panel whose only signal is a result shows the item-10 status line "Current panel: Pn; its 1 signal(s) are selected in the list …"; clicking it in the list
  or clicking its line lists the parameters. Results behave like any signal (rename, move, style, measure, spectrum, export). The selection stays on the sources.
- **Time information**: DSV signals are always uniformly sampled with time (fs = SPS × symbol rate, t = start + n/fs), so the panel is always MATLAB's "uniform signal with time"
  variant: filter frequencies in Hz (no ×π rad/sample), smooth / detrend units ps … years (no "samples"), no INTERPOLATION pane for Resample (nonuniform signals only), envelope units
  "samples" plus ps … years.
- **Filters** (Lowpass / Highpass / Bandpass / Bandstop; `dsv_filter`): Frequency Units (cycles/year … THz, default Hz; changing the unit only re-displays the value, which is stored in Hz),
  Passband Frequency (Lower / Upper Passband Frequency; empty by default for time signals, as in MATLAB), Steepness (spinner 0.5–0.9999, step 0.05, default 0.85; Bandpass / Bandstop
  take one "Steepness" or "Lower Band Steepness" + "Upper Band Steepness"), Stopband Attenuation(dB) (default 60, ≥ 10). Validation: "Passband frequency must be a positive scalar",
  "Lower passband frequency must be smaller than upper passband frequency", "Steepness must be a numeric scalar in the [0.5,1) range", "Stopband attenuation must be a numeric positive
  scalar greater than or equal to 10 dB". **FIR only** (user decision A4): where MATLAB's lowpass… would switch to a minimum-order IIR design for short signals, DSV does not process
  that signal and the dialog says how many samples it needs (`dsv_filter`'s SignalTooShortForFIR, with the signal length, FIR order and the minimum length). A passband beyond
  Nyquist uses an allpass / allstop filter with MATLAB's warning dialog. The computation (kaiserord, minimum even-order FIR, delay compensation) is compared value by value with
  MATLAB lowpass / highpass / bandpass / bandstop (`tests/matlab_ref/filters/`).
- **Smooth** (`dsv_clean.smooth` = MATLAB smoothdata): Smoothing Method Moving mean (default) / Moving median / Gaussian / Linear regression / Quadratic regression / Robust linear
  regression / Robust quadratic regression / Savitzky-Golay, Degree (Savitzky-Golay only: Auto or a positive integer); Window Type Duration (default; Duration Units ps … years,
  Window Duration Auto or a positive number) or Smoothing Factor (spinner 0–1, step 0.05, default 0.25). Validation: "Degree must be set to a numeric positive integer.",
  "Window duration length in time units must be a positive numeric scalar", "Smoothing factor must be a numeric scalar between 0 and 1"; MATLAB's "Degree is too large. …" error and
  "Degree has been adjusted to a smaller value. …" warning are reproduced.
- **Detrend** (`dsv_clean.detrend` = MATLAB detrend): Detrend Method Constant / Linear (default) / Piecewise Linear; Breakpoint Units and Piecewise Breakpoints (comma separated,
  parsed leniently, taking the leading number: "40abc" = 40; times map to the nearest sample; an empty part = no breakpoints = linear) appear for Piecewise Linear only. Validation: "Piecewise breakpoints
  in time units must be a numeric value". Restore Defaults resets only the method and units and keeps the breakpoints (MATLAB's behaviour).
- **Resample** (`dsv_convert.app_resample` = MATLAB resample as Signal Analyzer calls it): Resampling Method Sample Rate (default; Frequency Units + Sample Rate, Auto allowed) or Sample
  Factor (new rate = factor × current rate, non-integer allowed). Validation "Value must be a positive scalar"; a ratio above 10000 → "The ratio of desired sample rate to current sample rate
  exceeds limits…", a one-sample result → "The desired sample rate results in a resampled signal of length one…"; Auto leaves uniform signals alone with MATLAB's warning
  ("Uniformly sampled signals are not preprocessed when sample rate is auto computed."). **The result's SPS = source SPS × new rate / old rate** (symbol rate unchanged) and it starts
  where the source starts (MATLAB's ty(1) = tx(1)); changing the source's SPS later keeps the target rate and recomputes the result's SPS.
- **Envelope** (`dsv_convert.app_envelope` = MATLAB envelope): Envelope Upper (default) / Lower; Method Hilbert (default) / FIR (Filter Order) / RMS (Length Units + Window Length) /
  Peak (Separation Units + Maxima Separation); units samples (default) or ps … years (time → N = round(seconds × fs); switching between samples and a time unit clears the value, as in
  MATLAB). Validation: "Filter order must be a positive integer", "Window length in samples must be a positive integer", "Window length in time units must be a positive numeric scalar",
  "Maxima separation in samples must be a positive integer", "Maxima separation in time units must be a positive numeric scalar".
- **Signals with NaN / Inf** are not processed: the panel shows MATLAB's message "Unable to preprocess signals with missing or nonfinite values. Use Fill Missing to
  fill missing values." as soon as such a signal is selected, and Apply lists them in the error dialog. Error and warning dialogs follow MATLAB: "Selected signals have not been processed
  due to the following errors:" (all failed) or "Some selected signals have not been processed…", "Selected signals have been processed with the following warnings:", one "- name: message" per line.
- DSV's own decisions (no MATLAB counterpart or not determinable; the research report's recommendation was followed): results are derived signals instead of overwriting (above);
  the Window Duration validation uses the time-unit message (the research found that MATLAB shows the samples message even in time mode, which looks like a MATLAB bug); the Peak message follows its own
  unit field (the research found that MATLAB looks at the Window Length unit there); cycles/year = 365 days (dsv_convert), the smooth / detrend "years" = 365.2425 days (dsv_clean), the envelope "years" = 365 days
  (dsv_convert), each as the research recorded; only the ForcedAllpassDesign / ForcedAllstopDesign filter warnings, the smooth degree-adjusted warning and Resample Auto on a uniform signal raise
  a warning dialog (MATLAB raises no others); there is no "Overwrite signals?" confirmation, since nothing is overwritten; placeholders only on the fields the research recorded
  ("Enter Value" for Passband Frequency / Stopband Attenuation / Sample Factor, "Specify comma-separated values" for Piecewise Breakpoints; Bandpass / Bandstop's Lower / Upper Passband
  Frequency are the same kind of text field and follow Passband Frequency; the envelope's Filter Order / Window Length / Maxima Separation were not recorded and show none); the envelope
  method is MATLAB's "Peak" in English (the plain Chinese key used by the measurement tab's PEAKS section translates as "Peaks"; the two are separate catalog keys); tooltips: fields whose
  tooltip the research recorded use MATLAB's text (Stopband Attenuation(dB)'s tooltip is its label; the filters' Frequency Units says "Passband frequency units"), the rest (Resample's
  Frequency Units / Resampling Method, Smooth's Duration Units, Bandpass / Bandstop's Lower / Upper Passband Frequency) fall back to the label, nothing is invented; the Help button's tooltip
  "Preprocess Signal Help" is DSV's own; the CLEAN section lists Smooth before Detrend (the wording of the user decision; MATLAB's gallery has Detrend first); parameters read back from a
  settings file are re-validated with the panel's rules, so a hand-edited file shows MATLAB's field message in the status bar (e.g. a missing passband frequency → "Invalid parameters: Passband
  frequency must be a positive scalar") instead of a Python exception; stored numeric fields must be numbers and Degree / N integers (a hand-edited 2.5 or a string gets the same field's MATLAB
  message, not the module's own text); a result whose source has no data (a result chained after one that could not be computed, e.g. the envelope of lowpass(too-short signal), or an empty
  signal) is not a silent empty row: Fmt shows error and the status bar says "Source X has no data: reason" (no MATLAB counterpart: MATLAB overwrites signals and has no chaining), and selecting
  a result that could not be computed appends the reason to its status-bar line; a computation module's own error is listed verbatim in the error dialog (e.g. envelope's "N must be positive"
  when a time length rounds to 0 samples, or a Savitzky-Golay degree so large that it hits `dsv_clean`'s work limit), as the research has no MATLAB dialog text for those cases.
- The computation modules `dsv_filter` / `dsv_clean` / `dsv_convert` are compared value by value with MATLAB R2025a (`tests/matlab_ref/filters/`, `smooth_detrend/`, `resample_envelope/`);
  `python signal_viewer.py --selftest` (`_selftest_batch4`) runs those comparisons plus the panel defaults / show-hide rules / 18 validation messages, unit conversion, parameter ↔ panel
  round trips, derived-signal settings round trip, recompute on source change, the resample timebase, chaining, cyclic sources, the too-short / NaN / Nyquist messages and the English UI;
  the GUI test `tests_gui_mac.py` step `s31_batch4_preprocess` goes from the toolstrip button to the plotted line and compares it bit for bit with the module output;
  the interplay with the 0.9.9 features (results becoming independent signals on delete, a read-only frozen folder cancelling it, paste relinking, a followed
  selection, the spectrum and analysis windows, restoring chained results from the autosave with the "not restored" notice) is in `s37m_merge_pp_frozen_follow`
  and `s37n_merge_restore_chain`.

## Data Cursors and Data Tips (after MATLAB Time Scope / Signal Analyzer Data Cursors and figure Data Tips)
- **Data cursors** (Measurements → Data Cursors → **Data Cursors ▾**; the drop-down at the top of the "Cursor Measurements" panel; right-click on the plot → Data Cursors):
  **None / One / Two** vertical cursors labelled **1** and **2**, spanning all panels. Turned on, they go to the center of the current view
  (two = center ±1/4 of the view width) and the **Cursor Measurements** panel opens (right column; View → Layout toggles it too).
  - **Drag**: within a few pixels of a cursor line the pointer becomes ↔ and pressing grabs the cursor right away (no 10 px threshold); in that zone the
    cursor wins over pinning a data tip, drag-panning and hover tips (like MATLAB). Cursors stay inside the visible range; Esc cancels a drag.
    **The same holds while the toolbar's Zoom / Pan mode is on**: pressing within 4 px of a cursor line drags or selects the cursor, with no zoom box, no pan
    and no view reset on double-click (further away the mode zooms / pans as usual). Double-clicking a cursor does not restore the view.
  - **Horizontal cursors** (MATLAB Time Scope Screen Cursors → Horizontal; the "Horizontal Cursors" check in the Data Cursors menu, the Cursor Measurements
    panel and Measurements → Data Cursors; can be on together with the vertical cursors): **two horizontal lines per panel** (labelled 1, 2 at the right edge; panels have
    different y units, so each gets its own pair), placed at the center ±1/4 of each panel's y view when turned on. Dragging (the pointer becomes ↕ within 4 px)
    and Lock cursor spacing work the same; they do not snap (screen cursors). The Cursor Measurements panel gets a row **P*n* y** per panel: y1, y2, Δy
    (left-axis units); a panel with a right axis also gets **P*n* y right axis** (the same screen height in right-axis units); with **Normalize Y** or a
    **stack offset** the axis numbers are not signal units, so each signal of that panel gets a row **name (y)** = (y − stack offset) / normalize gain
    (raw signal units; buses skipped). Collapsed panels get none.
  - **Keyboard nudging**: click a cursor (or drag it) to select it (the line gets thicker); **← →** move a selected vertical cursor by one sample with Snap on
    (the Snap target signal) or 1 pixel with it off; horizontal cursors use **↑ ↓** (1 pixel); **Shift** is 10×. Esc, clicking empty space, or selecting a
    data tip / annotation deselects it (selections are exclusive). Arrow-key priority: whatever is being dragged → the selected cursor's own direction
    (it beats zoom mode's ↑↓ zoom and pan mode's arrow panning) → the selected data tip (next / previous sample) → pan 5 px. Keys that are not the
    cursor's direction (e.g. ↑ with a vertical cursor selected) keep their usual behavior.
  - **Cursor moves are not undoable** (MATLAB's cursors are not either): dragging, nudging, turning them on/off and Cursors into View never appear in the
    undo list; the settings still remember the positions.
  - **Snap to data**: cursors snap to the nearest sample (of the selected signal; the first shown signal when none is selected); turning it on snaps the current cursors too.
  - **Lock cursor spacing**: dragging one cursor moves both, Δx stays the same.
  - **Cursors into View**: brings cursors that left the screen back to the center (turns on two cursors when they are off); horizontal cursors go back into each panel's y view.
  - **Cursor Measurements panel**: x1, x2, Δx (x-axis unit), 1/Δx (Hz: Δx converted to seconds with the symbol rate), and each shown signal's value at
    cursor 1 and 2 with Δy (sample-and-hold like the crosshair; — when the cursor is outside the signal). Updates live while dragging;
    "Copy" or ⌘C / Ctrl+C puts it on the clipboard as TSV.
  - The **Measurements panel range** can be **Between cursors**: statistics and pulse measurements between the two cursors, recomputed as you drag
    (falls back to the current x view, with a note, when the cursors are off or there is only one).
  - Mode, positions, Snap, Lock, the horizontal-cursor switch and each panel's y1, y2 are saved in the settings (`view.dcursor_mode`, `view.dcursor_x`,
    `view.dcursor_snap`, `view.dcursor_lock`, `view.dcursor_h`, `view.dcursor_y` = `"1:y1,y2;2:y1,y2"`) and survive
    replots. Data cursors are included in "Copy figure" / "Save figure" (the crosshair is not).
- **Data tips** (MATLAB Data Tips):
  - **Export Data Tips…** (Measurements → Data Tips → Export Tips…; right-click a tip): writes every tip's #, signal, panel, sample index (1-based, like MATLAB),
    x (display unit) and y (true sample value) to TXT (tab separated) or CSV. Right-clicking a tip also offers **Copy Data Tips (TSV)** for pasting into Excel.
  - **Δ between tips**: with two or more tips, pinning, clicking or arrow-key moving a tip shows "Data tip #b − #a: Δx, Δy" in the status bar
    (the selected tip and the previous one; the next one when it is the first).
  - **Tip Content…** (Measurements → Data Tips; right-click a tip): choose the rows a tip shows — name, X, Y, sample index (Index), panel; applied to existing and new tips
    (hover tips too) and saved in the settings (`view.tip_fields`). The default (name / X / Y) is the original MATLAB look.
  - Figure windows (plotkit FigureWindow) have the same three items: View menu, the FIGURE toolstrip "View" section and the tip right-click menu;
    the tip content is saved in the figure file (JSON `tip_fields`) and can be undone.

## Despike Test Data and Decision Rule
- `samples/glitch/` (generated by `tools/make_glitch_samples.py`): `adc_sine_glitch.txt` (a 10-bit sine with 1-, 2- and 3-sample glitches to 0 or 1023; positions in the
  file header and README.txt), `adc_sine_clean.txt` (the same sine without glitches — put both in one panel and tick "mark differences"), `bus_dump_glitch.txt`
  (a 16-bit HEX bus dump, value held 8 samples, with single / 2-sample bad values). Add → Signal → Despike on → tick "mark fixed points": fixed points are marked
  with a red × and the status bar shows the count.
- Rule: for every candidate run of 1..k samples, a straight line is drawn between the samples just outside the run; the run is a glitch only if every sample deviates
  from that line by more than the threshold (max(minimum deviation, threshold × σ), σ from the median single-sample deviation), **and the deviation is larger than the
  step between the two end points** — so the edges of bus / digital value changes are never treated as glitches, and a glitch longer than k is left alone as a whole
  (never "half fixed" toward the bad value); raise k to fix it. `--selftest` checks this on the same synthetic data: k=2 fixes the 1- and 2-sample glitches with no false
  positives and leaves the 3-sample one, k=3 fixes all, the bus dump only loses its bad values.

## Plot Type, AM/PM/FM Analysis (after MATLAB Time Scope PlotType and PlotAsMagnitudePhase)
- **Plot type** (Signals → Style → **Plot Type ▾**; right-click in the list or on the plot → Plot Type; Signal Properties → Signal Parameters → Plot type), per signal:
  - **Line**: samples joined by straight lines;
  - **Stairs (default)**: each sample held until the next one (the original and formerly only drawing);
  - **Stem**: one stem per sample from 0 (including the stack offset) to the value, with a hollow circle head (the signal's own marker if one is set).
    The whole signal is a single Line2D ("baseline → value → baseline"), about 0.3 s for 1e6 points; heads are omitted above 50,000 points and
    signals over 1,000,000 points are drawn as lines (the status bar says so).
  Stored per signal (settings `signals[].ptype`; older settings files = stairs) and undoable; markers, line style / width, right axis, hiding, Normalize Y, stack offset,
  crosshair and data cursors all work as before; data tips and hover snap to the samples (the stem heads). Copying to a figure window turns line into a line and stem into its heads (samples + marker).
- **AM/PM/FM Analysis…** (Analyze → Analysis Windows; list right-click. Since 2026-10-24 the former "AM/PM Analysis…" and "FM Analysis…" buttons and windows are
  **one window** in which you tick AM / PM / FM; the action id is `analysis.ampm`, and a shortcut bound to `analysis.fm` (FM Analysis…) in an old settings file is applied to it):
  like Spectrum and GFSK it **opens a separate window** and leaves the main plot alone.
  **Which pair** (user-reported item 9, 2026-10-25; the same for Constellation and GFSK): the I and Q of the **current panel** (click it on the plot; it gets a frame;
  names like adc i / adc q pair automatically); if exactly **two signals (I and Q) are selected in the list**, those two; **a panel's right-click → AM/PM/FM Analysis (P1)…**
  analyzes that panel directly. The window title reads "AM/PM/FM Analysis — P1: I = …, Q = …" and so does the status bar; if the current panel has no I/Q, no empty
  window opens and the status bar lists the signals that panel has. The list right-click items name their target too (e.g. "AM/PM/FM Analysis (P1)…").
  For each I/Q pair they compute:
  - **AM** = magnitude `|I + j·Q|`; **PM** = phase `∠(I + j·Q)` (degrees, −180..180; tick "Unwrap Phase" for a continuous angle);
  - **FM** = instantaneous frequency (Hz) = phase difference between neighbouring samples × fs / 2π, fs = SPS × symbol rate (the symbol rate of the panel that holds the I/Q pair).
    **No mixing, no filtering** (use "GFSK…" for IF down-conversion + Gaussian filtering); the first sample has no predecessor and is empty (NaN).
  - AM / PM / FM can be ticked in any combination (all three the first time; the ticks are saved as `iq.kinds` and reused next time), one subplot each; the **x axis is seconds**
    from the start of the analysis range (= the main plot's current x range, as in the GFSK window; press "Recompute" after zooming the main plot);
    "I/Q order" QI flips the sign of PM / FM. Interaction is the same as the other analysis windows (wheel zoom, drag pan, data tips, right-click, save).
    The ticks, unwrap and order are saved in the settings file under `iq`.
  - **Copy / paste / drag** (following MATLAB's line right-click Copy and axes right-click Paste): in the window **right-click a line → Copy** (that one) or the
    "Copy Signals" button / ⌘C (all); in the main plot **right-click a panel → Paste to Pn** (below Undo / Redo) or press ⌘V (Ctrl+V); ⌘V inside the window also
    pastes into the main plot's current panel and, when something was pasted, brings the main window to the front (true since round 10: it never did before;
    when the paste is cancelled the main window is also brought to the front before the error dialog, which belongs to the main window, so it can be seen);
    or **drag a line straight onto the main plot** (press on the line, drag out of
    the window: release on a panel = paste into it (status bar "Release to add to Pn", that panel gets a frame), release on the blank area below the last panel = new panel
    ("Release to create Pn", dashed frame); releasing elsewhere cancels — the same target rules as dropping files or dragging from the Folder panel).
    **The settings of the panel you drop on do not change** (fixed in 0.9.11; in 0.9.8–0.9.10 dropping on a panel that was not the current one replaced its Symbol rate,
    x / y units and Link Time with the current panel's, and dropping below the last panel changed the top panel): every existing panel keeps its Link Time, x / y units and
    Symbol rate (item 8, "every panel has its own settings"); a panel created by the drop follows the same rule as one created by dragging from the list, the Folder panel or
    the Finder below the last panel — Link Time on, x unit and Symbol rate taken from the panel that was current before the drop, y unit blank; after the paste the panel
    you dropped on becomes the current one. The pasted signals are the derived kinds `|I + j·Q|`,
    `∠(I + j·Q) [deg]`, `FM(I + j·Q) [Hz]`; after pasting the canvas scrolls to that panel (a new panel is at the bottom). Removing a source (any way) keeps derived
    signals that were not selected along with it: they become independent signals with their current data (see "Clicking a panel"); Ctrl+Z restores the links;
    if the frozen folder cannot be written, nothing is deleted and an error dialog explains why.
    **Copying (and dragging a line onto the main plot) carries the whole data** (2026-10-26, decision U16): the values computed from the current I/Q sources over
    the whole signal (identical to the derived signal pasted while the sources exist — not just the window's analysis range). When the I/Q sources are deleted
    before pasting (⌘V, right-click Paste, dragging a line), the pasted signal becomes an independent signal with this data, with the same rules as in the main
    window: the data is first saved in the frozen folder and read back, and if it cannot be saved the whole paste is cancelled, the clipboard is unchanged and an
    error dialog explains why (see "If the frozen folder cannot be written, nothing is pasted" under "Clicking a panel"). Before, no data was carried and pasting
    after the sources were deleted gave an empty 0-sample signal.
    **After the sources' panel is deleted, FM keeps using that panel's own Symbol rate** (2026-10-26, round 11): the window's plot, "Recompute", copying and
    dragging all agree with the derived signal pasted while the sources existed (before, deleting the panel also dropped its Symbol rate and the toolbar field of
    the current panel was used instead, so with different Symbol rates per panel FM was off by a factor, without any notice).
    ⌘V and right-click Paste do not check for duplicates, as in MATLAB: a pair already in that panel is pasted again (keys with #2…; item 13, 2026-10-26);
    dragging a line onto the main plot does not add a pair that is already in that panel (the status bar says so). ⌘V in a figure window overlays (snapshots).
  - **Unwrap Phase** (right-click a phase signal): pasted phase signals in the main plot can be switched between unwrapped and wrapped (`view.iq_unwrap`).
  - Settings file: `signals[].derive` (iq_mag / iq_phase / iq_phase_unwrap / iq_fm) and `signals[].src` (the I and Q uids); derived signals whose sources were not
    restored are skipped with a note.
  - Offset-binary ADC data should be shifted first (e.g. −512); otherwise magnitude / phase are computed around (512, 512).
  - **The time base follows the source I**: changing I's SPS or offset afterwards (any way: signal parameters, nudge, slider, editing the fields) changes the
    SPS / offset of magnitude / phase along with it, so the x axis always lines up with I (the plot type does not follow; it is set per signal); it is undone by the
    same Ctrl+Z as I's change, and the settings file stores the values that follow I. When Q's SPS or start differs from I's, the status bar says
    "I/Q time base mismatch: the SPS/offset of Q differs from I (magnitude/phase use the time base of I, paired by sample index)".
## Constellation Diagram (after MATLAB Constellation Diagram / scatterplot)
Click a panel that has I and Q (or select I and Q in the list) and press **Analyze → Constellation…** (also in the list right-click menu and as "Constellation (P1)…"
in a panel's right-click menu; the target rule is the same as for AM/PM/FM). I is plotted against Q, one point every **Samples per symbol** samples:
- **Samples per symbol**: default = the SPS of the I signal; 1 = every sample (scatterplot); may be fractional (rounded to the nearest sample).
- **Offset**: sample position of the first symbol point (MATLAB SampleOffset); points are taken at round(offset + k·SPS).
- **Symbols**: All (up to 100,000 points), **Last N** (MATLAB SymbolsToDisplay, default 256) or **First N**; N is the box next to it and is greyed for All (unused).
  "Recompute" redraws from the main plot's **current** x range and the symbol count in the title follows (before 2026-10-24 changing N under "All" and pressing Recompute showed no change, because N was simply not used).
- **Current x range only** (ticked by default): only samples inside the main plot's current x range; unticked = the whole record.
- **Equal axes** (default on), **Grid** (with the I = 0, Q = 0 axes), **Remove DC** (subtract the mean of I and Q over the range, default off).
- **Reference**: BPSK / QPSK / 8-PSK / 16-QAM, scaled to the measured RMS; the status bar shows the RMS EVM (against the nearest reference point).
- **Timing/phase correction** (off by default = the Offset above and no rotation, the EVM is exactly as before): when ticked and a reference is chosen,
  a simple synchronization runs before the EVM — symbol timing tries every sampling phase 0 ≤ offset < SPS (at most 64) and keeps the lowest EVM; carrier phase
  is a least-squares rotation onto the reference (coarse 5° scan, then decision-directed refinement). The corrected points are plotted and the status bar says
  "timing/phase corrected (offset …, phase …°)". Only a fixed timing and phase are corrected, not a frequency offset (a rotating constellation still shows a large EVM).
- Data tips can be pinned on every point; wheel zoom, drag to pan and the right-click menu are the same as in the Spectrum window. Settings are saved under `constellation`.

## Eye Diagram (after MATLAB Communications Toolbox eyediagram)
**Analyze → Eye Diagram…** (also "Eye Diagram (N selected)…" in the list right-click menu and "Eye Diagram (P1)…" in a panel's right-click menu; shortcut action
`analysis.eye`, assign a key under Preferences → Keyboard). Works like MATLAB's `eyediagram(x, n, period, offset)`: the signal is cut into traces of n samples
that are all overlaid to show how open the eye is (batch 4 T4, 2026-10-26). **Plot only, no eye height / width measurement** (the user's 2026-10-24 decision;
MATLAB R2025a has no callable eye measurement function either).
- **Which signals** (the same rule as AM/PM/FM, Constellation and GFSK, item 9): the signals selected in the list; with no selection the visible signals of the
  **current panel** (click it on the plot; it gets a frame); when the list selection is the one that followed a panel click (item 10) it is that panel
  (the title says "P1", not "list selection"); a panel's right-click plots that panel. The window title says which panel and which signals are plotted
  (e.g. "Eye Diagram — P1: I = …, Q = …", "Eye Diagram — list selection (P2): …"), and so does the status bar.
  - **1 signal = one "Eye Diagram"** (real input).
  - **2 signals = treated as I/Q**: "Eye Diagram for In-Phase Signal" on top, "Eye Diagram for Quadrature Signal" below (MATLAB's complex input; MATLAB plots a
    two-column real matrix the same way). When the names show which is I and which is Q (adc i / adc q, i / q…, the same pairing as AM/PM/FM) I goes on top,
    otherwise the list order is used. If the two have different SPS they are aligned by sample index (the message line says so); different lengths use the shorter.
  - **3 or more**: MATLAB's x has at most two columns (three columns raise "Number of columns in the input data, X, cannot exceed 2."), so no window opens and the
    status bar shows that error and what to select; when the current panel has 3 or more signals, an I/Q pair in it is plotted as the pair.
- **Parameters** (units as in MATLAB):
  - **Samples per trace** (MATLAB's n, an integer > 1): default **2 × samples per symbol (SPS)** = two symbols per trace (MATLAB's n has no default — eyediagram needs at least two arguments; the examples shipped with R2025a that call eyediagram all use
    2*sps, e.g. OQPSKModulator's `eyediagram(waveform, 2*sps)`); empty or unchanged = automatic, following the signal's current SPS (press Recompute after changing the SPS); a value
    equal to 2 × SPS is saved as automatic.
  - **Period** (MATLAB's period, a positive number, default 1): the length of one trace on the time axis, x from −period/2 to period/2; **for odd n, as measured,
    −(n+1)/(2n)·period to (n−1)/(2n)·period** (the documentation says ±period/2, the measured line data does not). To use symbols as the unit enter n ÷ SPS (2 when
    n = 2 × SPS), for seconds enter n ÷ fs.
  - **Offset** (MATLAB's offset, in samples, an integer 0 ≤ offset < n, default 0): sample number offset (counting from 0) falls at t = 0 and a new trace starts every
    n samples; the arrows step by 1, clamped to 0 … n − 1.
  - The number fields follow the same rule as the Spectrum window (SI prefixes such as 2k, 500m, 2u are accepted; the whole entry must be a number, 12abc is an
    error). An invalid field also works like the Spectrum window: what you typed stays, the field gets a red frame, its tooltip becomes MATLAB's error message
    (e.g. "N must be an integer greater than 1."), and the message line and status bar show it too; **the plot and the settings file keep the last valid values**
    (if the last valid offset is not valid for the new n either, n also keeps its last value — in MATLAB the whole call fails and the figure does not change), and the
    message line says which values are plotted.
  - **Current x range only** (ticked by default): only the samples inside the main plot's current x range (the range of the signal's panel); unticked = the whole data.
    Press Recompute after zooming the main plot or changing SPS or shift. When the range holds no samples the message line shows MATLAB's "Input variable X is
    empty." and how to adjust the range.
- **The plotted lines and limits follow MATLAB** (`dsv_eye`; compared point by point with the MATLAB R2025a reference data in tests/matlab_ref/eye_diagram, which the
  GUI test s38 also uses as expected values): every complete trace has n+1 points and reaches both edges (the right-edge sample is drawn again at the start of the
  next trace), traces are separated by breaks; the x range = the actual minimum to maximum time of the data;
  **y range = [min(−1.05·max|x|, auto lower), max(1.05·max|x|, auto upper)]**, where the auto range is MATLAB's tick-aligned rule (ticks of 1, 2, 5 × 10^k).
  The two plots have the same x / y limits (MATLAB uses one set of limits) and zoom independently (MATLAB's two subplots are not linked).
- **Look**: follows DSV's current theme and plot style (the user's 2026-10-24 decision, not MATLAB's hard-coded black background with yellow lines; grid and
  colors as in the other analysis windows); titles "Eye Diagram" / "Eye Diagram for In-Phase Signal" / "Eye Diagram for Quadrature Signal", x label "Time",
  y label "Amplitude" (eyediagram's own English); tick positions follow DSV's (matplotlib's) rule.
  **Line style uses DSV's style menu** (instead of MATLAB's plotstring): Color, Line Width, Line Style, Marker, Marker Size and Reset Style at the top of the
  plot's right-click menu change both plots together, are saved in the settings file and are used the next time; e.g. MATLAB's `'r.'` = color #ff0000 + line style
  none + marker "Point .". Auto = the same first color as the other analysis windows, with line width / marker size from the plot style (MATLAB style 0.5 / 6 pt,
  MATLAB's defaults).
- Data tips, wheel zoom, drag to pan, Home, Ctrl+Z / Ctrl+Y for keyboard zoom and pan, and the right-click Copy Figure to Clipboard / Export This Panel Only… work
  as in the other analysis windows.
- **Large data**: the line itself keeps the complete data (data tips and export use it); when drawing, segments whose ends fall on the same pixel are drawn only a few
  times (with tens of thousands of overlaid traces Agg scans each one: drawing 1e6 samples with n = 16 in full takes about 16 s, and 4e6 samples raise an error).
  Measured: about 0.6–4 s for 1e6 samples and about 6 s for 4e6; for a 20,000-sample eye the image differs from a full drawing in < 0.2% of the pixels
  (difference > 96/255).
- Differences from MATLAB (the full list is in `dsv_eye.py`): integer inputs (int16) are converted to double; with ±Inf in the data the y range uses the finite values
  only; a single sample, or a period so small that every time value underflows, gives DSV's own error message (MATLAB fails elsewhere); n is limited to 2^53.
- Settings are saved under `eye`: `n` ("" = automatic), `period`, `offset`, `xrange`, `color` / `lw` / `ls` / `marker` / `ms` (null or "" = automatic).

## Error Rate (after MATLAB Communications Toolbox biterr / symerr / comm.ErrorRate)
**Signals → Compare → Error Rate…** (also "Error Rate (N selected)…" in the list right-click menu and "Error Rate (P1)…" in a panel's right-click menu; shortcut action
`analysis.errrate`, assignable in Preferences → Keyboard). Two digital signals, TX (transmitted, the reference) and RX (received), are compared with one value per
symbol, giving MATLAB's number of bit errors / bit error rate (`biterr`), number of symbol errors / symbol error rate (`symerr`) and the number of samples compared;
delays and selected samples work as in `comm.ErrorRate` (batch 4 T5, 2026-10-26; all computation uses `dsv_errrate`, checked against MATLAB R2025a).
There is one Error Rate window for the whole program: pressing the button again switches it to the new TX / RX and brings it to the front.
- **TX, RX**: two drop-downs at the top of the window list every signal in the list ("#row P1: name"; signals in analog format are marked "(analog)") and can be set
  to any of them (the user's decision, 2026-10-26). The defaults when the window opens follow the rule of item 9: the signals selected in the list, or with no
  selection the visible signals of the **current panel** (click it on the plot; it gets a frame), the panel the list selection followed (item 10), or the panel
  whose right-click menu was used; **the upper one in
  the list is TX and the next one is RX** (regardless of the order of selection — clicking a panel selects the whole panel at once); with only one signal RX = the
  signal after it in the list. The window title shows the pair ("Error Rate — TX = … (P1), RX = … (P2)"). With fewer than two signals in the list the window
  does not open and the status bar explains why.
- **Sampling: one value at the middle of each symbol** (the user's decision, 2026-10-24): for every cell k..k+1 of the x axis (in symbols) the value at the middle
  k + 0.5 is taken, sample index = floor((k + 0.5 − start) × SPS) — the same value the crosshair and the difference comparison read. Each signal uses its own SPS;
  the Offset lines the symbols up with the cells (for example, if the RX waveform lags by 3 samples, set its Offset to −3 sample and the middle falls on the center
  of every symbol). Only cells whose middle lies within the data are used; a signal can have at most 10,000,000 symbols.
- **Digital-format signals only** (the user's decision, 2026-10-24): 0/1 or bus values are compared directly (no level slicing first). When TX or RX is in
  analog format the window explains and computes nothing; **Make Digital** switches it (the same as right-click Display Format → Digital in the list or on the plot;
  Ctrl+Z in the main window undoes it; signals with values other than 0/1 are drawn as a bus on the main plot).
- **Parameters** (as in `comm.ErrorRate`, all in symbols):
  - **Receive delay** (ReceiveDelay, a nonnegative integer, default 0): RX at position k is compared with TX at position k − receive delay. Instead of a delay you
    can also move RX into line with TX with its Offset — the result is the same.
  - **Computation delay** (ComputationDelay, a nonnegative integer, default 0): this many of the first symbols that line up are not compared. When TX and RX start in
    the same cell and have the same length this is MATLAB's "the first receive delay + computation delay samples are not compared".
  - **Samples to consider** (Samples): Entire frame (default) = compare every symbol that lines up; Custom = only the ones listed in Selected samples from frame.
  - **Selected samples from frame** (CustomSamples): which RX symbols to compare (counting from 1; 0 is skipped, duplicates count once), written as `1 3 5`,
    `[1:100 200]` or `1:2:99` (MATLAB's colon operator); grayed and not checked with Entire frame. **Empty is an error when Custom is selected** (what MATLAB R2025a
    actually does; the documentation says it compares everything); a position beyond RX's number of symbols is an error too (MATLAB's "The elements of the Samples
    property must be smaller than or equal to the input length."), and then there is no result; that list does not count as valid, so a later mistyped field
    falls back to the earlier valid one (fixed 2026-10-28).
  - The order of checks, the identifiers and the messages follow MATLAB (the English interface shows MATLAB's own text, e.g. "Expected ReceiveDelay to be
    nonnegative.", "Expected CustomSamples to be a vector."): negative, non-integer, empty (= MATLAB's []), vector and unreadable text (= MATLAB receiving a char)
    are errors. Numbers can use SI prefixes (1k = 1000). A mistyped field works as in the Spectrum and Eye Diagram windows: the text stays, the field gets a red
    frame, its tooltip becomes the error message, the message line and the status bar say it too, and **the results keep the last valid value** (the message line
    says which values were used). The arrows of the delay fields step by 1.
- **Results**: the number of samples compared; the number of symbol errors / symbol error rate (`symerr`: any differing value is one error, NaN counts as an error,
  and with Inf / NaN the message line shows MATLAB's warning); the number of bit errors / bit error rate (`biterr`: each symbol is expanded to k bits compared bit
  by bit, **k automatic = the bits needed by the larger maximum of both**, MATLAB's default); bits per symbol k and the number of bits compared. biterr takes
  nonnegative integers only (MATLAB's rule): with negative, fractional or NaN values the two bit cells show "—" and the message line gives MATLAB's error
  (X = TX, Y = RX), while the symbol results are still shown. Below the results the window shows how many symbols TX and RX have, where they are, and which RX
  symbols were compared; when no symbols line up it says why.
- **Red segments on the main plot** (the user's decision, 2026-10-24, drawn like Highlight Differences: translucent red over the full panel height): the RX symbols
  in error; when TX is in another panel, that panel marks the TX symbols they were compared with (shifted back by the receive delay). Adjacent cells merge into one
  segment, and too many segments merge by the difference-comparison rule. **Previous Error / Next Error** in the window jump between the segments of the RX panel
  and zoom in (the same rules as Previous / Next Difference). The red segments do not depend on the Highlight Differences toggle; they are included when the figure
  is saved, and disappear when the window closes.
- **Recomputed automatically when the main plot's signals change** (Offset, SPS, data, display format, a signal removed or restored); Recompute forces it.
- Differences from MATLAB: MATLAB's functions take symbol sequences, DSV takes waveforms (one value at the middle of each symbol); comm.ErrorRate accumulates frame by
  frame, DSV compares everything at once; when TX and RX start at different places or have different lengths only the symbols both have are compared (MATLAB needs
  equal lengths) and the computation delay counts from the first symbol that lines up; there is no Input port (SEL) and no ResetInputPort; signals are always
  double (MATLAB's special rules for logical, integer types and single do not apply).
- Settings are saved under `errrate`: `rd`, `cd`, `samples` (`Entire frame` / `Custom`), `custom` (the last valid text of each field).

## Spectrum (as in MATLAB Spectrum Analyzer)
Select signals and press "Spectrum…". The analysis range is the main plot's current x range (press Recompute after zooming or panning the main plot).
The toolstrip follows MATLAB R2025a's Spectrum Analyzer: the tabs **Scope / Estimation / Measurements**, plus the contextual tabs **Spectrum**,
**Spectrogram**, **Spectral Mask** and **Channel Measurements**, that appear only while that view is shown (Spectral Mask and Channel Measurements go with the
spectrum view; Spectral Mask also needs a type other than RMS and dB units). All settings are saved under `spectrum` in the settings file and reused next time; a view the settings file does not know (anything other than spectrum, spectrogram or both) falls back to the spectrum when the window opens, silently (round 9; both views used to be off: nothing drawn, every contextual tab hidden, while the status bar reported a computed spectrum).
- **Typing numbers** (every numeric field of the toolstrip, plus the color limits in Settings…; one rule for the whole spectrum window since 2026-10-25):
  SI prefixes are accepted — 4p, 3n, 20u (or 20µ), 500m = 0.5, 2k (or 2K) = 2000, 1.5M = 1.5e6, 1G = 1e9 (m is milli, M is mega; case matters in every
  field) — and are applied in decimal (1.023k is the integer 1023, the same as 1.023e3); a trailing Hz, sps or S/s unit is optional (2 kHz = 2000); Time
  Resolution and Time Span in seconds may also end in s or sec (1ms, 20us, 1 s, 1msec; the prefix still keeps its case: 1Ms is a million seconds and 20US
  is an error — these two fields used to read 1Ms, 1MS and 20US as milliseconds / microseconds). The number itself follows DSV's other fields (for example
  Symbol rate): 1,5 = 1.5 (decimal comma) and 1,000 = 1000 (thousands separator); no spaces inside a number or after its sign (1 000, 1e 3 and - 5 are
  errors), and hexadecimal / binary such as 0x10 and 0b101 are not accepted (the fields that used the plain number parser used to take them). Vectors and
  matrices (ACPR offsets, color limits, the upper / lower mask limits) are converted to half-width first (full-width brackets, semicolons and minus signs
  typed with a CJK input method work), commas, spaces and semicolons separate the numbers, and every number follows this rule. The whole text must be a
  number: an incomplete number or trailing text (12abc, 50abc, 1..2; a unit that is not the field's own, such as 5 dB or 70 dBm, see unit words below) is an error; a blank field keeps its earlier meaning (Auto fields = Auto,
  Reference Level = no change, Min Height = no limit, Threshold = 0; a blank is an error elsewhere). Inf / -Inf (any case, +Inf and Infinity too; no spaces
  inside the word or after the sign, so In f and - Inf are errors) are accepted only by the fields that already took infinities: the upper / lower mask
  limits and Reference Level, and the peak Threshold (+Inf) and Min Height, plus Min Distance, which takes Inf as in MATLAB (since 2026-10-26); the upper / lower mask limits also take NaN (that segment is not tested); Inf
  and NaN are errors in the other fields. The Spinbox arrows (Overlap, Occupied BW %, Num Pairs, coefficient; ▲▼ buttons, Up / Down keys and the mouse
  wheel) follow the same rule: they step from the field's value (0.098k ▲ 98.5, 250m ▲ 0.35), or from the last valid value when the field is invalid, clamp to the range, write the number the way MATLAB does (99.5 ▲ 99.99) and apply it like Enter (Tk's
  built-in arrows took the leading number and rounded to the step's digits: 0.098k ▲ became 0.6 and 99.5 ▲ the invalid 100).
  **dB-type fields accept their own unit word** (decided by the user on 2026-10-26): the number may be followed by that field's unit (with or without a
  space, any case, also after Inf); any other unit word is an error — Attenuation (dB) takes dB (70 dB; 70 dBm and 70 Hz are errors); Reference Level (dBr)
  and the mask levels (a scalar mask, the second column of a matrix) take dBr (5 dBr, -10 dBr, [0 -17 dBr; 500 -17dBr]; 5 dB or Hz on a level is an
  error); the peak Min Height and the color limits take the spectrum's current unit, i.e. the unit on the y-axis and colorbar labels: dB, dBFS,
  dBm (plus /Hz for power density, /(cycles/symbol) when the frequency is not in Hz; RMS in dB is dBV), W, W/Hz or Vrms for linear units, and none for the
  linear magnitude (the y-axis says amplitude). After the spectrum unit or type changes, a field still written with the old unit becomes invalid (for example
  Min Height -50 dB after switching to dBm). Threshold is the height difference between a peak and its neighbors: with a dB-type y-axis (dB, dBFS, dBm, dBV,
  /Hz for power density) a difference is in dB, so like the other dB-type fields it takes only its own unit word dB (3 dB; 3 dBm, 3 dBFS, 3 dBV and
  3 dBFS/Hz are errors — round 8; it used to take the y-axis level unit: 3 dBm with a dBm y-axis, 3 dB an error), and the y-axis unit for linear units
  (3 W; no unit for the linear magnitude).
  In vectors and matrices (color limits, upper / lower mask limits) every number may carry the unit, with or without a space (-80 dB, 20 dB or [-80dB 20dB]).
  The other fields are unchanged: a trailing Hz, sps or S/s is optional and dB is an error; the mask frequency column and Frequency Offset are not dB-type
  (dBr is an error there).
  **Every field shows errors the same way** (decided by the user on 2026-10-26; Channel Measurements, Distortion and Spectral Mask already did, while the
  batch-2 and peak fields used to reset to their defaults with a DSV sentence on the message line, and Reference Load / Full Scale silently fell back to
  1 / Auto): the typed text stays, the field gets a red frame (Reference Load and Full Scale exist on both the Spectrum and Spectrogram tabs; both turn red),
  the tooltip becomes MATLAB's message, the message line and status bar show it too (the status bar prefixes the section or feature: Bandwidth,
  Frequency Resolution, Window Options, Time Options, Scale, Configuration, Peaks, Channel Measurements, Distortion, Spectral Mask), and the computation,
  the peak search and the settings file use and keep the last valid value (or the default when the last valid text is no longer valid now — after a
  spectrum-unit or RBW change, for example); a valid input clears it. Every recomputation (pressing Enter in a toolstrip field recomputes) checks every
  field again, so an invalid field stays marked until it is fixed.
  The status bar follows the batch-3 rule as well (round 7, 2026-10-26): while any field is still invalid, the recomputation's "Computed …", the peak
  fields' "Peak Finder: applied" and the sentence restored when Channel Measurements is turned off do not hide the error — the status bar shows the
  error written last among the fields that are still wrong, and returns to that sentence only when all are fixed (with two invalid fields, fixing the
  batch-2 or peak one used to write "Computed …" while the other stayed red); pressing Enter again in an invalid field (even with the same text) or Apply
  again in the Settings dialog writes the error again; a new sentence written by a feature itself stays — the Channel Measurements result (turning it
  on, changing its type, filter shape, frequency span mode or channel, Enter in one of its fields) and the Spectral Mask's "counts cleared …" —
  while the error is still shown by the red frame, its tooltip and the message line (confirmed in round 9: the batch-3 rule since round 3, "a newer
  sentence from another feature is left alone"). When a peak field becomes valid outside a recomputation (valid
  text typed without Enter, then used when zooming re-finds the peaks), the message line drops its message and the status bar returns to the sentence
  from before the error (round 9; the red frame used to go while the message line and status bar kept the old error until the next action); errors
  found outside a recomputation are written as before (round 7). A Time Span
  rejected for being shorter than twice the update time cannot be checked while no spectrogram is drawn (spectrogram turned off, or too large to compute),
  so it stays invalid and the last valid value is used and kept (turning the spectrogram off used to make it the "last valid" value and save it, losing
  the earlier one).
  **A disabled or hidden field that is still invalid** (decided by the user on 2026-10-26): the error state stays and the last valid value is still used and
  kept; the field keeps the theme's grey frame (the theme's disabled image comes before invalid, so no red frame; MATLAB also only toggles the
  enabled state), and the message line says which field it is and how to reach it — "Field: message (… to edit it)", for example "Window Length: Enter
  window length as a finite positive real scalar greater than 2. (switch to Window Length mode to edit it)"; switching back shows the red frame and the
  message line shows the message alone. The status bar still says "Section: message". The fields that can be disabled or hidden and what the message line
  says: RBW (window-length mode; switch to RBW mode), Window Length (RBW mode; switch to Window Length mode), Attenuation (windows other than Chebyshev and
  Kaiser; select the Chebyshev or Kaiser window), Time Resolution and Time Span on the Spectrogram tab (spectrogram off; turn on the Spectrogram view),
  Reference Load and Full Scale under Scale (one on the Spectrum tab and one on the Spectrogram tab, so hidden only with both views off — the toolstrip
  always keeps one on and a view the settings file does not know falls back to the spectrum, so only code that sets both view variables can cause
  it; turn on the Spectrum or Spectrogram view), the color limits (in the Settings… dialog, while it is closed; click
  Settings…); Channel Measurements — the whole tab is hidden with the spectrum view off (turn on the Spectrum view) — Occupied BW (%) (ACPR; set Type to
  Occupied BW), Num Pairs / Offsets / Adjacent BW (Occupied BW; set Type to ACPR), the coefficient (Roll-off Factor or BT Product, named after the filter
  shape; Occupied BW or Filter Shape None; set Type to ACPR, set Filter Shape to RRC or Gaussian), Span / Center Frequency and Start / Stop Frequency (the
  other frequency span mode; set Frequency Span to that mode — switching modes rewrites these fields with the settings, so they normally carry no error);
  Distortion's Num Harmonics (Type Intermodulation; set Type to Harmonic); the Spectral Mask's upper / lower limits, reference level and frequency offset
  (while the tab is hidden; turn on the Spectrum view, set the spectrum type to something other than RMS, set the spectrum unit to something other than
  Linear — whichever conditions are not met). When several are needed all are written ("turn on the Spectrum view and set Type to ACPR to edit it"); the
  Channel Measurements, Distortion and Spectral Mask fields are named with their feature ("Channel Measurements Num Pairs"). The four peak fields, the
  bandwidth Offset, FFT Length and Overlap are never disabled or hidden.
  Conditions of the batch-2 and peak fields (messages as MATLAB Spectrum Analyzer's toolstrip and Peak Finder fields show them): bandwidth
  Offset (a finite number); RBW (Auto or positive); Window Length (greater than 2; DSV also needs an
  integer; 2 used to be accepted); FFT Length (Auto or an integer ≥ 2; the message's {0} is 2 because DSV accepts an FFT shorter than the
  window and wraps the data); Attenuation (≥ 45); Overlap (0 to 100, excluding 100); Time Resolution
  (Auto or positive), and with a specified RBW also ≥ 1/RBW → an error ("…larger than or equal to {0}
  seconds", {0} = 1/RBW; it used to reset to Auto with a note); Time Span (Auto or positive), and while the spectrogram is drawn also at
  least twice the update time → an error ("…larger than {0} seconds", {0} = twice the update time; it used to show the whole
  range with a note) — with time in symbols these two say symbols (DSV's own sentences; MATLAB only has seconds); Reference Load
  (positive); Full Scale (Auto or positive); the color limits use the Settings dialog's check ("Enter [cmin cmax], where cmin and cmax are finite scalars.": two finite numbers, the first
  smaller; the dialog shows it too, and Cancel or closing the dialog drops the typed text and clears the error — the dialog reopens with the applied value,
  as MATLAB's Settings dialog does); Num Peaks (1 to 99; DSV also needs an integer); Threshold (≥ 0, +Inf allowed); Min
  Height (real, ±Inf allowed); Min Distance (a positive integer, and **Inf as in MATLAB = only the highest peak** —
  it used to be an error; NaN, ≤ 0 and finite fractions are errors). A peak field is saved to the settings as soon as Enter is pressed (it used to wait
  for the next recomputation and then saved the mistyped text). Invalid values in the settings file (from older versions or hand edits) are replaced by
  the defaults when the window opens, without a note (as for the batch-3 fields).
  Limits that only DSV has (with SI prefixes, values such as 10k or 1G are easy to type; MATLAB has no limit; kept by the user's decision on 2026-10-26):
  an attenuation too large for the selected window to be computed (about 6139 dB for Chebyshev and 6450 dB for Kaiser, beyond double precision; what
  MATLAB does there was not measured) is an error ("Attenuation … dB is too large to compute the window"; a borderline value that only fails for a longer
  window is reported after that signal's name) — only the selected window counts (round 5's rule, the limit the user decided to keep; round 6 checked both
  Chebyshev and Kaiser and rejected 6140–6449 dB for Kaiser, which can compute it): switching windows checks again, so a last valid value the new window
  cannot compute becomes invalid and the default 60 is used, and switching back restores it; windows without attenuation (Hann etc., field disabled) only
  need ≥ 45; FFT Length is at most 2^24 (16777216) points ("FFT length can be at most 2^24 (16777216) points"); the frequency Offset is at most ±1e300
  (round 7; beyond that matplotlib cannot compute the frequency-axis ticks — measured: drawing raised an exception from about 9e307 on a linear axis and
  4e307 on a log axis, every recomputation used to raise, the bad value was saved and every later spectrum window then failed in its constructor; message
  "Frequency offset … is too large to draw the frequency axis (at most ±1e+300)"); Full Scale must be between 1e-150 and 1e150 (round 8, the user decided
  on 2026-10-26 that it gets a limit too; message "Full scale … is out of range; it must be between 1e-150 and 1e+150") — 0 dBFS is the power of a
  full-scale tone, FS²/2 (FS² for complex data), and within this range FS² lies in 1e-300 to 1e300: a normal double (FS² overflows to Inf above about
  1.34e154 and FS²/2 becomes subnormal or 0 below about 2.1e-154) and the same range as DSV's floor for power-type dB (1e-300 = -3000 dB); dBFS is now
  computed with logarithms (10·log10(P) − 10·log10(FS²/2), magnitude 20·log10(A) − 20·log10(FS)), so within the range (Auto follows the data and may be
  larger) every finite double spectrum gives a finite dBFS and 0 still sits at the floor — it used to divide first, so a tiny full scale with large data
  overflowed P/(FS²/2) to Inf (with full scale 1e-150 a power of 1e8 already did) and the channel power became +Infinity; a finite Min Distance is at
  most 2^53 − 1 (9007199254740991, JavaScript's Number.MAX_SAFE_INTEGER; round 8, decided by the user on 2026-10-26; message "Minimum peak distance … is
  too large: a finite value can be at most 2^53 − 1 (9007199254740991); enter Inf to keep only the highest peak") — beyond it a double cannot tell
  neighbouring integers apart (1e19 and 1e19 + 1 are the same number, so the typed integer may not be the one used), and no spectrum can have that many
  points (2^53 doubles take 64 PiB); an integer larger than the number of bins but within the limit is accepted as in MATLAB (only the highest peak, like
  Inf), and Inf is accepted as in MATLAB; when the spectrogram would need more than 2^26 cells (segments × FFT
  length, three times that with Reassign; 2^26 complex numbers alone are about 1 GB) it is not computed and the message line says why, while the spectrum is still
  drawn — with a typed FFT length longer than Auto and with FFT Length Auto alike (with Auto, a high overlap over a long range exceeds it too: 10 million
  samples at 90 % overlap need about 100 million cells and used to allocate 4–5 GB at once; the note suggests a smaller overlap, a narrower main plot
  range or turning off Reassign); a very small RBW or very long Time Resolution whose window is longer than the samples in the range reports "fewer than
  one window" without designing that window first (RBW 5u or Time Resolution 1.5M s used to allocate billions of points); a subnormal RBW such as 5e-324 or 1e-320 (a valid entry) makes fs/RBW
  overflow, so the window would need infinitely many samples and the message line says "fewer than one window (Inf samples)" (round 9; it used to say
  "Attenuation 60 dB is too large to compute the window", although Hann does not use the attenuation — the attenuation is blamed only when it really
  cannot produce the window), and with RBW Auto a Time Resolution of 5e-324 writes the RBW as Inf in "RBW too large" (it used to be Python's inf).
  Integers such as sample and
  segment counts in the message line are written the way MATLAB's messages write numbers (JavaScript's String): below 1e21 as an integer, larger in
  scientific notation (Window Length 1e300 gives "fewer than one window (1e+300 samples)"; it used to print 301 digits). Within these limits a
  recomputation can still take a lot of memory and some time (the window does not respond until it finishes; measured on an Apple Silicon Mac, the times with no
  other load): 640 000 samples at 99 % overlap with FFT Length Auto and the spectrogram on (42565 segments × 1536 cells, just under 2^26) add about 3.0 GB of
  peak RSS and take 2.3 s; FFT Length 2^24 (the limit) takes about 9 s and, with only the spectrum shown, adds about 2.6 GB per signal the first time and
  stays at about +3.7 GB after recomputing (the new result is computed while the old result and plot still exist), growing with the number of signals —
  about 4.1 / 6.1 GB for 2 signals and 7.4 / 10.7 GB for 4 (first time / after recomputing; measured in round 9 with 20 000-sample signals); a spectrogram
  exactly at the limit (for example 20 000 samples, RBW 2.5k or Window Length 4096 with FFT Length 2^24: 4 segments × 2^24 = 2^26 cells) adds about 8.6 GB
  of peak RSS and stays about 5.4 GB higher afterwards, and after a few recomputations peaks about 10.4 GB higher and stays about 7.4 GB higher (the earlier
  "2^24 adds about 2.6–2.9 GB, about the same with the peak search and the spectrogram view on" holds only for one signal computed once: a drawn
  spectrogram, more signals and recomputations all take more); after switching back to Auto or closing the window Python's memory is released (tracemalloc drops
  from 2.6 GB to 2 MB, so it is not a leak) while the RSS does not shrink right away (the allocator keeps it). After seeing these measurements the
  user decided on 2026-10-27 to keep the limits exactly as they are (FFT Length 2^24, spectrogram 2^26 cells including Auto).
  The Welch average of 1 million samples at 99.99 % overlap (998465 segments) needs no extra memory and takes about 20 s — several times slower
  on a busy machine (the round-6 review measured 34 s, 134 s and 207 s under load). A very large (1e155) or very small (1e-200) full scale and a very
  large Min Distance (1e19, 1e300) used to raise OverflowError / ZeroDivisionError on every recomputation, save the bad value and break every later
  spectrum window; round 7 accepted them (the spectrum at the floor, the channel power ±Infinity, only the highest peak), and since round 8 they are the
  error state above; out-of-range values in the settings file (1e155, 1e300 saved by round 7) are replaced by the defaults (Auto, 1) when the window
  opens, without a note.
  Unlike MATLAB: MATLAB's toolstrip differs per field — the Spectral Mask, Peak Finder, Distortion and Channel Measurements fields take the leading number
  ("12abc" is 12, "2k" is 2, "500m" is 500) while fields such as RBW, Window Length, FFT Length and Attenuation are evaluated as
  MATLAB expressions (no 2k shorthand, and a unit word is an error) — DSV uses this one rule everywhere, plus the dB-type fields' own unit words (so
  Threshold takes only dB with a dB-type y-axis; MATLAB's field takes only the leading number and ignores unit words); MATLAB has none of the six limits above (it is
  a stream and computes one segment at a time; its frequency offset only has to be finite, full scale any positive number and Min Distance any positive
  integer); MATLAB does not say how to reach a disabled field; DSV checks the lower
  bound of Time Resolution only with resolution method RBW and a specified RBW (≥ 1/RBW), while MATLAB
  always checks the minimum attainable time resolution once data has arrived (max(1/(span/2), 1/fs) with RBW Auto, otherwise 1/actual RBW, also in window-length
  mode) and also rejects values below the sample time — in DSV a tiny Time Resolution is no error and has no
  effect in window-length mode, and with RBW Auto it turns into "RBW too large"; for Time Span MATLAB compares with twice the actual time resolution,
  DSV with twice the update time (the spacing of two spectrogram lines) — MATLAB's actual time resolution in each mode was not
  measured; when span / RBW is below 2 MATLAB marks the RBW field invalid
  while DSV still notes "RBW too large" for that signal and skips it (signals may have different sample rates); DSV reads a blank Min
  Height as no limit (MATLAB finds no number, an error).
- **Scope**:
  - **Views**: Spectrum and Spectrogram toggles, one or both (at least one stays on); Type = Magnitude (DSV default, a tone of amplitude A reads A) /
    Power (power per bin, a sine reads A²/2) / Power Density (divided by RBW, per Hz; white noise σ² has a one-sided density of 2σ²/fs) / RMS (√power, a sine reads A/√2).
  - **Bandwidth**: Sample Rate (inherited from the signal: SPS × symbol rate) and Offset (Hz) added to the frequency axis (for example the carrier for baseband I/Q).
  - **Configuration**: Settings… (spectrogram color limits and colormap), Legend (off by default, as in MATLAB), Colorbar (on), Layout (Vertical = spectrum above
    the spectrogram, Horizontal = side by side).
  - **Data** (DSV only): Recompute, remove DC (subtract each segment's mean), Separate panels, Frequency in Hz (off: cycles/symbol and symbols), I/Q complex (I + jQ from the first two signals).
- **Estimation** (Welch only; MATLAB also has Filter bank, which DSV does not implement):
  - **Frequency Resolution**: Resolution Method **RBW** (default) or **Window length**. RBW Auto = 1024 RBW intervals over the span (two-sided fs/1024,
    one-sided fs/2048); or type a value (10k, 1.5M) with span / RBW > 2. The window length follows from the RBW as in the DSP System Toolbox
    Spectrum Estimator: L = ceil(NENBW·fs/RBW), refined until it stops changing (the shortest window whose RBW does not exceed the request;
    Hann has NENBW exactly 1.5, so fs/1024 gives 1536 samples). FFT Length Auto = max(1024, window length) (measured on the real MATLAB analyzer on 2026-10-24: a 1000-sample window gives a 1024-point FFT, 4000 gives 4000; MATLAB's FFT length rule for spectrum estimation; up to 0.9.9 Auto = window length, from 0.9.10 max(1024, window length)); shorter wraps the windowed data, longer zero-pads.
  - **Window Options**: Blackman-Harris / Chebyshev / Flat Top / Hamming / Hann (default) / Kaiser / Rectangular (Hann, Hamming, Flat Top and Blackman-Harris
    are periodic; Chebyshev = chebwin; Kaiser's β comes from the attenuation), Attenuation (dB) (≥ 45, default 60; Chebyshev and Kaiser only;
    too large for the selected window to be computed is an error, see "Typing numbers" above), Overlap (%) (default 0).
  - The data is a recorded range, not a stream: **the normal trace is the average of all segments in the range** (pwelch mean) and Navg is shown in the info line.
    If the range is shorter than the window RBW Auto needs, the whole range is used as one window (with a notice); a specified RBW / window length that needs
    more samples than the range has is not drawn (with a notice).
- **Measurements → Peaks**: Peak Finder (as in MATLAB): Num Peaks (default 3), Threshold (0), Min Height (blank = no limit), Min Distance (1 frequency bin;
  Inf or an integer larger than the number of bins = only the highest peak, as in MATLAB; a finite value is at most 2^53 − 1) — an invalid field shows the
  common error state (MATLAB's message; the last valid value is used and saved, see "Typing numbers"); Threshold may carry dB (the y-axis unit for linear
  units) and Min Height the y-axis unit;
  Label Peaks (P1, P2, … above the ▼). It searches only the visible frequency range (again after zoom / pan), on the plotted values (dB or linear),
  preferring the normal trace; the Peaks panel at the bottom lists P1… value and frequency per signal.
- **Measurements → Channel**: Channel Selector (MATLAB's MeasurementChannel, the same one as in the Channel Measurements tab): the list holds every plotted
  trace — all normal traces, then all Max-Hold, then all Min-Hold (as in MATLAB) — labelled as in the legend (e.g. "x (Max-Hold)"); channel
  measurements and distortion measure the selected trace (MATLAB also picks the line by its label) and the panels' first column shows its
  name. It is enabled whenever the spectrum view is shown (also with a single item) and selects by list position, so equal names are told apart. Peak Finder
  still lists every signal. With only the spectrogram shown, the selector and the Peaks / Distortion toggles are disabled (as in MATLAB).
  Until you pick a channel in a window it works like MATLAB's index (MeasurementChannel, item 0 by default): with the normal trace off and only Max-Hold drawn it
  measures "name (Max-Hold)", with I/Q complex on it measures the pair. The index counts every signal of the window × the checked traces, including a signal
  that gives no spectrum in the current range (MATLAB's input channels never drop out of the list for lack of data), so when the first signal is skipped the
  panel stays blank with a notice instead of measuring the next one. Once you pick a channel it follows that trace (signal + trace kind); see "Differences
  from MATLAB" below. The settings file stores `cm_channel` as the index into that list (used by new windows; updated when the picked trace moves).
- **Measurements → Distortion** (MATLAB's DISTORTION; batch 3): toggle, Type (Harmonic / Intermodulation), Num Harmonics (including the fundamental, 2 to 99,
  default 6; Harmonic only), Label Harmonics / Label Frequencies.
  - Harmonic Distortion panel: columns THD, SNR, SINAD, SFDR, H1…Hn; rows Frequency, Power (type (unit), e.g. "Power (dBm)"), Rel. Power (dBc), % — THD…SFDR are
    in the Rel. Power row and THD% in the % row, the other cells are blank (as in MATLAB's panel); harmonics above Nyquist leave their columns blank with a notice.
    Intermodulation Distortion panel: F1, F2, 2F1 - F2, 2F2 - F1, TOI (Rel. Power: 2F1 - F2 relative to F1, 2F2 - F1 relative to F2). The plot marks them
    with ▼ (tip on the peak, edge in the line colour; the face is the axes background blended with the line colour by the measured line's alpha / 2 into an
    opaque colour — 0.5 for the normal trace, 0.35 Max-Hold, 0.25 Min-Hold, the same blend as MATLAB); with Label checked it writes H1…, or F1, F2, 2F1 - F2,
    2F2 - F1 (in the line colour). The power row's title follows the settings (also "Power (dBm)" when there is no result); linear magnitude has no unit and
    reads just "Magnitude".
  - The rules come from 20 captures of MATLAB's spectrumAnalyzer run on 2026-10-24 (D1–D11 in `dsv_distortion`): only the f ≥ 0 half is used (a two-sided
    display reads 3.01 dB lower absolute powers), each tone's power is its peak bin's displayed value, harmonics are cleared one by one, Pnoise follows the
    formula in MATLAB's documentation; in power-density mode the power row is in dBm/Hz; the range is the whole Nyquist range; the trace selected in Channel
    Selector is measured (normal, Max-Hold or Min-Hold); complex signals use the positive half. The GUI test applies the settings of 17 captures one by one and
    every value and every panel cell (frequency row, power row, Rel. Power, THD…SFDR, %, F1 / F2, TOI) equals MATLAB's (largest difference 1.3e-11).
  - Known differences (rules the captures cannot pin down, listed separately by the selftest): SFDR when a non-harmonic spur exceeds every harmonic
    (dist_h_alias, 6.73 dB); MATLAB still reports a frequency for a non-existent IM3 product (4171.875 Hz) where DSV leaves it blank (power -Infinity and TOI
    Infinity agree); round-off at 1e-28 W for a noiseless signal.
  - Num Harmonics: MATLAB's field takes the leading number ("12abc" is 12) and only checks 2 to 99 (it accepts 2.5; what happens next was not captured);
    DSV follows "Typing numbers" and needs the whole text to be an integer from 2 to 99 (an SI prefix such as 0.01k works; 12abc and 0x10 are errors).
    An invalid entry works
    like MATLAB's toolstrip: the typed text stays, the field turns to its error state (red frame, tooltip = MATLAB's message), the message line shows it too,
    and the measurement and settings keep the last valid value. Linear units (not captured in MATLAB): the power row shows the displayed value, Rel. Power uses
    dB ratios and TOI is in W. Settings are saved as `dist_*` under `spectrum`.
- **Spectrum** (contextual): Trace Options = Two-Sided Spectrum (on by default as in MATLAB: −fs/2..fs/2, with the Nyquist bin on the positive end for even NFFT;
  off = one-sided 0..fs/2, real signals only; I/Q complex is always two-sided), Normal Trace, Max-Hold Trace, Min-Hold Trace (maximum / minimum over all segments
  at each frequency, drawn in the normal trace's colour at opacity 0.7 / 0.5 like MATLAB); Scale = Frequency Scale (Linear / Log; log only for one-sided),
  Reference Load (Ω), Spectrum Unit (dB / dBFS / dBm / Linear), Full Scale (Auto = guess the ADC bits from the data; a typed value 1e-150 to 1e150).
- **Spectrogram** (contextual): one line per segment, frequency across, time up (newest at the top), colour = the value in the spectrum's units.
  - Channel: the signal shown. The list holds every signal of this window (the pair when I/Q complex is on), including those without a spectrum in
    the range this time, so a skipped earlier signal does not shift the selection to another one; when the selected signal has no spectrum this time
    the first one that has one is shown for now and the message line says so, and in a window with fewer signals (the selected number is beyond
    them) the first one is shown. The selection and the saved `channel` stay, so a window that has that signal shows it again (the same rule as the
    spectral mask's channel; it used to be reset to the first signal and saved).
    Time Resolution Auto = 1/RBW; with RBW on Auto a specified time resolution sets RBW (= 1/time resolution); with both specified it
    must be ≥ 1/RBW (otherwise the Time Resolution field is invalid and the last valid value is used, see "Typing numbers" above) and several
    segments are averaged into one line (MATLAB: several spectral estimates are combined into one spectrogram line).
    Time Span Auto = the whole analysis range; a value shows the last part (at least twice the duration of one update; otherwise the field is
    invalid and the last valid value or the whole range is used).
  - Reassign (MATLAB Signal Analyzer; spectrogram(…,'reassigned')): moves each cell's energy to its centre of gravity in time and frequency.
  - Color limits (default [-80 20], in the spectrum's unit, which may be typed; "Scale to Data" = maximum down to 100 dB below) and colormap (jet / hot / bone / cool / copper / gray; MATLAB's list also has
    parula, MathWorks' own colormap that matplotlib does not include) are in Settings….
- **Spectral Mask** (contextual; MATLAB's SPECTRAL MASK; batch 3):
  - Sections as in MATLAB: **Views** (Upper Mask and Lower Mask toggles), **Configuration** (Upper / Lower Limits, Reference Level (dBr), Channel,
    Frequency Offset); DSV adds **Test → Clear Counts** (MATLAB resets only with a new scope object). Defaults as in MATLAB: both off, upper Inf,
    lower -Inf, reference 0, channel 1, frequency offset 0.
  - Upper / Lower Limits: one number = the same level over the whole spectrum, or [frequency level; …] — two columns (frequency, level), at least two
    rows; frequencies must not decrease (a repeated frequency makes a vertical step), linear in between, not tested outside. A last frequency of +Inf
    extends to the right end (the test uses the previous row's level for that segment; the +Inf row's level only affects the patch, which MATLAB
    still draws to that level, so it slopes; inferred from the interface rules, not measured on its own in MATLAB); a first frequency of -Inf leaves that first segment
    **untested** (measured in MATLAB: [-Inf -30; Inf -30] and [-Inf -30; 500 -30] pass every time; MATLAB still draws the patch to the left edge),
    so to test from the left edge write a finite frequency such as 0 or -fs/2. Levels are dB relative to the reference level; a segment whose level is
    NaN is not tested (measured in MATLAB, mask_A_nan_segment: with NaN from 90 to 110 Hz the points above it there do not count) and has no patch
    (as MATLAB draws it).
  - Reference Level (dBr): a number, or "Spectrum peak" from the list = the maximum of this spectrum of the channel selected in Channel (one value for
    every signal). Channel is enabled only then; its items are the channel numbers 1, 2, … (numbers rather than names, as in MATLAB; how they are
    counted differs, see "Differences from MATLAB" below): one number per signal in the order of this window's signals, the pair when I/Q complex
    is on; a signal without a spectrum in the range this time keeps its number, so a skipped earlier signal does not shift the numbers to another
    signal; when the reference level is a number it is disabled and still shows the selected number. When the selected channel has no spectrum this
    time, the reference level uses the first channel that has one for now and the message line says "the selected channel n has no spectrum this
    time…"; when the number is beyond this window's channels (a window with fewer signals, or only the pair left after turning on I/Q complex) the
    first channel is used too and the message line says "the selected channel n is not in this window (k in total)…". Either way the test still runs
    and counts, and the selection and the saved `mask_channel` stay, so a window that has that channel uses it again.
    The numbers in Reference Level and Frequency Offset follow "Typing numbers" above (2k = 2000, 500m = 0.5; "12abc" and "50abc" are errors; Reference
    Level and the mask levels may carry dBr): clearing
    Reference Level changes nothing (the field gets the current value back, as in MATLAB), Inf / -Inf are accepted (MATLAB's error text
    says finite, but the field does not check); an empty Frequency Offset (added to the mask matrix frequencies; a single-number mask is not
    affected), an incomplete number or Inf is an error.
  - Every signal's plotted spectrum is tested (dB; the normal trace, else Max-Hold, then Min-Hold) on its own frequency grid (signals with different
    sample rates are compared separately) at the displayed frequencies (including the spectrum's frequency offset): any point above upper limit +
    reference or below lower limit + reference fails, and one failing signal fails the test (`dsv_mask`: rules measured on 88 analyzer calls). Each
    spectrum recomputation is one test (a theme redraw is not); changing the mask settings only re-evaluates the last test without counting another;
    Clear Counts resets the counts and tests the current spectrum once (when nothing can be tested it only resets). Counts belong to the window. With
    type RMS, linear units or only the spectrogram the tab is hidden, nothing is tested and the counts stay; with none of the three traces plotted
    nothing is tested either, the panel still shows the counts and the message line asks for a trace.
  - The panel below has MATLAB's one row of 7 columns: Success Rate (%), Passed Tests, Total Tests, Current Status, Upper Mask Status, Lower Mask Status
    (-- when off), Failing Channel(s) (names joined by commas); number columns use the analyzer table's 4 decimals (so test counts read 3.0000, as in
    MATLAB). On the plot the upper mask is filled upward from its limit line to the top of the y axis (to the highest level when a level is above it)
    and the lower mask downward to the bottom (to the lowest level when one is below it); with a NaN level the fill always stops at the axis limit and
    the NaN points are drawn there, so that segment has no fill (as MATLAB draws it); green when passing and red when failing (following the current
    theme), opacity 0.4, no edge; as in MATLAB the patches cover the spectrum lines (a trace segment inside a mask is tinted), with the peak and
    distortion markers, labels and data tips on top; the channel measurement bands and edge lines are on top too (DSV's fixed order, see
    "Differences from MATLAB" below); redrawn for the new axis range after zoom / pan.
  - The GUI test uses the 8 calls of the MATLAB captures mask_A_doc_upper_W4000 and mask_A_status_upper_lower_W4000 (single periodograms, exactly
    reproducible): pass/fail and failing channels equal MATLAB's getSpectralMaskStatus, and the number of points outside the mask per signal equals
    analyze_mask.py's count on MATLAB's displayed spectrum; a scope frequency offset of 1000 Hz with the mask shifted by 1000 Hz
    (mask_A_scope_freq_offset_1000's settings) is compared call by call too, against mask_A_doc_upper_W4000 — that capture itself is WL 1000 with
    4 averages and not reproducible, but on every call MATLAB gives the same result as the unshifted mask_A_doc_upper.
    Custom reference level, spectrum peak of channel 1 / 2, mask frequency offset (both directions), lower mask and different sample-rate grids are
    checked against expectations computed from MATLAB's displayed W4000 spectra. Captures that average (SpectralAverages > 1) are a streaming exponential average
    while DSV averages one recorded range, so their numbers differ; `dsv_mask`'s selftest checks those on the captured spectra.
  - An invalid field works like MATLAB's toolstrip: the typed text stays, the field turns to its error state (red frame, tooltip =
    MATLAB's message) and the message line and status bar show it; the settings keep the last valid value until a valid entry (or clearing Reference
    Level, which writes the value back) clears it. The status bar then returns to what it said before — while another field (mask, distortion,
    channel measurements) is still in its error state it shows the most recently written of those errors instead, and only when all are fixed does
    it return; when another feature has already written a newer status it is left alone.
  - Differences from MATLAB: MATLAB's English error for the lower mask says "upper", DSV says "lower"; Upper / Lower Limits accept only numbers and
    matrices, and the brackets may be omitted: an unbracketed "0 -17; 90 -17" is taken as a matrix, the numbers in a matrix follow "Typing numbers"
    (0.09k, 0.5kHz in the frequency column and dBr after a level work) and "12abc" is an error (MATLAB's field takes
    the leading number — "12abc" becomes 12 and an unbracketed "0 -17; 90 -17" becomes 0 — and evaluates the text in the MATLAB workspace only when there
    is no leading number); typing "Spectrum peak" (or spectrum-peak, or the Chinese label) in Reference Level also selects it (a DSV convenience; MATLAB's field only
    honours the list item, and whether MATLAB's editable combo box turns typed text into the item was not probed); DSV rejects an Inf / -Inf frequency
    offset (MATLAB's field does not reject it and what happens next was not probed; the field's error text asks for a finite value); channel numbers are
    one per signal, while MATLAB's list has one item per plotted trace (one group each for the normal,
    Max-Hold and Min-Hold traces), so with two signals and both the normal and Max-Hold traces MATLAB lists 1 to 4 (what picking 3 or 4 does was not
    measured), and with one kind of trace both agree; when the selected channel has no spectrum this time or is beyond this window's channels the
    reference level falls back to the first channel that has one and the test still runs (MATLAB never has a channel without a spectrum in range; for a
    number beyond the input channel count MATLAB's behavior was not measured; DSV's settings are shared by every
    spectrum window, so a window with fewer signals can have the selected number beyond its channels, and DSV keeps going and says so on the message
    line); the channel measurement bands and edge lines are always drawn above the mask patches (MATLAB draws its annotations in the order they were
    added, so whichever was turned on later is on top; this was not measured in MATLAB but inferred from the interface rules); Reference Level and Frequency Offset
    do not use MATLAB's lenient parsing (in MATLAB "12abc" is 12, "2k" is 2 and "500m" is 500) but "Typing numbers" ("12abc" is an error, 2k = 2000,
    500m = 0.5 — the same rule as the other fields of the window). Settings are saved as `mask_*` under `spectrum`.
- **Channel Measurements** (contextual; MATLAB's CHANNEL MEASUREMENTS; batch 3):
  - Sections as in MATLAB: **Channel** (Channel Selector: the trace measured, see "Measurements → Channel"; I + jQ for I/Q complex), **Channel Measurements** (toggle, Type = Occupied BW / ACPR,
    Occupied BW (%): 0 to 100 exclusive, default 99), **Frequency Options** (Span and Center Frequency, default 2000 / 0; or Start and Stop Frequencies, default
    −1000 / 1000), **Adjacent Channels** (ACPR only: Num Pairs 1 to 64, default 2; Offsets [2000 3500]; Adjacent BW 1000; Filter Shape None / RRC / Gaussian;
    Roll-off Factor or BT Product 0 to 1, default 0.5, disabled for None).
  - **Occupied BW**: the panel below lists Channel Power, Occupied Bandwidth and Frequency Error (= middle of the occupied band − center frequency; in start/stop
    mode the center is (start + stop)/2); the plot shades the measured band (opacity 0.45; as in MATLAB it covers the spectrum lines; the spectral mask
    patches always stay below it, while in MATLAB the one turned on later is on top) with two dashed lines at the occupied-bandwidth edges (MATLAB's
    dash: 1 px, [10 5] px).
    **ACPR**: one column per pair (ACPR1…) with Offset, Lower and Upper (dBc relative to the main channel), scrolling sideways for many pairs;
    the plot shades the main channel at 0.45 and the adjacent channels at 0.25 — for a pair whose offset is 0 (the 0s added when Num Pairs grows)
    MATLAB draws only a 1 px line in the line colour at x = 0, with no shading.
  - The rules come from captures of MATLAB R2025a's spectrumAnalyzer run on 2026-10-24 (`tests/matlab_ref/scope`): the trace selected in Channel Selector is
    measured (normal, Max-Hold or Min-Hold); PSD = displayed power / RBW (the displayed values in power-density mode), each bin integrated as a constant over
    [f − df/2, f + df/2]; channel power is the integrated power in dBm in both power and power-density modes (= 10·log10(P / reference load) + 30; dB / dBFS /
    linear use the same conversion as the power spectrum). The panel's "Channel Power" header shows the spectrum's display unit as MATLAB does (= the y axis:
    dBm/Hz, dBFS/Hz, W/Hz in power-density mode, dBV for RMS in dB, as in MATLAB) — MATLAB's header says /Hz while the
    number is the integrated power, and DSV copies that; the status line gives the number's own unit (dBm). The frequency offset is subtracted before measuring and
    added back afterwards (the measurement runs on the grid without the offset), so GHz offsets with a fine resolution still measure; the occupied-bandwidth edges
    are at (100 ∓ P)/200 of the cumulative power; ACPR is a plain power ratio
    (no comm.ACPR bandwidth normalisation); RRC / Gaussian are power weights applied to the PSD (symbol rate = the main channel span, the same filter moved to each
    adjacent channel). A band outside the spectrum gives NaN for all three Occupied BW values and NaN only in that cell for ACPR (MATLAB neither errors nor clips;
    two-sided, −fs/2 is not a frequency bin, so [−5000, 5000] is NaN too); those cells are blank in the panel (MATLAB's table only writes numbers,
    NaN shows nothing) and the message line gives the actual reason (main channel outside the spectrum, main channel power 0, adjacent channel power 0 →
    -Infinity). When nothing can be measured (start ≥ stop, the selected trace not plotted) the status line says why too; turning the measurement off puts the
    spectrum's status back instead of keeping the last band and channel power. The GUI test types the settings of 42 captures (21 Occupied BW, 21 ACPR, including
    RRC / Gaussian, start/stop, one-sided, power density and I/Q) into the toolstrip one by one and every number equals MATLAB's.
  - Automatic band on enable, and on a type change while enabled (MATLAB restarts the measurement), as in MATLAB: until you change span /
    center / start / stop, it uses the analyzer's full range (two-sided [−fs/2, fs/2], one-sided [0, fs/2], plus the frequency offset; the lower
    end is RBW on a log scale), or the current x range once you zoomed / panned the spectrum axes (with spectrum and spectrogram together matplotlib's x range is
    the spectrogram image's edge and cannot be used directly), intersected with the Nyquist range: center = middle, span = width/5, adjacent BW = width/10, the
    first two offsets = width × [4 7]/20 (the full two-sided range gives the defaults; one-sided 0 to 5000 Hz gives 2500 / 1000 / 500 / [1000 1750], as in the
    MATLAB capture); once a value really changes it stops (pressing Enter on the same value, or 2e3 for 2000, does not count).
  - Panel numbers follow the analyzer's table: 4 decimals (rounded from the exact double value), NaN left blank, and engineering units for frequencies (kHz, MHz…, one prefix for the whole group,
    from the largest value; a frequency error of ~1e-12 Hz shows in pHz, as in MATLAB). The first column header is the selected trace (its legend text); it stays
    when a measurement fails while there is data, and reads - - when there is none (the selected trace not plotted; as in MATLAB). The ACPR offset
    row's unit comes from the whole stored offsets array (fewer pairs do not shorten it, as in MATLAB), showing only the first Num Pairs values.
  - An invalid field (percent 150, 0 pairs, a number of offsets other than Num Pairs, coefficient 1.5…) works like MATLAB's toolstrip: the typed text stays, the field turns to its error state (a red frame in both themes) with MATLAB's message as its tooltip, the message and status
    lines show it too, and the settings and measurement keep the last valid value until a valid entry clears it. Changing the type or the filter shape rewrites
    the offsets and adjacent BW fields with the stored values, and changing the frequency span mode rewrites both frequency fields (as in MATLAB), so a pending typo is not carried into another mode and a disabled or
    swapped field does not keep an error. Start ≥ stop is accepted (MATLAB does not block it) and the measurement is NaN with a notice. More pairs pad the
    offsets with 0, fewer use the first ones (the rest are kept and come back). Every field (and every number of the offsets) follows "Typing numbers":
    2k, 1.5M and 500m work; 12abc, 1..2 and 0x10 are errors.
  - Differences from MATLAB: the ACPR panel's offset row is always "Offset (unit)" (MATLAB's cell turns into "Frequency (Hz)" after a unit change); the adjacent BW
    error uses DSV's own message (MATLAB reuses the center frequency one and marks the frequency offset field as the error); the English panel title reads Occupied BW
    (MATLAB: Occupied Bandwidth); once you pick a channel, the Channel Selector follows that trace (signal + trace kind) within the window: when the list
    shifts the same trace is measured (`cm_channel` follows its new position), and while it is missing (unchecked, another I/Q pair) the selection is kept and
    the panel shows - - with blank cells (MATLAB's MeasurementChannel is just an index that points at another line when the list changes); before any pick it
    is MATLAB's index; the fields are stricter than MATLAB's: MATLAB's toolstrip takes the leading number ("50abc" is 50, "2k" is 2,
    and Inf is accepted), then checks the range for Occupied BW %, Num Pairs and the coefficient, and only NaN for span / center / start / stop frequency
    and Adjacent BW (what an Inf or negative span does next was not captured); DSV follows "Typing numbers" and needs the whole text to be a valid finite
    number (every field takes SI prefixes such as 2k, 1.5M and 500m — the same rule as the other fields of the window), span and Adjacent BW must be > 0 and
    Num Pairs an integer. Settings are saved as `cm_*` under `spectrum`.
- Info line: Window (and attenuation), NENBW (equivalent noise bandwidth, bins), RBW, window length, NFFT, overlap, Navg, the spectrogram's time resolution and line
  spacing, type, units and Full scale / Reference load.
- The computations are checked value by value against MATLAB (`tools/matlab_ref/spectrum_ref.m` runs MATLAB R2025a's pwelch, spectrogram and window functions
  to produce `tests/matlab_ref/spectrum_ref.json`, compared by `python signal_viewer.py --selftest`): windows, NENBW, Welch mean / max-hold / min-hold,
  one-sided / two-sided / centred frequency axes, overlap, NFFT wrapping and zero padding, power / psd, spectrogram and reassigned spectrogram, spectrum peaks.
- The old "Welch segments" control (0.9.5 and earlier) is replaced by RBW / window length; old settings keep hann / hamming, rect → Rectangular, blackman → Blackman-Harris.
The plots in the Spectrum and GFSK windows have the same interactions as the main plot: wheel zoom, left-drag to pan,
double-click empty space or Home to reset the view, click a line to pin a data tip (the toolbar "Data tip" toggle turns this off), and a right-click menu
(delete / clear data tips, reset view, copy figure to clipboard, copy as vector graphic); data tips are cleared when you recompute or change an option. Ctrl+W (macOS ⌘W) closes the window (MATLAB figure File > Close).

## GFSK Analysis Steps
1. Import a CSV with I and Q columns (e.g. `Time, adc i, adc q`), fill in the Sample rate with "Use Estimate" or by hand, suggested shift −512 (10-bit ADC),
   plot them merged in one panel.
2. Set the Symbol rate in **View → Axes** (or Signal Properties → View / Diff, Preferences → Plot; 1M for LE1M; internally fs = SPS × that panel's symbol rate).
3. Click a panel that has I and Q (or select I and Q in the list) and press "GFSK…" (or a panel's right-click "GFSK (P1)…"; the target rule is the same as for AM/PM/FM).
   Auto-pairing rule: within one panel, names matching `adc i` / `in_i` / a standalone `i` and `adc q` / `in_q` / a standalone `q`;
   if nothing matches, the names of the first two signals are used; if that also fails and exactly 2 signals are selected, those 2 are taken as the pair.
4. Enter the IF frequency, 3dB bandwidth, I/Q order (IQ / QI), Filter taps (5..129, forced odd), then press Enter or "Recompute".
5. Processing: truncate to equal length → multiply by `exp(-j2π·fc·n/fs)` to down-convert → subtract the mean → Gaussian filter
   (`g = exp(-(π·sqrt(2/ln2)·bw·t)²)`) → unwrap the phase → first difference × fs/2π gives the frequency (Hz). x axis in seconds, y axis in Hz.

Recommended parameters:

| Mode | IF | BW | Deviation |
|---|---|---|---|
| LE1M | 1 MHz | 500 kHz | ±500 kHz |
| LE2M | 1.77778 MHz | 500 kHz | ±1 MHz |
| LE4M | 4 MHz | 1 MHz | ±2 MHz |

> If the discriminator output looks upside down, change the I/Q order to QI; if the frequency has a constant offset, adjust the IF frequency.

## Export TXT
Select signals (or none = all) and press "Export TXT"; after choosing a folder, each signal is written to its own `NN_<safe filename>.txt`,
with values rounded to int64 when the source data are integers, and written as-is when the source has fractions (e.g. float I/Q in a CSV) (NaN / inf raise an error). File header:

```
# source=<file path> column=<column>
# n=<sample count>
# despike=on|off k=.. thr=.. min=.. fixed=..
# shift=.. scale=..
```

The folder is opened automatically when done. These files can be read straight back into this program as text files.

## Preferences, Figure Export, Zoom Out and Direction Limits, Undo Names (after MATLAB Settings / Export To… / axes toolbar / Edit ▸ Undo)
- **Preferences** (Home → Environment → Preferences; macOS ⌘,) has three more pages and a **Help** button at the bottom left
  (opens this guide at this section, like the Help button of MATLAB Settings):
  - **Fonts** (Settings ▸ Fonts): **UI font size** (9–16 px, default 12 px as measured from MATLAB R2025a; toolstrip, panels, tables, menus and tooltips
    change together as soon as you press Apply), **Plot font size** (6–20 pt, default 10 pt; tick labels, axis labels, titles, legends, data tips and
    text annotations scale together in the main plot, Spectrum, GFSK and figure windows), and "Restore Default Font Sizes".
  - **Export**: the **Default DPI** (default 150) and **Default background** (Theme color / White / Transparent) the "Save Figure As…" dialog starts with.
  - **Appearance ▸ Theme** (1.0.0): besides MATLAB's **Dark / Light** there are six more looks (the View → Appearance dropdown has the same list).
    All six change only the colour palette and the corner radius — the colours are inspired by the brand looks, not copied from any brand's assets;
    layout, sizes and fonts stay as measured from MATLAB; the MATLAB plot style follows the theme with a matching palette (figure face = window
    background, so the plot has no seam; axes face = input background in the two Sony themes and Apple (light), #141414 — one step darker than
    the input background — in Apple (dark) and Apple (dark, graphite), and pure black in Apple (dark, black); the matplotlib style does not follow); the analysis windows (Spectrum, GFSK,
    AM/PM/FM, Constellation, Eye Diagram) draw their lines in the theme's line colours too (the first one is in the theme's accent colour family; Dark / Light keep
    matplotlib's colour order); Dark / Light are unchanged to the last value. Saved as `view.theme`; a theme name an older version does not know falls back to Dark,
    so after opening 0.9.14 or an earlier version, choose the theme again when you come back to 1.0.0.
    - **Sony (black)**: the matte warm black of an α camera body, graphite-silver borders and tab strip, and a single accent colour — α orange — used
      only for highlights (focus frames, the focused selection row, primary buttons, the selected panel header, the panel selection frame,
      the zoom box and the like); 1 px corners; the
      plot's first line is α orange too, the rest are MATLAB's dark colours (the second orange dropped, cyan — orange's complement — second,
      blue last).
    - **Sony (deep blue)**: the blue-black background and cool white text of the PlayStation system UI; PlayStation blue for primary buttons and the
      selected panel, electric blue for highlights such as focus frames, the panel selection frame, the progress bar and the icons' accent strokes; 3 px corners; plot lines in the same hue order
      (electric blue #2e8cff — the accent colour — / orange / yellow / purple / green / cyan / pink).
    - **Apple (light)**: the macOS light appearance — #ececec window, white content areas, the macOS purple accent colour (light-mode system purple
      #af52de; surfaces that carry white text, such as primary buttons and the selected panel, use the accessible deeper purple #8944ab, 6:1 with
      white; selection rows are a light lilac), and a tab strip that works like a light grey segmented control (dark text, the selected tab merges
      into the content); 5 px corners; figure face = window grey, opaque hairline grid, HIG accessible system colours for the lines (the first is
      purple, system blue last).
    - **Apple (dark)**: the macOS dark appearance — #1e1e1e window, a graphite tab strip instead of a blue band, and the macOS purple accent colour
      #bf5af2 only on what is selected or being operated (focused selection row, primary buttons, focus frames, the selected panel); 5 px corners;
      HIG dark system colours for the lines, the first one system purple.
    - **Apple (dark, graphite)**: the Apple (dark) window with graphite selection and selected-panel surfaces and system orange #ff9f0a as the accent
      (focus frames, the plot's first line and the selected data-tip frame); 5 px corners.
    - **Apple (dark, black)**: a watchOS-style pure black window and plot background with system green #30d158 as the accent — the same green family
      as the "success" status colour, so green does not always mean success here; the green of primary buttons and the selected panel is darkened to
      #24883d so white text reaches 4.5:1; 5 px corners.
    (2026-11-01, the user: "do all of it" — Sony (black) gets an orange first line, Apple (light) switches to purple, and the two Apple dark variants
    seen in the trial stay as options; Sony (deep blue) keeps its blue, which is PlayStation's identity.)
  - **Confirmation Dialogs** (General ▸ Confirmation Dialogs): **Confirm before clearing all signals** (on by default; when off, Clear removes
    everything at once — still undoable with Ctrl+Z / ⌘Z).
  - The **Plot** page has a new **Zoom/pan direction** (Unconstrained / Horizontal (x) / Vertical (y); see below).
  - All of these are saved in the settings file (`view.ui_font_px`, `view.plot_font_pt`, `view.export_dpi`, `view.export_bg`, `view.confirm_clear`,
    `view.nav_dims`); older settings files without them use the defaults.
- **Save Figure As…** (Export → Image File; the save button on the plot toolbar; the save buttons of the Spectrum, GFSK and figure windows and their
  "File → Save Figure As…") is MATLAB's **Export To…** dialog:
  - **Format**: PNG, JPEG, TIFF, PDF, EPS, SVG, PS, SVGZ, GIF, WebP, AVIF (whatever matplotlib can write; PGF, which needs LaTeX, is not listed).
  - **Content type**: PDF / EPS / PS / SVG are **vector** automatically (lines and text scale without loss), the others are **image** (raster);
    the bottom of the dialog shows the output size in pixels or inches.
  - **Resolution (DPI)** (36–1200, default 150) and **Background** (Theme color = what you see on screen / White / Transparent — transparent also
    clears the axes background).
  - **Width / Height + Units** (in / cm / mm / pt / px): the current figure size by default; a different size re-lays-out the figure just for the file
    (the figure on screen does not change); "Current Size" puts it back.
  - Press **Export…** and pick a file name. The crosshair is never included; data cursors are. The dialog remembers the last format, DPI and background.
- **Export This Panel Only…** (right-click empty space or a line; also in the Spectrum and figure windows): saves just that panel (with its right axis,
  ticks, labels, title, subtitle and legend; not the figure title); the other panels are hidden for the moment and the file is cropped to the panel's
  tight bounding box plus 0.1 in.
  The default file name is `signal_viewer_P<n>`.
- **Zoom out** (the magnifier-minus button right of zoom on the plot toolbar, MATLAB's axes-toolbar Zoom out): every panel zooms out 1.5× around its own
  center (the shared x only once), stopping at "show all" like the wheel (as in MATLAB, down to the original limits); it goes into Previous / Next View.
- **Direction limits** (MATLAB Unconstrained / Horizontal / Vertical Zoom and Pan = `InteractionOptions.LimitsDimensions`): the zoom-mode right-click menu
  (Zoom Out Shift-Click, Reset View | Unconstrained / Horizontal / Vertical Zoom), the **pan-mode right-click menu** (Reset View | Unconstrained /
  Horizontal / Vertical Pan — as in MATLAB, right-click on empty space in pan mode no longer shows the general menu; a right-click **on a line** still opens the signal menu
  with Delete this signal, colour…), or Preferences → Plot. With "Horizontal" the
  **wheel, drag panning, pan-mode dragging, zoom-mode clicks and boxes, + / −, arrow keys and the Zoom out button** change x only ("Vertical": y only);
  the limit stays after leaving the mode (as in MATLAB) and the status bar says which direction is active. A Shift / Ctrl + wheel axis that the limit
  excludes does nothing.
- **Undo / Redo show the action** (MATLAB Edit menu "Undo: Pan"): the Undo / Redo button tooltips on the quick access toolbar and the Home tab, the
  right-click menus on the plot and the list, and the Edit menu of figure windows read "**Undo: <action>**" / "**Redo: <action>**"
  (e.g. "Undo: Line color #ff0000"); with nothing to undo they read just "Undo" and are disabled. After undo / redo the status bar says
  "Undone: <action>" / "Redone: <action>". Views (zoom, pan) still use Previous / Next View rather than Undo.

## Keyboard shortcuts (MATLAB Preferences ▸ Keyboard ▸ Shortcuts)
- Every toolstrip action has a configurable shortcut (**Preferences → Keyboard**): the list on the left shows the actions (search by name,
  category or shortcut); select one, press the key combination in the "Press a new shortcut" box and click **Add**.
  **Remove Selected Shortcut**, **Restore Default for This Action**, **Restore All Defaults**; **Export… / Import…** save the shortcuts as JSON
  (to move them to another computer or share them; a file saved on macOS swaps ⌘ for Ctrl when read on Windows).
  A key can belong to only one action: adding a key that another action already uses asks whether to reassign it; a conflict created by
  restoring a default is marked ⚠ on the row with the count shown above the list.
- Changed shortcuts are stored in the settings file under `shortcuts` (only actions that differ from the default), so auto-restore and
  Import Settings bring them back; button tooltips show the current shortcut.
- Defaults (⌘ on macOS, Ctrl on Windows/Linux):

  | Action | Default | Action | Default |
  |---|---|---|---|
  | Undo / Redo | ⌘Z / ⌘Y, ⇧⌘Z | Copy / Cut / Paste signals | ⌘C / ⌘X / ⌘V |
  | Select All | ⌘A | Remove selected signals | Delete, ⌫ |
  | Move Up / Down | ⌥↑ / ⌥↓ | Import CSV… | ⌘I |
  | Export Settings… / Import Settings… | ⌘S / ⌘O | Browse Root Folder… | ⇧⌘O |
  | Rescan | F5 | Help / Preferences… | F1 / ⌘, |
  | Previous / Next transition | `[` / `]` | Previous / Next difference | ⇧`[` / ⇧`]` |
  | Data Tips | ⌘T | Grid / Legend | ⌘G / ⌘L |
  | Show All | ⇧Home | Plot Only | ⇧⌘M |
  | Link Time (current panel) | ⌘U | | |
  | New Figure Window | ⌘N | Copy Figure / Save Figure As… | ⇧⌘C / ⇧⌘S |
  | Restore View (plot) | Home | Zoom In / Out (plot) | `+`, `=` / `-` |
  | Pan (plot) | ← → ↑ ↓ | Other actions | no default; assign your own |

  "Other actions" include the eight Preprocess functions (Lowpass … Envelope, which open the Function Parameters panel), the Panner, Extract Signals Between Time Limits / Between Time Cursors, Preserve Start Time, the five measurement groups and Bilevel Settings…,
  glitch suppression parameters…, comparison tolerance…, Data cursors None / One / Two, and the folder panel's Back / Forward / Up.

- Rules: while a text field (address bar, parameter entries) has focus, typing keys and editing keys such as ⌘C / ⌘V / ⌘Z still go to the field;
  while a list has focus, arrow keys and Home belong to the list and do not pan the plot; plot keys (restore view, zoom, pan) are handled by the
  plot itself when the canvas has focus and still act on the plot when pressed on another panel. On the plot, Delete / Esc are fixed
  ("delete the selected tip/annotation", "cancel").
- **Zhuyin, Russian, Greek and other non-Latin input sources** (item 13, 2026-10-26; the user's second menu choice on 2026-10-27, "fix them all"): shortcuts are
  recognised by the key's **physical position** (ABC layout), as in other Mac apps. Tk 8.6.13 translates a key with the current keyboard layout and then looks up a
  keysym (⌘ and ⌃ are not taken into account), so with Zhuyin (measured with real key presses) ⌘V has the keysym `??` (the V key is ㄒ), so do ⌘W and ⌃A;
  `[` / `]` are `kana_openingbracket` / `kana_closingbracket` (the CJK corner brackets U+300C / U+300D), ⇧`[` is `kana_openingbracket` + Shift
  (the shifted bracket U+300E has no keysym) and `-` is `??` (ㄦ) — the matching shortcuts used to do nothing. They now all go by the physical key:
  - every ⌘ / ⌃ shortcut of the main window, the Plotted Signals list, ⌘C / ⌘V of the AM/PM/FM window (item 13);
  - **figure windows**: ⌘C copy, ⌘V paste (overlay), ⌘Z / ⌘Y (⇧⌘Z) undo / redo, ⌘A select all, ⌘S save JSON, ⌘W close (plotkit's own figure windows too);
  - **every analysis window** (Spectrum, GFSK, AM/PM/FM, Constellation): ⌘W close, ⌘Z / ⌘Y undo / redo the view;
  - **keys without ⌘**: `[` / `]` previous / next transition, ⇧`[` / ⇧`]` previous / next difference, `-` zoom out on the plot (wherever a key works with ABC,
    it works with Zhuyin);
  - the **measurement table and the data cursor table**: ⌘C / ⌃C copies **the table's text** (TSV) and never the signals — with Zhuyin it used to copy signals
    (found by the final verification on 2026-10-27; the status bar even said "Copied 1 signal");
  - **text fields and dialogs** (address bar, parameter entries, comboboxes, spinboxes, text areas, list boxes, the Title… / Name… dialogs): ⌘C / ⌘V / ⌘X / ⌘A
    (plus ⌘Z in text areas) and emacs keys such as ⌃A / ⌃E / ⌃D / ⌃K behave exactly as with ABC; while a main-window text field has focus, ⌘C / ⌘V still act
    on the text, not on signals;
  - Preferences → Keyboard records the same shortcut for `[`, ⌘V or ⇧`[` with Zhuyin as with ABC.
  - **Nothing changes with ABC**: only non-Latin keysyms (`??`, `kana_…`, `Cyrillic_…`…) are replaced by the physical key, and ABC only gives Latin ones, so that
    layer never acts; Latin layouts such as German (ü) or Dvorak keep their own characters; characters typed with Option alone (⌥A = å) are unchanged.
  - **The 3, 7 and `` ` `` keys with Zhuyin**: Tk gives the Latin-named keysyms `caron` (ˇ), `abovedot` (˙) and `periodcentered` (·). ABC never produces
    those keysyms on those three keys, so when the keysym and the physical key both match they too are recognised by the physical key as 3, 7 and `` ` ``
    (the user's fifth menu decision of 2026-10-27: with Zhuyin, ⌘3 is ⌘3, and Preferences → Keyboard records it as ⌘3). No default shortcut uses those
    keys, so only shortcuts you record yourself are affected; another layout producing the same character on another key (Czech ˇ on the = key) is unchanged.
  - **⇧`[` / ⇧`]` (previous / next difference)**: the default shortcut is written ⇧`[`, but Tk reports the shifted character `{` (`braceleft`) — **this never matched
    with ABC either** (already so in 0.9.9, confirmed with real Tk events). Now "the shifted symbol of the same key" counts as ⇧`[` when nothing is bound to it;
    a ⇧`{` you recorded yourself in Preferences still wins.
  - **⇧= (the default Zoom In is written `+`)**: Tk reports the shifted character `+` (`Shift+Plus`) while the default shortcut is `Plus` without Shift, so
    outside the plot (focus in the main window, not in a list) ⇧= never matched before — with ABC and Zhuyin alike (already so in 0.9.9; with the canvas focused
    the plot handles the key itself, so it always zoomed there). Now, when nothing is bound to it, "the symbol itself" is tried too (the user's seventh menu
    decision of 2026-10-27); a ⇧`+` you recorded yourself still wins; on the canvas it still zooms exactly once.
    **The same with the focus in the Plotted Signals list** (fixed in 0.9.11; before, after clicking a row of the list ⇧=, = and − did nothing — already so in 0.9.9):
    while the list, a scrollbar, a slider or a tab bar has the focus, only the keys those widgets use themselves (arrow keys, Home / End, PageUp / PageDown, Return,
    space…) are kept from the plot — ↓ still moves the selection, ← / Home neither pan nor restore the view — and every other plot key (⇧= / = zoom in, − zoom out,
    including the Zhuyin keys matched by physical position) works without clicking the plot first.
  - How text fields are handled: the Tk class bindings `<Mod1-Key>` / `<Control-Key>` of the text widget classes (which did nothing) get a front part that looks up,
    by physical key, the binding that class would match with ABC — a virtual event such as `<<Paste>>` is sent to that widget (every binding tag handles it as
    usual), a class binding such as `<Control-Key-d>` is run as is (`plotkit/keys.py`, installed when DSV starts and when plotkit opens its first figure window).
    Ordinary typing in a text field still goes to the input method.
  **One key press acts once**: the key event and the Edit menu's virtual event (`<<Paste>>`…) of the same key press run the action once; choosing the item from
  the menu alone still runs it (see "Copying and pasting signals with ⌘C / ⌘V"). The physical-key fallback only acts when Tk's own binding did not match, so one
  key press never acts twice.

## Settings and Auto-restore
- "Export Settings" saves version (6 since v3.4), root, x range, view settings (including MATLAB style, wheel zoom), Spectrum / GFSK / Constellation / Eye Diagram / Error Rate / CSV defaults,
  every parameter of each signal (line color, width, style, marker, visibility, left/right axis), annotations and data tips as JSON; v3.2 settings files can be read directly;
  the data of independent signals (derived signals whose sources were deleted) is stored in the file too (`frozen_data`), so the file does not depend on the frozen
  folder (whose files are cleaned up once nothing uses them, see above); "Import Settings" restores them (you are warned when the root in the file does not exist;
  since 0.9.13 signals whose files cannot be found stay in the list as placeholders until the files are back, see "Opening while a source file is temporarily missing" below; when the path of an independent signal's data file belongs to another account or computer and this computer's frozen
  folder has a file with the same name whose content matches, that file is used — see "The autosave can be read but some signals cannot be restored" below).
- **Importing a settings file that carries data: if the frozen folder cannot be written, nothing is imported** (2026-10-26): when the settings file carries
  independent signals' data, every piece of it is written into this computer's frozen folder and read back **before** anything is imported. If this window cannot
  register in the folder or the folder cannot be written (read-only — also when the data is already in the folder —, full disk, a file with the same name in the
  way, any write error), **the whole import is cancelled**: the current session is not touched at all (signals, layout, settings and undo history stay as they
  were), and the error dialog "Import cancelled" names the signals, the folder path, the reason and the settings file. Make the folder writable and import again
  (before, the session was replaced and those signals were skipped).
- With "Auto-restore Last Session" checked, closing the window (or quitting with ⌘Q on macOS) saves automatically to `~/.signal_viewer_last.json`; the next start restores it automatically.
  **A start with arguments does the same** (0.9.13, user decision B2 of 2026-10-28): `python signal_viewer.py <files or folders…>` on the command line and files
  dropped onto the Windows exe first restore the last session as usual, then add the arguments by the rule of the "Drag and drop" section — a folder becomes the
  root folder and is scanned, a data file opens a new panel with all its columns or the whole signal, files already plotted are not added again but selected,
  unknown or missing paths are listed in the status bar, ⌘Z undoes; the status bar says "Start-up arguments: added 2 signal(s) to P3".
  (Before 0.9.13 a start with arguments did not restore the session, took only the first argument as the root folder and silently ignored files, and did not
  apply the preferences either; on close the autosave was overwritten by that session and the previous session's independent-signal data files were then
  cleaned up as unused.) Opening the macOS app from the Finder / Dock passes no arguments; dropping files on the Dock icon works as before.
  With it unchecked, closing saves only the preferences (language, theme, view settings) to that file, and the next start does not restore the old signals
  (with arguments likewise: only the preferences are restored and only the given files are opened);
  the figure title, every panel's names and titles and the collapsed state are not carried over either (the user's fifth menu decision of 2026-10-27; each
  panel's axes settings — units, Symbol rate — are kept as in 0.9.9).
- **Opening while a source file is temporarily missing** (user decision of 2026-10-28, 0.9.13): when a signal's file is missing during auto-restore or "Import Settings"
  (external disk not connected, file moved), that signal **stays in the Plotted Signals list as a placeholder** (greyed out, Fmt column "file missing", n empty) and is
  not drawn; the derived signals built on it (I/Q magnitude / phase / FM, Preprocess results, whole chains) are kept too and not drawn (Fmt column "waiting for source
  file"), with all parameters, the panel's axes settings, names and titles; the autosave and "Export Settings" keep recording them (path, parameters, panel layout), so
  they survive closing and reopening, and the status bar's signal count says "(k with missing files)". One notice at start-up (the notice window shown once the main
  window is up; it does not block anything and is merged with "Some signals of the last session were not restored") lists the missing files; "Import Settings" lists
  them in its usual "file not found" warning. **A settings entry without a file path** (a hand-edited, broken file, or a derived-signal kind this version does not
  know) is not "temporarily missing" — there is nothing to wait for: as in 0.9.12 it is **skipped with a notice** "Files not found, skipped" (at start-up merged into
  the start-up notice "Some signals of the last session were not restored", on Import Settings in the warning; derived signals built on it are skipped with it), it
  does not stay as a placeholder and the autosave written on close no longer records it; when it uses an independent signal's data (frozen file), the original
  autosave is kept as a copy and no frozen file is cleaned up, as in "The autosave can be read but some signals cannot be restored" below (user decision P-6 of
  2026-10-29). **A file that exists but cannot be read** (a CSV column renamed, no read permission, wrong format…) **also stays as a
  placeholder** (user decision of 2026-10-29; before, the redraw treated it as a read failure, removed it from the list with an error dialog, and the autosave written
  on close no longer had it, nor its Preprocess parameters): the Fmt column says "unreadable", the status bar's signal count says "(k with unreadable files)", and the
  notice (and the import warning) gives the reason for each one; the signals, derived signals, parameters and panel settings are kept and the autosave keeps
  recording them; once the file is fixed, any of the retries below loads it (a file with wrong content is only read again by the automatic retry after it has
  changed, so a large file is not re-read every 3 s; a file that cannot be opened — no permission, locked by another program — is retried every time). **Once the files are back they are loaded automatically**: every start retries; while DSV is open the files are checked
  every 3 s when "Preferences → Refresh automatically when the folder changes" is on (the folder panel's timer) and whenever the folder panel rescans; you can also
  right-click the list and choose "**Reload Signals with Missing Files**" (greyed out when there is no placeholder); dropping that file onto the window (or onto a
  panel) again, or naming it as a start-up argument, also reloads it right away (user decision of 2026-10-28; the status bar says "The dropped file is back: reloaded
  N signals (…)", followed by the usual drop sentence "… already plotted in P1 (selected)"; with a start-up argument the start-up retry has already loaded the
  file that is back, so the status bar says "The start-up argument's file is already plotted in P1 (selected)"). After loading, the derived signals are recomputed
  and everything is drawn back in its original panel (panel numbers and settings unchanged); the status bar says "Reloaded N signals (the files are back)" and also
  names the files that are still missing or exist but cannot be read (permissions, format) — those stay in the list. The frozen-file clean-up counts the data
  files referenced by placeholders as in use. A placeholder has no data: it is not exported to TXT (the status bar says so, counting "missing" and "unreadable" files separately; selecting a Preprocess result that waits for data says "the source file is missing" or "the source file cannot be read" accordingly), Extract Signals skips it and the analysis
  windows treat it as an empty signal; a copied-and-pasted placeholder is a placeholder too. **Opening this version's autosave with 0.9.12 (or older)** still skips
  the signals whose files are missing and drops them on close (known; the old version's rule).
  **A file that runs into trouble while DSV is open** (external disk unplugged, file moved or deleted, rewritten by another program into something that cannot be
  read, read permission removed): the data is still in memory and keeps being drawn and used (redraw, measurements, export and the analysis windows use the data in
  memory). When that signal has to be read again later — **changing its read format** (right-click "Read format" in the list, or "Read format" + "Apply" on the
  toolstrip or in the Signal Properties panel, for the selection or, with nothing selected, all signals) or ⌘Z / ⌘Y of that action, and **a redraw that finds the file
  changed** (any action that redraws, the folder panel's "Rescan") — and it cannot be read, it **stays in the list as a placeholder** just like at start-up above: Fmt
  "file missing" when the file is gone, "unreadable" (reason kept) when it is there but cannot be read; greyed out, not drawn; the derived signals built on it
  (I/Q magnitude / phase / FM, Preprocess results, whole chains) wait for the data, all parameters and panel settings are kept, and the autosave (and its identical
  backup) keeps recording them — **with or without derived signals**, no error dialog, nothing removed from the list. The status bar says it once: "The files of n
  signals are gone (…): they stay in the list as placeholders…" or "The files of n signals are there but cannot be read (…; reason): they stay in the list as
  placeholders…" (after the action's own sentence for ⌘Z, "Rescan", Despike and the like). Once the file is back or fixed (automatic refresh, right-click "Reload
  Signals with Missing Files", dropping the file in again, starting with it as an argument, rescanning the folder panel) it is read with the new read format, the
  derived signals are recomputed and everything is drawn back in its original panel (user decisions of 2026-10-29: P-5 at 18:1x for "file gone, with derived
  signals", the other cases — no derived signals, a file that is there but unreadable, found only on a redraw — at 22:5x; 0.9.14. In 0.9.12 / 0.9.13 the redraw
  failed with derived signals — an "Error" dialog, the list unchanged — and otherwise the signal counted as a read failure and was removed from the list together with
  its derived signals and Preprocess parameters, with an error dialog). **A file just added and never read yet** (drag and drop, the folder panel's "Add", the CSV
  import) that cannot be read is still not added ("Failed to read signals (removed from the list)"; a drop says "None of the dropped files could be read").
  **Copying a signal whose file is already gone (or cannot be read) and pasting it** gives a placeholder copy too (the status bar adds "(k files are already gone:
  pasted as placeholders…)", or the unreadable sentence; it is read once the file is back or fixed; in 0.9.12 / 0.9.13 the copy could not be read → "Failed to read
  signals (removed from the list)" followed by an "Error" dialog).
  **Extract Signals (ROI) from a signal whose file is already gone**: an extracted signal reads its range from the file, so it is **not extracted** and nothing is
  added to the list; the status bar says "The source files of 1 signals are gone, cannot extract (try again when the files are back): …"; a file that is there but
  cannot be read is treated the same way ("… cannot be read, cannot extract (try again when the files are fixed): … (reason)"); selecting a signal that is already a
  placeholder (greyed out, not drawn) gives the same explanation (first review round: it used to say "No displayed signals to extract"; with nothing selected, extracting
  all displayed signals still does not mention placeholders); the readable ones of the same
  selection are extracted as usual and the status bar adds which ones were not; extracting a derived signal still computes it from the source data in memory (user
  decision of 2026-10-29 22:5x, 0.9.14; in 0.9.12 / 0.9.13 a signal that could not be read was added, then "Failed to read signals (removed from the list)", while
  the status bar said "Extracted 1 signals").
- **The autosave was opened by an older version** (user decision of 2026-10-28, 0.9.13; since 0.9.14 every version keeps a backup of its own, user decision of
  2026-10-29): after every successful autosave write, an identical "written by this version" backup `~/.signal_viewer_last.backup-<version>.json` is written (for
  example `.signal_viewer_last.backup-0.9.14.json`; same folder as the autosave; it carries `app_version`; with "Auto-restore Last Session" unchecked the autosave holds
  only the preferences and so does the backup; a backup that cannot be written is only logged and never blocks closing).
  **One backup per version, the latest 3 versions kept**: after this version writes its own backup, the backups are ranked by version number (this version counts as
  one) and the backups of versions older than this one that are not among the latest 3 versions are deleted automatically (logged; while another DSV is open nothing is
  deleted that time — the next backup write looks again; "open" means registered in the frozen folder: a DSV that uses independent signals or whose start-up question
  asked about or listed any backup always registers (second review round, K1: it used to register only when another version's backups were listed, so when the question
  was about this version's own backup only and there was no frozen folder, a newer DSV closing meanwhile deleted it under "keep 3 versions" and Restore the Backup then
  restored the other DSV's autosave), a DSV with neither does not, and while only such a DSV is open the others delete as usual); the independent-signal data only
  they used is then cleaned up as usual. This version's own backup and the backups of newer versions are never deleted (with a newer, this and an older version used
  in turn all three stay); backups that cannot be read, whose version cannot be told or whose file-name version does not match their content (renamed or copied
  ones) are never deleted. The `.signal_viewer_last.backup.json` written by 0.9.13 is **only read, never written** by this version (0.9.13 decides C6 below by that
  file: if a newer version wrote it, 0.9.13 would stop keeping its own backup); it counts as the backup of the version written inside it (0.9.13) and takes part in
  "the latest 3 versions" like the others (user decision R3-D2 of 2026-10-29, replacing the 0.9.13 known issue "three versions used in turn": there used to be a single
  `.backup.json`, so after a newer version had been used the middle version kept no backup of its own, and once an even older version rewrote the autosave the
  signals added in the middle version could not be brought back).
  At the next start, when the autosave's `app_version` is older than a backup's (an older version was opened and closed in between: keys it does not know —
  Preprocess results and parameters, each panel's axis names / titles, the Eye Diagram and Error Rate defaults, the Sony / Apple interface theme — are dropped by it; a file without `app_version`
  counts as the oldest), DSV asks once before restoring: "**Restore the Backup** / **Use the Current File**" (a dialog drawn by DSV that shows which version wrote
  each file and when; the default, Esc and closing the window mean the current file). The backup it asks about is, among the backups that are **not newer than this
  version and newer than the autosave**, **the one from the most recent work** — the one saved last (the save time recorded in the backup, the one the question shows;
  when it is missing or cannot be read, the file's modification time, and the question says "file modified …"; within the same second the newer version wins), not the
  one with the newest version (user decision of 2026-10-29). Example: 0.9.14 used → 0.9.13 adds signals → 0.9.12 opened once → back in 0.9.14: the question offers
  0.9.13's backup (the signals added in 0.9.13 are in it; settings only 0.9.14 has may be missing) and says "the backup from the most recent work was written by version
  0.9.13 (time; newer than this version's own backup from time)". This version's own backup (saved earlier) is then shown in the question too (version, time, path):
  closing rewrites it, so **whichever you choose, a copy of it is saved automatically first** after you answer, `.signal_viewer_last.bad*.json` (the same way as R2-D2
  below: a notice once the main window is up and the status bar give the path, no frozen file is cleaned up while it exists, and opening it later with Import Settings
  brings back the settings only this version has; if the copy fails, it is not rewritten this time). When this version has no usable backup of its own yet (for example
  the first start of a new version while an even older version has rewritten the autosave) it is another version's backup (for example 0.9.13's `.backup.json`), and
  the question says so ("the newer backup was kept by version 0.9.13; this version has no usable backup of its own"). The other backups that are also newer than the
  autosave and not newer than this version are listed at the end of the question (version, time, path); open one with Import Settings to use it (this version does not
  rewrite them and does not delete them by the rule above while it stays open). **The same holds for the backup the question asks about**: if, say, it was kept by an
  old version outside the latest 3, it is not deleted while this session is open (first-round fix of 2026-10-30: it used to be deleted on the same close); it is deleted as
  usual at a later start without a question. Another DSV that closes meanwhile also sees this one and does not delete them that time (also a DSV without independent
  signals: when its question asks about or lists any backup it registers in the frozen folder).
  The backup restores the session kept in it (changes made after the old version was opened are not in it; if the backup cannot be read or applied at that moment —
  say another program damaged it while the question was open — the current autosave is restored instead and, once the main window is up, the status bar says
  "This version's backup cannot be read (…); restoring the current autosave instead" (for another version's backup: "The backup kept by version 0.9.13 cannot be
  read (…) …"), visible from 0.9.14 on); the current file restores the autosave as usual (the
  settings dropped by the old version do not come back); either way closing rewrites the autosave and this version's own backup (another version's backup that was
  asked about is not rewritten).
  With Use the Current File **the backup that was asked about is saved as a copy automatically**, `.signal_viewer_last.bad*.json` (same folder as the autosave; a
  notice once the main window is up and the status bar give the path; the name follows the U15 pattern below, so while it exists no frozen file is cleaned up and the
  data used only by the old backup stays too — open it later with Import Settings to get back the settings the old version dropped; if the copy fails, that backup is
  neither rewritten nor deleted this time) — no need to copy it yourself (user decision R2-D2 of 2026-10-29: the question used to tell you to copy the backup elsewhere
  first, but then the data used only by the old backup was cleaned up on this close, and importing that copy gave "file missing" for those signals). No question when
  there is no such backup, when either file cannot be read (an unreadable autosave follows U13 below) or when the autosave was written by this or a newer version;
  **nor when both files hold only preferences** (written with "Auto-restore Last Session" unchecked) — the current file is used (user decision of 2026-10-29;
  neither file has the Preprocess results or axis names the question talks about); when the most recent work saved only preferences while this version's own (earlier)
  backup holds a session, nothing is asked either, but a copy of this version's own backup is saved automatically first (as above: closing rewrites it; a notice
  at start says where the copy is and every close reminder lists it — user confirmed on 2026-10-30 to keep it this way).
  **A backup written by a newer version than this one** (for example 0.9.14 opened after 1.0.0 was used) is **neither asked about nor rewritten** by this version
  (this version is the older one); it restores the autosave as usual, and the next time the newer version starts it notices that an older version rewrote the
  autosave and asks whether to use its own backup, as above (user decision C6 of 2026-10-29; up to 0.9.13 the older version rewrote the backup too, so back in the
  newer version both files were written by the older one, nothing was asked and the newer version's settings were silently gone).
  **Closing the main window, ⌘Q (Windows: WM_CLOSE) or a termination signal while the question is open saves nothing**: the autosave, every backup and the frozen
  files stay untouched byte for byte, none is deleted, and the next start asks again (first review round of 2026-10-29: before, an empty session overwrote the
  autosave and the backup and then all frozen files were cleaned up); the same holds for closing before restoring the last session and opening the start-up
  arguments are done.
  **Files opened from Finder while the question is open** (double-click, Open With, drop on the Dock icon) **or dropped on the window are queued** and added by the
  drag-and-drop rules once the restore (question included) is done — the same as opening with arguments: the status bar adds "Dropped N signals into P…" after
  the restore sentence, ⌘Z undoes it; if you close while the question is open (nothing is saved) they are not added (user decision R2-D3 of 2026-10-29:
  before, they were added at once and then wiped out by the restore after you answered, so the file silently did not open).
  The frozen-file clean-up counts the data files referenced by **every** backup (each version's own, 0.9.13's `.backup.json`, those of newer versions) as in use
  (also with auto-restore off or when started with arguments); when any of them cannot be read nothing is cleaned up that time (logged; another version's backup is
  not copied, not noticed, not deleted and not changed). **When this version's own backup exists but cannot be read** (damaged, truncated, wrong structure),
  start-up keeps a copy as `.signal_viewer_last.bad*.json` as in U13 and shows a notice once; from then on U15 cleans up no frozen file at all (so the data files
  used only by that backup are not cleaned up after this close rewrites the backup); if the copy fails, the backup is not rewritten this time and nothing is cleaned
  up (first review round of 2026-10-29: before, closing rewrote the backup and then cleaned up the data files only it used). The backups' names do not match
  `.bad*.json`, so they never stall the clean-up; a folder with the same name in the way is left alone and nothing is cleaned up that time. When this version's own
  backup cannot be read, the question asks about another version's backup and you choose Use the Current File, the two parts ("the autosave backup kept by this version
  could not be read", copied to .bad.json, and "a copy of the old backup was saved") appear in the same notice and the status bar mentions both; when U13's Start Empty
  is chosen, "the last autosave could not be read, Start Empty was chosen (unreadable file: …)" is put in front of the notice's status line (decision of 2026-10-29
  23:0x "both parts must be visible", first fix round of 0.9.14).
  0.9.13 and older versions do not know the per-version backups: their clean-up counts only the autosave (0.9.13 also `.backup.json`), so **independent-signal data
  that only a newer version's backup still uses** (signals deleted in the old version, or deleted in a newer version and only remembered by its backup) is cleaned up
  by the old version the next time it starts, and choosing Restore the Backup back in a new version then shows that signal as "file missing" (the old version's own
  rule, which this version cannot change).
- The autosave and "Export Settings" are first written to a temporary file in the same folder and only replace the old file once complete (2026-10-26): if
  writing fails half way (full disk…) the old file is left untouched byte for byte and the temporary file is removed (before, the autosave was overwritten in
  place, a full disk truncated it to half a file, the next start showed nothing and the independent-signal data files it used were cleaned up afterwards).
  A failed export shows an error dialog. When the temporary file cannot even be created (**the folder cannot be written — even if the file itself can be**,
  full disk…), the old file is **never overwritten in place** either: the autosave asks as in the next item ("Close Anyway / Don't Close"), the export shows an
  error dialog, and the old file stays untouched byte for byte (round 10: before, a folder without permission fell back
  to overwriting the file in place, and a full disk then truncated the previous autosave to half a JSON). Both dialogs add a line "Folder that cannot be
  written: …" (the path as you see it; it fails even when the file itself is writable), and the export error gives a readable reason (Chinese / English) and
  says the existing file was not changed (round 11: before, they only said "no permission to write" with the autosave path, and the export showed the raw
  system message with a resolved path such as /private/tmp).
- **The autosave cannot be written while closing** (full disk, no permission…; 2026-10-26): the dialog "Autosave could not be written" says that the changes of
  this session have not been saved, with the autosave path and the reason, and lets you choose "**Close Anyway**" (the changes are not saved; the previous autosave
  stays untouched byte for byte and the next start restores it) or "**Don't Close**" (back to DSV: free some space or fix the permissions and close again; you can
  also save the session elsewhere with Export Settings first). The relaunch after changing the language in Preferences asks the same (Don't Close = no relaunch).
  This dialog is drawn by DSV itself (a system dialog cannot have these button labels). A termination signal (the restart after an update, `kill`) or a moment
  when no dialog can be shown (a system message box is already open) does not ask: DSV closes anyway, the previous autosave stays untouched and the log says so; a
  termination signal while the dialog is open counts as "Close Anyway", so the restart after an update is never blocked by it.
- **A reminder of unhandled files when closing** (user decision of 2026-10-30: "keep them, but say on every close where something is left to handle", including
  "files that pause the clean-up of data"): when you close DSV yourself (the window's close button, ⌘Q / the app menu's Quit; on Windows Alt+F4 and `taskkill /PID`),
  DSV **writes the autosave first** and then, if any of the following files exist, shows a small window "Some files still need your attention" with their locations;
  OK closes DSV, and nothing is shown when there are none. ① Images saved when copying the figure to the clipboard failed (`plotkit_clip_*.png` in the temp folder —
  Windows' `%TEMP%` and macOS' temp folder alike, user decision of 2026-10-30; on Windows a file whose pid has since been reused by another program is still recognised as left over);
  ② old backups saved aside and backups of unreadable autosaves (`.signal_viewer_last.bad*.json`: while one exists no standalone signal data file in the frozen folder
  is cleaned up, see U15 above); ③ version backups that cannot be read (while a `.signal_viewer_last.backup*.json` cannot be read the frozen clean-up stops); ④ backups whose
  copy aside is still owed (copying failed last time and again at this start: DSV neither rewrites nor deletes them until the copy succeeds, see F-R2D2N below). DSV never
  deletes these files itself and reminds you on every close until you deal with them (open a backup with Import Settings to check its signals, delete what you no longer need);
  each group lists at most 12 files, the rest is summed up as "… and N more (all in this folder)". Closing the main window while the start-up question (B3 / U13) is still open
  shows the reminder too (user decision C2-2 of 2026-10-31; that path still saves nothing and the notice says so).
  The window **closes by itself after 15 seconds** and DSV then closes (on Windows `taskkill /PID` cannot be told apart from the close button, and the program must not be
  impossible to close); when the autosave cannot be written, the question of the previous item comes first and the reminder follows only after "Close Anyway" (it then says plainly that this session's
  changes were not saved, instead of "the autosave has already been written"). A termination
  signal (the restart after an update, `kill`) and Ctrl+Break on Windows show no reminder and still save and exit within 2 seconds; neither does the relaunch after a language change.
  **Logging out, shutting down or restarting the system shows no reminder either** (user decision C2-4 of 2026-10-31): on macOS these arrive as a quit Apple Event from
  loginwindow that carries the reason, which DSV recognises — the autosave is written and DSV exits quickly without asking or reminding; ⌘Q / the app menu's Quit take another
  route (reminder as above), and the Dock icon's Quit is a quit Apple Event without a reason and counts as ⌘Q. On Windows, logging out, shutting down or restarting (including
  an automatic Windows Update restart) sends WM_QUERYENDSESSION and DSV writes the autosave and this version's backup first (no question, no reminder; Windows then ends the
  process) — the Windows builds of 0.9.12 / 0.9.13 did not handle that message, so a session left open at logout was lost entirely (second review round, W14R2-1).
- **The autosave cannot be read at start-up** (damaged or truncated by another program, wrong structure, no read permission, a missing link target…; 2026-10-26): DSV starts empty and, once the main
  window is up, shows a notice (it does not block anything) with the reason and where the backup is. A backup copy of that file is kept in the same folder:
  `.signal_viewer_last.bad.json`, or `.signal_viewer_last.bad-YYYYMMDD-HHMMSS.json` when that one exists — an older backup is never overwritten (the same
  damaged file is not copied twice; the file itself stays where it is until the next autosave replaces it). With **no read permission** the reason says "no
  permission to read" (it used to say "no permission to write"): the file cannot be copied, so it is renamed to the backup (there is no autosave at the original
  place any more) and keeps its permissions, so it still cannot be read; the notice says so and reminds you to fix its permissions (let your account read it)
  before opening it with Import Settings.
  **When a backup can be read** (user decision of 2026-10-29; since 0.9.14 the one saved last among the readable backups that are not newer than this version is chosen
  — the most recent work, picked as in B3 above; it is not necessarily this version's own `.signal_viewer_last.backup-<version>.json`, for example 0.9.13's
  `.backup.json`, and the question says which version kept it and when; when this version's own backup is not the one asked about it is shown too and a copy of it is
  saved automatically after you answer — and only when there is none of those, as in 0.9.13, a backup written by a newer version, again the one saved last): after keeping the copy DSV **asks right away "Restore the Backup / Start Empty"** (a dialog drawn by DSV, the same kind
  as B3 above: the default, Esc and closing the dialog mean Start Empty); the question gives the reason, where the copy is, which version wrote the backup and when,
  the other readable backups (open one with Import Settings; not deleted while DSV stays open — nor is the backup the question asks about) and the U15 rule below. Restore the Backup restores that backup and the status bar
  says where the unreadable autosave was saved; Start Empty (also the default, Enter, Esc and closing the question) starts empty as described here (closing rewrites the autosave and this version's backup with this
  session — when the question was about this version's own backup, copy it elsewhere first to keep it (no second notice); **when it was about another version's backup**
  (one not newer than this version; a backup kept by a newer version is already protected by C6 — this version neither rewrites nor deletes it — so it is not copied and
  there is no extra notice, user decision of 2026-10-30) this version does not rewrite it and **first copies it automatically** to `.signal_viewer_last.bad*.json` (user decision F-U13P of 2026-10-30, the same as
  Use the Current File in B3 above; the question says so beforehand): once the main window is open, a notice "The backup asked about was copied aside" appears once and
  the status bar gives the path (the "started empty as chosen" sentence stays too), every close reminder lists the copy, and it stays until you delete it — after "keep the
  latest 3 versions" deletes the original, the last work can still be opened with Import Settings, and while the copy exists U15 cleans up no frozen file; when copying
  fails the notice says "Copying aside the backup asked about failed", the original is not deleted while DSV stays open and copying is tried again before each autosave
  (if it keeps failing until DSV is closed, the debt is recorded next to the autosave in `.signal_viewer_last.pending-aside.json`; **the next start copies first** and only
  then rewrites or prunes that backup, and if copying fails again the notice "The owed backup copy failed again" appears and the backup is left alone — the same after
  Use the Current File in B3 and for this version's own older backup; user decision F-R2D2N of 2026-10-30; before, the debt lived only in memory and the next start without a
  question deleted or rewrote the backup). Restore the Backup makes no copy (the backup's content becomes this
  session). This version's own backup, when it is listed, is then copied automatically as above, both in one notice; the unreadable autosave has already been kept as .bad,
  so U15 cleans up no frozen file and the copied backup imports with its data). **When the backup was written by a newer version**, this version does not rewrite it (C6) and the question says so: "this version does
  not rewrite it", "closing this time rewrites only the autosave", and after Restore the Backup the status bar says "restored the last session from
  the backup written by version X, newer than this one" (third review round of 2026-10-29: it used to say the backup was written together with this
  version's last autosave and would be rewritten). While the list holds placeholders (files missing or unreadable), the status bar ends with the "The source files
  of … signals are missing" sentence; which backup was used and where the unreadable autosave was saved are in the question and the notice.
  The backup is not rewritten before you answer; closing while the question is open saves nothing (as above).
  **As long as any backup exists next to the autosave, no independent signal's data file in the frozen folder is cleaned up automatically**
  (backups = `.signal_viewer_last.bad*.json`, copies or renamed ones you made count too; whether anything uses it or not; 2026-10-26, decision U15 — a
  damaged file may be cut off before "signals" or be all NUL bytes, so it cannot tell which files the last session used), and the notice says exactly that;
  to get the last signals back, repair the backup and open it with Import Settings — **import it first and check that the signals are back before deleting the backups**
  (once the backups are deleted, data files used only by them are cleaned up; a backup moved to another folder or renamed so that it no longer matches the
  pattern does not count either; the notice says so since round 11); when you no longer need them, delete **all** the backups — only then does the
  automatic clean-up of unused files resume.
  **JSON that parses but has the wrong structure** (e.g. "view" is not an object, "signals" is not a list, "version" is not an integer, or applying it fails half
  way) counts as unreadable too: the notice says what is wrong, a backup is kept and DSV starts empty (round 11: before, it was only logged with no notice, and
  with a wrong "view" closing overwrote the whole file and then cleaned up the data files the last session used — the data was lost for good).
  **The autosave can be read but some signals cannot be restored** (a field of the wrong type, e.g. "panel" is text or null, "dk" / "lw" is text; "key" is
  missing; a derived signal's sources were not restored; a missing file no longer counts since 0.9.13 — the signal stays in the list as a placeholder, see the next item) and they use independent signals' data files that no restored signal uses
  (2026-10-26, round 12, following U13 / U15): **the other signals are restored as usual**; once the main window is up a notice "Some signals of the last session
  were not restored" (it does not block anything) lists them with the reason (e.g. `the settings file's "signals[].panel" is not an integer`) and where the
  backup is; a backup copy of the original autosave is kept as above (`.signal_viewer_last.bad.json`, identical byte for byte), and **while the backup exists no
  data file in the frozen folder is cleaned up** (U15); to get those signals back, repair the backup and open it with Import Settings (the data comes back bit
  for bit), and check that they are back before deleting the backup. Before, they were skipped silently at start-up, the new autosave written when closing no
  longer recorded them and the clean-up that followed deleted their data files — the data was lost for good (all independent signals of the session at once when
  every entry was like that). If no backup can be made (the folder cannot be written), the notice says so: no data file is cleaned up while DSV stays open, and
  closing tries the backup again and, if that still fails, asks as in "The autosave cannot be written while closing" above without overwriting the original
  autosave. Ordinary files (CSV…) that are missing: since 0.9.13 the signal stays in the list as a placeholder and a notice is shown (next item; up to 0.9.12 they were skipped silently).
  **When the autosave records the path of an independent signal's data file that belongs to another account or computer** (a new computer, a different user
  name) and this computer's frozen folder has a file with the same name whose content matches the hash in its name, that file is used to restore it (no notice;
  the clean-up already went by file name, so that file always counted as used); a file with the same name but different content is not used — since 0.9.13 that
  signal stays in the list as a placeholder (see "Opening while a source file is temporarily missing").
  **An autosave that is a symbolic link whose target is missing** (an external or network disk not connected…) counts as unreadable too: the notice says where
  the link points, **the link itself is renamed to the backup** (it still points to that file, which is not touched), and closing writes a new autosave at the
  original place; once that file is back, open the backup with Import Settings to get the signals back (round 11: before, it counted as "no autosave", start-up
  deleted every data file the last session used, and if the file came back before closing it was overwritten through the link).
  If no backup can be made (the folder cannot be written), the damaged file stays where it is and DSV does not overwrite it
  (closing asks as in the previous item); once the folder is writable again, closing or restarting makes the backup first. When DSV was started with
  a root folder (the autosave is not read) or the autosave was damaged by another program while DSV was running, the backup is likewise made before
  the new autosave is written (no notice, written to the log; while that backup exists nothing is cleaned up either — delete it when it is not needed).
- The log is written to `~/signal_viewer.log`; an exception in a button pops up an error window directly and is written to the log.
- **Home → Help → Diagnostics** window: environment info, each signal's parameters, keyboard input test, the last 25 action records; one click copies everything to the clipboard.

## Feature Overview
Multi-file / multi-column overlay, plotting in separate panels, SPS and offset alignment, difference highlighting and jumping, despike, crosshair,
Spectrum (Welch), GFSK discriminator, Export TXT, settings export / import and auto-restore, search-filtered file tree, in-place list editing,
click lines on the plot to change color / line width / line style, copy to a figure window to overlay (v3.2).

## Garbled Characters
If Chinese text shows up garbled in the Windows Command Prompt, run this first:

```
chcp 65001
```

then run `python signal_viewer.py`. The packaged exe (`--windowed`) has no console and is not affected.
Running inside a Spyder / IPython kernel shows a red warning; please press "Relaunch Standalone".

## Language
- The UI defaults to Traditional Chinese and is also available in English. Switch it with **Home → Environment → Preferences → General → Language**; the choice is stored in the settings file (`view.lang`) and takes full effect **after the program is restarted** (as in MATLAB; pressing OK, also after Apply, offers to restart right away). On macOS ⌘, also opens Preferences.
  The language is a preference of this computer: importing someone else's settings file does not change it.
- Command line `python signal_viewer.py --lang en`, or environment variable `DSV_LANG=en` (precedence: `--lang`, then `DSV_LANG`, then `view.lang` in the auto-saved settings, then Chinese).
  It applies to this run only; **when files are given as arguments** (`python signal_viewer.py --lang en a.csv`) this language is also stored as the preference
  and used next time (as in 0.9.12; user decision of 2026-10-29). Only an explicit `--lang` or `DSV_LANG` overrides the restored preference: with file arguments
  and no language given, the restored preference stays — the backup's language when "Restore the Backup" was chosen at start-up (user decision of 2026-10-29).
- With the English UI the Help window reads `README.en.md` (falling back to `README.md`); `build_exe.bat` / `build_mac.sh` bundle both READMEs with `--add-data`.
- The catalogs live in `plotkit/i18n_en*.py`; the mechanism is described in the "Language (plotkit.i18n)" section of `docs/plotkit.md`.

## Known Issues (open)
Known when 0.9.10 / 0.9.11 were released and deferred by the user (menu decisions of 2026-10-26 to 10-28; none of them is a 0.9.9 feature broken in 0.9.10;
0.9.11 fixed four everyday items; 0.9.13 fixed the four that could lose data: a source file temporarily missing, opening with arguments, an autosave rewritten by
an old version, and Preprocess results that could not be computed, see "Settings and Auto-restore" and "Plotted Signals table"). The two items found in the
0.9.13 review and not fixed in 0.9.13 are both fixed in 0.9.14 (a source file disappearing while derived signals are open — it now stays as a placeholder,
see "Opening while a source file is temporarily missing"; the backup when three versions are used in turn — now one backup per version, see "The autosave was
opened by an older version" under "Settings and Auto-restore"). None of these loses data:
- **Geometry differences that come with the UI font now being the designed 12 px** (the user chose A on 2026-10-25; in 0.9.9 the UI font settings mostly did not take
  effect and the system default font was used): the toolstrip is a little shorter and the plot canvas a little taller (681 → 684 px measured on the same Mac with the same
  window), so the default size of Save Figure As… (= the current canvas size) differs from 0.9.9 by a few pixels and the automatic range of the constellation plot (equal
  axis scaling) differs slightly; the signal data and exports at a given size (for example 10 × 6 in) are identical to 0.9.9. On 2026-10-27 the user listed this as known
  and deferred it to 0.9.11.
- Spectrum window: with the toolstrip collapsed by hand (double-click a tab) an invalid field gets no "expand the toolstrip to change it" hint, and clicking a tab while
  collapsed does not expand it temporarily (batch 3 B3, P3); the English status sentence "Computed 1 spectra" (B6, P3).
- Packaging (`build_mac.sh`) does not yet write the commit / push / build times into `VERSION_LOG.md` automatically; it is written by hand at release time.
- Windows: after you dragged a sash yourself (or one was restored from the saved layout), shrinking the window a lot can squeeze the plot cell to 0 px behind the
  Measurements panel in the same column (it comes back when the window grows; same in 0.9.13) — kept as is per the 2026-10-31 decision "a sash you drag yourself is not
  moved back" (2026-11-01).
- Windows: paths longer than 260 characters cannot be opened (when Windows has LongPathsEnabled off) and the message says "not recognised or unreadable" / "file missing";
  no data is lost (the autosave records the signal, which stays as a placeholder; move the file to a shorter path and drop it again). Not handled in 1.0.0 yet; deferred to a later version (decided 2026-11-01).
- Interface themes (deferred past 1.0.0, decided 2026-11-01): in the default 1600 px wide window on macOS the View tab's Layout and Appearance sections do not fit and
  are not shown at all (same in 0.9.14); with a window 2029–2108 px wide (2453–2516 px in the English UI) the 1.0.0 Appearance section is also collapsed (the cost of the
  wider theme drop-down; the new width is kept by decision). To change the theme use Preferences ▸ Appearance ▸ Theme, which is always visible.
- Interface themes: a drop-down list that was already opened before you change the theme (including the theme drop-down itself) keeps the old theme's colours (for
  example the dark theme's black list with a MATLAB-blue selection); the selection colour of an unfocused text box behaves the same. Switching from Dark to Light in
  0.9.14 does the same; it is only colour and does not affect data. Reopening that window shows the new theme's colours (for the main window's drop-downs, quit and
  start the program again). Deferred past 1.0.0 (decided 2026-11-01).

## Version Number and Relaunch After Update
- Version **x.y.z** (`APP_VERSION` in `signal_viewer.py`; used by the window title, the settings file's `app_version`, the Windows exe file version and the macOS
  app's CFBundleShortVersionString): every small change bumps **z** (`python3 tools/bump_version.py patch`); **x / y** change only when the user calls for a major /
  minor release (`major` / `minor`; `--set 0.9.1` also works). Counting starts at **0.9.1** on 2026-10-23.
- **Automatic relaunch after an update** (macOS): after `bash build_mac.sh` packages and publishes to `/Users/Shared/DSV-latest`, it runs `tools/relaunch_mac.sh`:
  the running SignalViewer.app gets SIGTERM — the program **autosaves first, then closes** (same as ⌘Q; "Restore last session" brings the signals, layout and
  x range back on the next start) — and once it has exited the same .app is reopened with `open` (DSV-latest if that path is gone). Nothing happens when it is not
  running (`--always` opens it anyway); `NO_RELAUNCH=1 bash build_mac.sh` skips the relaunch. `kill <pid>` is the same clean shutdown.
  On SIGTERM the program **saves right away** and then closes, and a wake-up pipe makes an idle Tk loop handle it immediately (from 0.9.5; earlier versions could be slowed down
  by macOS App Nap after sitting in the background with the display asleep, and once did not respond within 15 s, were force-quit and did not save). The relaunch script waits up to 60 s before forcing.
  A termination signal never asks "Close Anyway / Don't Close": when the autosave cannot be written (full disk) DSV closes anyway, the previous autosave stays
  untouched and the log says so; when that dialog or the notice about an unreadable autosave is open, a termination signal still ends DSV within the time limit
  (2026-10-26).
- **Windows** (0.9.13, compatibility check W6): Windows has no SIGTERM. `taskkill /PID <pid>` (without `/F`) sends WM_CLOSE = the window's × button: autosave first, then close
  (needs a logged-in desktop; in a session without one — scheduled task, service — taskkill answers that the process can only be terminated forcefully, measured 2026-10-28;
  DSV itself handles WM_CLOSE the same way, save then close within 0.3 s; WM_CLOSE cannot be told apart from the × button, so when there are unhandled files the
  autosave is still written first, then the reminder "Some files still need your attention" appears and closes by itself after 15 seconds, and the program exits —
  see "Settings and Auto-restore"); **logging out, shutting down or restarting** (including an automatic Windows Update restart): Windows sends WM_QUERYENDSESSION and Tk
  calls the WM_SAVE_YOURSELF handler DSV registers — the autosave and this version's backup are written first, nothing is asked or shown, and Windows then ends the process
  (0.9.12 / 0.9.13 did not handle it: a session left open at logout was lost; decision of 2026-10-31, second review round W14R2-1);
  **The single-file exe (the default onefile build of `build_exe.bat`) runs as two processes named `SignalViewer.exe`**: the first is PyInstaller's launcher (it unpacks; it has no window) and the real program is its child (the one with the window). `taskkill /PID <launcher>` (without `/F`) answers SUCCESS but the program stays open and nothing is saved (the launcher has no window to receive WM_CLOSE); send it to the child instead: `taskkill /PID <child>` — it saves, closes, and the launcher exits too (about 1.3 s); naming both PIDs in one taskkill works the same (measured on the user's PC on 2026-10-30). To find the child, in PowerShell: `Get-CimInstance Win32_Process -Filter "Name='SignalViewer.exe'" | Select-Object ProcessId, ParentProcessId` — it is the one whose ParentProcessId is the other SignalViewer.exe;
  when run from a console (`python signal_viewer.py`), **Ctrl+Break** (or another program sending `CTRL_BREAK_EVENT`; DSV must be in its own process group) also saves first and
  then closes (SIGBREAK shares the SIGTERM handler); an empty 250 ms timer wakes the idle event loop, so a signal is handled within 0.25 s at the latest. `taskkill /F` kills
  without saving. There is no `tools/relaunch_win` yet (close and reopen the exe yourself after an update).

## Packaging
```
pip install pyinstaller
build_exe.bat            # single file: dist\SignalViewer.exe
build_exe.bat onedir     # folder version: dist\SignalViewer\SignalViewer.exe (starts faster)
```
`build_exe.bat` adds `--add-data README.md;.` and `--add-data README.en.md;.` (for the Help window) and excludes PyQt5 / PyQt6 / PySide2 / PySide6 / IPython / scipy / pandas.
`build_exe.bat` first runs `python tools\make_version_file.py build_version_info.txt`, which writes a PyInstaller version file from `APP_VERSION` in
`signal_viewer.py`, and passes it with `--version-file`: Explorer's Properties → Details shows File version / Product version = APP_VERSION and the product name
Digital Signal Viewer (company name left empty).
The `plotkit/` package is bundled automatically by PyInstaller (the script also adds `--hidden-import plotkit` to be safe); it does not need to be placed next to the exe.
The onefile exe unpacks itself to a temporary folder on every start: 10–20 seconds the first time (matplotlib also builds its font cache), and about 8 seconds before the window appears after that, measured on the user's PC on 2026-10-30 (this used to say "after that it is fast", which is not true); use the folder build (`build_exe.bat onedir`) for faster starts. Defender / SmartScreen may also make you wait a little for an unsigned exe.
**High DPI on Windows** (since 0.9.13, user decision W10 of 2026-10-29; verified and completed in 0.9.14 on the user's PC — 175%, portrait 1080×1920): the program
declares itself per-monitor DPI aware at start-up (Help → Diagnostics shows `dpi_awareness=per-monitor-v2`); Tk's scaling follows the screen (175% → 2.33, 168 dpi),
the UI text and sizes grow with it and the plots are drawn with the screen's real pixels (device_pixel_ratio 1.75), so text and lines are sharp (before, Windows
scaled the whole window up as a bitmap, which looked blurry). The start size of the main window, the analysis windows (spectrum, AM/PM/FM, constellation, GFSK,
eye diagram, error rate), Help, Diagnostics and figure windows grows with the scaling but never exceeds the work area (the screen minus the taskbar; 95% of the
width, 90% of the height); the first time a window appears its whole frame (title bar included) is moved into the work area (a dialog wider than the screen,
such as Preferences, is narrowed to the screen so its OK / Cancel buttons are visible); the main window's minimum size never exceeds the screen. **When the screen
cannot hold the macOS minimum width** (a 175% portrait 1080 px screen is only 617 points wide; the main window is 1026 px): the toolstrip tabs become narrow
(and scroll left / right with ◀ ▶ at both ends if they still do not fit; the selected tab is always scrolled into view); a tab whose content is wider than the window
gets ◀ ▶ scroll buttons at both ends (the mouse wheel over the toolstrip buttons scrolls too) — before, the MEASUREMENTS / VIEWS / EXPORT tabs and the HELP section
on the right were simply cut off and could not be clicked; the parameter rows at the top of the analysis windows wrap onto more lines (the window grows taller).
When everything fits, nothing changes. macOS is not affected (all of this is on for Windows only).
0.9.14 also fixes three problems that appeared once DPI awareness was declared (already in 0.9.13 on a 175% screen; measured on the user's PC on 2026-10-29): the main figure was drawn 1.75 times larger than its canvas, so only the top one or two panels were visible and the right side was cut off — the figure now fills the canvas exactly and each panel has the same height in inches as in 0.9.12; mouse positions on the plot were converted with a 1.75× error (which panel a drop lands on, the × at a panel's top left, the selection frame, whether the wheel is over an axes or a margin, scrolling to a panel) — they now use the real pixels; the first time the data-cursor readout appeared in the right column, the plot column in the middle was squeezed to nothing and the whole plot vanished (closing the cursors did not bring it back) — on Windows the plot column now keeps at least 45% of the dock width (also when the window gets narrower). macOS is unchanged in all three (one point is one pixel in TkAgg on macOS).
First fix round of 0.9.14: at 1920×1080 and 175% (the default of many laptops), opening the data cursors while the Measurements panel was open made the panel's toolbar
wrap and grow, and the measurement table in the same column squeezed the plot out of sight (closing the cursors did not bring it back) — on Windows the plot now keeps at
least 160 px (scaled with the DPI, at most half the column; checked after each re-layout — a panel shown, hidden or collapsed, the data-cursor readout panel appearing —
and, when the window size changes, only if you have not dragged the sash yourself: a sash you dragged (or one restored from the saved layout) stays where you put it until the
next re-layout — user decision of 2026-10-31; the first fix round also pushed it back on every resize. A sash restored from the saved layout: since 0.9.14 the layout
records the DPI scale it was saved at; when that scale equals the current one the sash is restored exactly where it was saved (70 px saved at 100 % stays 70 px when
reopened at 100 %, as in 0.9.13), and only a different scale (the display scaling changed) or a layout without a recorded scale (saved before 0.9.14) triggers one
minimum-height check after the layout is applied);
running `python -m plotkit figure.json` or `python -m plotkit --demo` on its own now declares per-monitor DPI awareness like DSV (user decision of 2026-10-30; before,
such a window was scaled up by Windows as a bitmap and looked blurry). macOS is not affected.
On Windows, when the `--selftest` output is redirected to a file or run over ssh, the program automatically rewrites characters that cannot be encoded in cp950 as escapes instead of aborting.
For an ordinary Windows user (no "create symbolic links" privilege, Developer Mode off), `--selftest` reports the two round-11 checks "the autosave is a symbolic link" as
skipped and still prints `SELFTEST OK` with exit code 0 (measured 2026-10-29 on the user's desktop with both Python and `SignalViewer.exe`; before, the whole round 11
ended with an exception); macOS / Linux can always create symbolic links, so those two checks always run there (being unable to create one counts as a failure).
Tested 2026-10-21 on the user's Windows 11 desktop: `build_exe.bat` produced a 38.7 MB `dist\SignalViewer.exe`; `SignalViewer.exe --selftest` passed completely and the GUI started normally (details in `docs/windows-checklist.md`).
The bundle does not include `tests/matlab_ref` (the MATLAB reference data, 15 MB): the `--selftest` checks that compare against it are skipped in the exe / .app
(they print "no tests/matlab_ref/…: skipped"), everything else runs; the 0.9.12 exe crashed in the error-rate part because the reference file was missing
(a windowed exe shows an error box and never exits) — fixed in 0.9.13 (Windows compatibility check W2, 2026-10-28).

macOS can also be packaged into a double-clickable `dist/SignalViewer.app`:

```
bash build_mac.sh            # onedir (recommended, starts fast)
bash build_mac.sh onefile    # single file; the first start has to unpack
```

The script uses anaconda's Python (Tk 8.6) to create `.venv-build/` inside the project; numpy / matplotlib / PyInstaller are all installed there, leaving anaconda and the system untouched.
The `.app` **is code-signed** (`build_mac.sh` re-signs it after writing the version into Info.plist: when the project has `.signing/` — the dedicated keychain and the local self-signed certificate "DSV Local Code Signing" created by `tools/make_signing_keychain.sh` — it signs with that certificate, whose designated requirement is identifier + certificate, so macOS recognises every rebuild as the same app and does not ask for the "Documents" and similar permissions again; without `.signing/` it falls back to an ad-hoc signature (`codesign -s -`); either way `codesign --verify --deep` checks the result). Neither is an Apple developer certificate and the app is not notarised: one built on the same Mac opens directly; to run it on another Mac you still have to allow it in "System Settings → Privacy & Security" or run `xattr -dr com.apple.quarantine SignalViewer.app`.

## Trademarks and Non-affiliation

- MATLAB is a registered trademark of The MathWorks, Inc.
- Sony, PlayStation, α, Apple, macOS, watchOS and other names mentioned here are trademarks of their respective owners.
- The appearance themes (MATLAB dark / light, Sony-style, Apple-style) only use those colour styles as a reference: this project is not affiliated with,
  endorsed or sponsored by any of these companies, and uses none of their assets (icons, fonts, images or code).
