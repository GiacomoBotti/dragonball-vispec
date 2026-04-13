#!/usr/bin/env python3
"""
Flying Nimbus GUI

- Imports and runs `flying_nimbus_core.py` 

How to run (dev option):
  pip install PyQt6 numpy matplotlib
  python flying_nimbus_gui.py
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional
import csv
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.ticker import MultipleLocator, AutoMinorLocator, AutoLocator

ASCII_BANNER = r"""
                                  %
                                %%%%%
                               %%%%%##%       %%
                                %%%#%#*#%      %
                                %%%%%***+*#%    %
                                 %%%%#*++++##   %%
                                  %%%%%*+--=+#%  %
                                  %%%%%#*---=*#% %
                 %%#####****##%    %%%%%%+=;;=+# %
             %%%#######**+++++##%  %%%%%%*+--==*%
          %%%%%%%%%####*++++++++### %%%%%#*==---##
      %%%%%%%%%%%####*++++===+++++*#%%%%%%#*****%%##%
     %%%%%%%%%%%%####*++++===++++**#%%%%%%%%%%%%%%%%%%%
          %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            %%%%%%%%%%%%%%%%%%%%%%%%%%%#%%%%%%%%%%%%%%%%%%%
                 %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
           %%%###%%%%%%%%%%%%%**=*+=-:;*#*+-;:,,::;=##**++*#%%%##########%%%%%%%
         %%%%%%%%%%%%%%%%%%%%%*+--;-;,;**-;:....::-+=-=+####%%%%%%%%%%%%%
         %%%%%%%%%%%%%%%%%#*##*=-;::,,:==;:.....::=--==+*###%%%##%%%%%
                   %%%%%%#+=+++=-;:,,,:::.. ...,,,,.,:-++++**%%%%%####
                 %%%%%%%%#=-;=+=-;:,,,::.    ,:::;...,-=+=;++###**#%%%%%
                %%%%%%%%%#=;;;==-;:,,-+:.    ,:==:..,,:--;;++%%%%#####%%%%
                        ##+==;----;,,:;:.....,:--:. ..:;:;-+*%%%
                     #####+===-----:,,,,.,,..,:::,.. .:;;-=+#%%%
                 %###***###****++=-::..,::::::,,....,:;;;-+#%%%%%
                 #%####***######++=::..::::::::.  .,::---+=      ==;::
               %%     ####  ######*=;::,::::::,,...:++==;=+    *=:,...;;
                          ########*==::::::,::,...,:*+==-+=*#**+-::,..;:
                        ########***++=-;;:,,,:,.:,:-+==+=++##**=-;:.. ;:
                      %##*++*##*+*+**+=-;::::,::,:;;+====++###*=-;,.,.--
                      %##*+=-=+++=+*+++=-;;;;::,:;=+====+++####*==;;;;;-
                     %#*==-;;;----=++==--;::,,:;--===++++*##%####
                     #=--;::,:::;-=+=----;;;::---==+++**
                   #*=;;-;;:..,,:;-----===-;;-==++**#
                  *=;=++++-;;;;;:--=====+=++++**+
                #=;=***+=;::,,:;-=+*#*###++**#=--=+*+***
               #;:;-***=++**++*+*+**=++***+****=--====+++**
              #;:;=+*###**++*####*=-=--=+*##+**=-==-==---=+
               #*++*#*###*#**##+*=--=+++++=-+***+##********
             #*=----====+++=+==++            **++=-;-:;=-
            ##*+=--====+++=+====+*            ++=--;==
         ......................+*=.......---=.......+#
      #.......:++*-=........=:::+*+.................:....#
    #...........-.................+=....=*-...............
  #............=...:**...................+*.............*##
 =......:....::..+:......................*=...............:
 =.=.....................................*-................#
 .--..........:.............**=......++-*:.......................#######.....##
  #**#=......+:..:=:........:.:.-=:...*****=*....:=::*+.*=............:=+*####*-
    #**#****:.......+++:..........**=.*****+=..*********##%############       #
     %+****..........=...........*+**-******+-=******+@*@
     #@#*++......................*******************+%@#
        ###-=...............****+*******%***%%#***#%@#
            ##*+--+........+**********+%%%++*%%@####
              #####**-::=+*+#%%@***++*@%%%@@@@@#
                   ##*****%@%@@@@@%@@@@@#####
                      -#%%%#+#   #---#
           ██████╗ ██╗     ██╗   ██╗██╗███╗   ██╗ ██████╗
           ██╔═══╝ ██║     ╚██╗ ██╔╝██║████╗  ██║██╔════╝
           █████╗  ██║      ╚████╔╝ ██║██╔██╗ ██║██║  ███╗
           ██╔══╝  ██║       ╚██╔╝  ██║██║╚██╗██║██║   ██║
           ██║     ███████╗   ██║   ██║██║ ╚████║╚██████╔╝
           ╚═╝     ╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝

           ██╗  ██╗   ███╗   ███╗██████╗ ██╗   ██╗███████╗
           ██║  ██║   ████╗ ████║██╔══██╗██║   ██║██╔════╝
           ██║  ██║   ██╔████╔██║██████╔╝██║   ██║███████╗
           ██║ ██╔╝   ██║╚██╔╝██║██╔══██╗██║   ██║╚════██║
           ████╔═╝▀▀  ██║ ╚═╝ ██║██████╔╝╚██████╔╝███████║
           ╚═══╝  ██  ╚═╝     ╚═╝╚═════╝  ╚═════╝ ╚═════
"""
# ---- Qt (PyQt6) ----
try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except Exception as e:
    print("PyQt6 not found. Install with: pip install PyQt6", file=sys.stderr)
    raise

# ---- Nimbus core (must be next to this file) ----
try:
    import flying_nimbus_core as nimbus
except Exception as e:
    print("Could not import flying_nimbus_core.py. Put it next to this GUI.", file=sys.stderr)
    raise


# ---------------------------
# Utilities
# ---------------------------
def parse_int_list(text: str) -> list[int]:
    s = (text or "").strip()
    if not s:
        return []
    out: list[int] = []
    for tok in s.replace(",", " ").split():
        out.append(int(tok))
    return out


def parse_range_list(text: str) -> list[int]:
    s = (text or "").strip()
    if not s:
        return []
    out: list[int] = []
    for tok in re.split(r"[\s,]+", s):
        if not tok:
            continue
        m = re.fullmatch(r"(\d+)(?:\s*(?:-|\.\.|:)\s*(\d+))?", tok)
        if not m:
            raise ValueError(f"Invalid range token: {tok}")
        start = int(m.group(1))
        end = m.group(2)
        if end is None:
            out.append(start)
            continue
        stop = int(end)
        step = 1 if stop >= start else -1
        out.extend(range(start, stop + step, step))
    return out


def normalize_sep(sep: str) -> str:
    sep = (sep or ",").strip()
    if sep.lower() in ("tab", "\\t", "t"):
        return "\t"
    return sep


def safe_read_nat_from_xyz(path_text: str) -> int:
    ptxt = (path_text or "").strip()
    if not ptxt:
        return 0
    p = Path(ptxt).expanduser()
    if not p.is_file():
        return 0
    fn = getattr(nimbus, "read_nat_from_xyz", None)
    if callable(fn):
        return int(fn(str(p)))
    # fallback
    lines = p.read_text().splitlines()
    return int(lines[0].split()[0])


def ensure_cnorm_path(text: str) -> str:
    s = (text or "").strip()
    if not s or s == ".":
        return "cnorm.dat"
    return s


def open_in_file_manager(path: Path) -> None:
    path = path.expanduser().resolve()
    url = QtCore.QUrl.fromLocalFile(str(path))
    QtGui.QDesktopServices.openUrl(url)


# ---------------------------
# Clickable label + collapsible sections
# ---------------------------
class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        self.clicked.emit()
        super().mousePressEvent(e)


class CollapsibleSection(QtWidgets.QWidget):
    """header button + content"""

    def __init__(self, title: str, parent=None, expanded: bool = True):
        super().__init__(parent)
        self._expanded = expanded

        self.btn = QtWidgets.QToolButton(text=title)
        self.btn.setCheckable(True)
        self.btn.setChecked(expanded)
        self.btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)
        self.btn.clicked.connect(self._toggle)

        self.content = QtWidgets.QWidget()
        self.content.setVisible(expanded)
        self.content_lay = QtWidgets.QVBoxLayout(self.content)
        self.content_lay.setContentsMargins(10, 8, 10, 10)
        self.content_lay.setSpacing(10)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self.btn)
        lay.addWidget(self.content)

    def _toggle(self):
        self._expanded = self.btn.isChecked()
        self.btn.setArrowType(QtCore.Qt.ArrowType.DownArrow if self._expanded else QtCore.Qt.ArrowType.RightArrow)
        self.content.setVisible(self._expanded)

class AsciiSplash(QtWidgets.QWidget):
    splashClosed = QtCore.pyqtSignal()

    def __init__(self, text: str):
        flags = (
            QtCore.Qt.WindowType.SplashScreen
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(None, flags)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.lbl = QtWidgets.QLabel()
        self.lbl.setText(text)
        self.lbl.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.lbl.setWordWrap(False)

        fixed = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.lbl.setFont(fixed)
        self.lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.lbl.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        screens = QtGui.QGuiApplication.screens()
        if screens:
            g = screens[0].geometry()
            for s in screens[1:]:
                g = g.united(s.geometry())
        else:
            g = QtCore.QRect(0, 0, 1400, 900)
        self.setGeometry(g)

        lines = text.splitlines() or [""]
        fm = QtGui.QFontMetrics(fixed)
        text_w = max(fm.horizontalAdvance(line) for line in lines)
        text_h = fm.lineSpacing() * len(lines)

        h_align = QtCore.Qt.AlignmentFlag.AlignHCenter if text_w <= g.width() else QtCore.Qt.AlignmentFlag.AlignLeft
        v_align = QtCore.Qt.AlignmentFlag.AlignVCenter if text_h <= g.height() else QtCore.Qt.AlignmentFlag.AlignTop

        if text_w <= g.width() and text_h <= g.height():
            self.lbl.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        else:
            self.lbl.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        lay.addWidget(self.lbl, 1, h_align | v_align)

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        self.close()

    def closeEvent(self, ev: QtGui.QCloseEvent):
        try:
            self.splashClosed.emit()
        finally:
            super().closeEvent(ev)

class SeriesNameEditDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        ed = super().createEditor(parent, option, index)
        if isinstance(ed, QtWidgets.QLineEdit):
            ed.setStyleSheet(
                "background: #0f172a; color: #e5e7eb; selection-background-color: #2563eb; selection-color: #ffffff; padding: 0px 6px;"
            )
        return ed

    def updateEditorGeometry(self, editor, option, index):
        r = QtCore.QRect(option.rect)
        if index.column() == 0:
            shift = 28
            r.setX(r.x() + shift)
            r.setWidth(max(10, r.width() - shift))
        editor.setGeometry(r)



# ---------------------------
# Pop-out spectrum window
# ---------------------------
class SpectrumPopoutWindow(QtWidgets.QMainWindow):
    """Large detached window that mirrors the Results plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Flying Nimbus — Spectrum")
        self.resize(1200, 800)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        lay = QtWidgets.QVBoxLayout(central)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self.fig = Figure(figsize=(10, 7), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.nav = NavigationToolbar(self.canvas, self)

        lay.addWidget(self.nav)
        lay.addWidget(self.canvas, 1)

    def refresh(self, draw_fn):
        """draw_fn(ax) should clear + draw the plot."""
        draw_fn(self.ax)
        self.canvas.draw_idle()

# ---------------------------
# Core
# ---------------------------
class _QtStream:
    def __init__(self, emit_fn):
        self.emit_fn = emit_fn

    def write(self, s: str):
        if s:
            self.emit_fn(s)

    def flush(self):
        pass


class NimbusWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(int)

    def __init__(self, cfg_kwargs: Dict[str, Any], workdir: Path, overwrite_cnorm: bool, parent=None):
        super().__init__(parent)
        self.cfg_kwargs = cfg_kwargs
        self.workdir = workdir
        self.overwrite_cnorm = overwrite_cnorm
        self._cancel = False  # best-effort

    def request_cancel(self):
        self._cancel = True

    def run(self):
        try:
            self.workdir.mkdir(parents=True, exist_ok=True)
            os.chdir(self.workdir)

            # If core doesn't support rm_cnorm, we can still do it here.
            cnorm_path = ensure_cnorm_path(str(self.cfg_kwargs.get("cnorm_path", "")))
            if self.overwrite_cnorm and int(self.cfg_kwargs.get("readcnorm", 0)) == 0:
                p = Path(cnorm_path)
                if p.exists() and p.is_file():
                    p.unlink()

            stream = _QtStream(self.log.emit)
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                # Filter kwargs to match core Config fields (future-proof)
                fields = set(getattr(nimbus.Config, "__dataclass_fields__", {}).keys())
                safe_kwargs = {k: v for k, v in self.cfg_kwargs.items() if (not fields) or (k in fields)}

                cfg = nimbus.Config(**safe_kwargs)
                nimbus.run(cfg)

            self.done.emit(0)
        except Exception:
            self.log.emit("\n" + traceback.format_exc() + "\n")
            self.done.emit(1)


# ---------------------------
# Main UI
# ---------------------------
class NimbusMainWindow(QtWidgets.QMainWindow):
    HELP: Dict[str, str] = {
        "workdir": "Working directory where output files are written.",
        "xyz": "Equilibrium XYZ geometry file. nat is read from the first line.",
        "traj": "Trajectory XYZ file (multi-frame). First line of each frame should be nat.",
        "hess": "Hessian file used to compute normal modes (required if readcnorm = 0).",
        "readcnorm": "0: compute cnorm from Hessian and write cnorm.dat. 1: read cnorm.dat from file.",
        "cnorm": "Path to cnorm file. If empty, defaults to cnorm.dat.",
        "rm_cnorm": "If enabled and readcnorm=0, delete existing cnorm file before writing (overwrite).",
        "nrototrasl": "Number of roto-translational modes to exclude: 6 (non-linear), 5 (linear).",
        "nstart": "Index of first trajectory frame to use (1 = first frame).",
        "ncorr": "Number of time points used for correlation / TA.",
        "nbeads": "Number of beads for time averaging (0 = auto).",
        "nbeadsstep": "Stride between beads.",
        "dt": "Time step between frames (atomic units).",
        "coord": "Coordinate system: nm (normal modes) or cart (cartesian).",
        "ta": "Time-averaged spectrum mode.",
        "alpha_pow": "Damping coefficient for power spectrum.",
        "alpha_dip": "Damping coefficient for dipole correlation / IR.",
        "modes": "List of vibrational modes (1-based). Supports ranges: 1-5, 10..12, 20:22 and commas. Required if coord = nm.",
        "atoms": "Optional space-separated list of atoms (1-based). Empty = all atoms.",
        "init_wnumb": "Start wavenumber (cm^-1).",
        "spec_res": "Spectrum resolution (cm^-1).",
        "wnumb_span": "Wavenumber span (cm^-1).",
        "freq_offset": "Shift the output wavenumber axis by this offset (cm^-1).",
        "norm1": "Normalize each printed spectrum so the highest peak is 1.",
        "excel": "Write Excel-friendly CSV tables.",
        "excel_sep": "CSV delimiter: ',' ';' or 'tab'.",
        "excel_merge": "Also write merged CSV per spectrum type (columns = selected modes).",
        "plot": "Save PNG plots of spectra.",
        "plot_dir": "Directory where plots are written.",
        "plot_dpi": "PNG resolution (DPI).",
        "out_prefix": "Output filename prefix.",
        "results_file": "Spectrum file to load (.csv from --excel or .dat output).",
        "results_series": "Select one or more series to plot (for merged CSV: each column is a series).",
        "results_norm": "Normalize each plotted series so its maximum is 1.",
        "results_offset": "Shift x-axis (wavenumber) by this offset (cm^-1).",
        "results_smooth": "Moving-average smoothing window (points). 1 disables smoothing.",
        "results_xlim": "Limit x-axis range. Leave empty to auto-scale.",
        "results_logy": "Use log scale for y-axis.",
        "results_fill": "Fill the whole area under each plotted spectrum using the same curve color.",
        "results_fill_alpha": "Transparency (alpha) of the filled area under each plotted spectrum.",
        "results_svg": "Save the current plot in SVG (vector) format for publication-quality figures.",
        "results_popout": "Open a separate large window for the spectrum. It stays synced with the embedded plot.",
        "results_frame": "Control the plot frame: box (all), half-open (hide top/right), or open (no spines).",
        "results_grid": "Show/hide the grid in the Results plot.",
        "results_grid_alpha": "Grid transparency (alpha).",
        "results_grid_style": "Grid line style and width.",
        "results_bg": "Axes background: default / white / transparent (useful for papers).",
        "results_xtick": "Major tick step on x (cm^-1). Leave empty for auto.",
        "results_ytick": "Major tick step on y. Leave empty for auto.",
        "results_minor": "Enable minor ticks (and optionally minor grid).",
        "analysis_curve": "Curve used for interactive picking (mouse clicks on the plot).",
        "analysis_pick": "Pick a peak by clicking near it on the plot. The code snaps to the nearest local maximum.",
        "analysis_fwhm": "Compute FWHM (full width at half maximum) of the selected peak A.",
        "analysis_dist": "Compute the distance in cm^-1 between peak A and peak B maxima.",
        "analysis_shade": "Fill the area under the peak A region (its FWHM) with chosen color and transparency.",
        "analysis_color": "Choose fill color for the highlighted peak area.",
        "analysis_alpha": "Transparency (alpha) for highlighted peak area: 0 = invisible, 1 = opaque.",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flying Nimbus GUI")
        self.resize(1220, 860)

        self.worker: Optional[NimbusWorker] = None
        self._popout_win: Optional[SpectrumPopoutWindow] = None

        self.settings = QtCore.QSettings("FlyingNimbus", "NimbusGUIHeavy")
        self._build_actions()
        self._build_ui()
        self._apply_theme(dark=True)
        self._restore_settings()

        # Don't compute preview at startup if XYZ not set
        self._refresh_nat_badge()
        self._update_preview_safe()

    # ---------------------
    # Actions / menus
    # ---------------------
    def _build_actions(self):
        self.act_run = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay), "Run", self)
        self.act_stop = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaStop), "Stop", self)
        self.act_open_workdir = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon), "Open workdir", self)
        self.act_save_preset = QtGui.QAction("Save preset…", self)
        self.act_load_preset = QtGui.QAction("Load preset…", self)
        self.act_toggle_dark = QtGui.QAction("Dark theme", self, checkable=True)
        self.act_toggle_dark.setChecked(True)

        self.act_show_log = QtGui.QAction("Show log", self, checkable=True)
        self.act_show_help = QtGui.QAction("Show help", self, checkable=True)
        self.act_show_preview = QtGui.QAction("Show preview", self, checkable=True)

        self.act_run.triggered.connect(self._run)
        self.act_stop.triggered.connect(self._stop)
        self.act_open_workdir.triggered.connect(self._open_workdir)
        self.act_save_preset.triggered.connect(self._save_preset)
        self.act_load_preset.triggered.connect(self._load_preset)
        self.act_toggle_dark.toggled.connect(self._apply_theme)

    def _build_menu(self):
        m_file = self.menuBar().addMenu("File")
        m_file.addAction(self.act_load_preset)
        m_file.addAction(self.act_save_preset)
        m_file.addSeparator()
        m_file.addAction("Quit", self.close)

        m_view = self.menuBar().addMenu("View")
        m_view.addAction(self.act_toggle_dark)
        m_view.addSeparator()
        m_view.addAction(self.act_show_log)
        m_view.addAction(self.act_show_help)
        m_view.addAction(self.act_show_preview)

        m_run = self.menuBar().addMenu("Run")
        m_run.addAction(self.act_run)
        m_run.addAction(self.act_stop)

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.addAction(self.act_run)
        tb.addAction(self.act_stop)
        tb.addSeparator()
        tb.addAction(self.act_open_workdir)
        tb.addSeparator()
        tb.addAction(self.act_load_preset)
        tb.addAction(self.act_save_preset)

    # ---------------------
    # UI construction
    # ---------------------
    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()

        # Central splitter: sidebar + pages
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        self.sidebar = QtWidgets.QListWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setSpacing(4)
        self.sidebar.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        def add_nav(title: str, icon: QtGui.QIcon):
            it = QtWidgets.QListWidgetItem(icon, title)
            it.setSizeHint(QtCore.QSize(200, 44))
            self.sidebar.addItem(it)

        add_nav("Files", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirIcon))
        add_nav("Dynamics", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView))
        add_nav("Spectrum", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon))
        add_nav("Export", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DriveHDIcon))
        add_nav("Results", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView))
        add_nav("About", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation))

        self.pages = QtWidgets.QStackedWidget()
        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)

        self.page_files = self._make_scroll_page()
        self.page_dyn = self._make_scroll_page()
        self.page_spec = self._make_scroll_page()
        self.page_export = self._make_scroll_page()
        self.page_results = self._make_scroll_page()
        self.page_about = self._make_scroll_page()

        self.pages.addWidget(self.page_files)
        self.pages.addWidget(self.page_dyn)
        self.pages.addWidget(self.page_spec)
        self.pages.addWidget(self.page_export)
        self.pages.addWidget(self.page_results)
        self.pages.addWidget(self.page_about)

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        # Docks: Log, Help, Preview
        self.dock_log = QtWidgets.QDockWidget("Log", self)
        self.dock_help = QtWidgets.QDockWidget("Help", self)
        self.dock_preview = QtWidgets.QDockWidget("Preview", self)

        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(200000)
        self.dock_log.setWidget(self.txt_log)

        self.txt_help = QtWidgets.QTextBrowser()
        self.txt_help.setOpenExternalLinks(False)
        self.txt_help.setHtml("<h3>Help</h3><p>Click a parameter name to see its explanation.</p>")
        self.dock_help.setWidget(self.txt_help)

        self.txt_preview = QtWidgets.QPlainTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setMaximumBlockCount(10000)
        self.dock_preview.setWidget(self.txt_preview)

        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_log)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.dock_help)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_preview)

        # Default visibility: log+help shown, preview hidden
        self.dock_preview.setVisible(False)
        self.act_show_log.setChecked(True)
        self.act_show_help.setChecked(True)
        self.act_show_preview.setChecked(False)
        self.act_show_log.toggled.connect(self.dock_log.setVisible)
        self.act_show_help.toggled.connect(self.dock_help.setVisible)
        self.act_show_preview.toggled.connect(self.dock_preview.setVisible)

        self.dock_log.visibilityChanged.connect(self.act_show_log.setChecked)
        self.dock_help.visibilityChanged.connect(self.act_show_help.setChecked)
        self.dock_preview.visibilityChanged.connect(self.act_show_preview.setChecked)

        # Build pages
        self._build_page_files(self._page_layout(self.page_files))
        self._build_page_dyn(self._page_layout(self.page_dyn))
        self._build_page_spec(self._page_layout(self.page_spec))
        self._build_page_export(self._page_layout(self.page_export))
        self._build_page_results(self._page_layout(self.page_results))
        self._build_page_about(self._page_layout(self.page_about))

        self._set_running(False)

        # Status bar
        self.status = self.statusBar()
        self.lbl_nat = QtWidgets.QLabel("nat: —")
        self.status.addPermanentWidget(self.lbl_nat)

    def _make_scroll_page(self) -> QtWidgets.QScrollArea:
        sc = QtWidgets.QScrollArea()
        sc.setWidgetResizable(True)
        w = QtWidgets.QWidget()
        sc.setWidget(w)
        return sc

    def _page_layout(self, page: QtWidgets.QScrollArea) -> QtWidgets.QVBoxLayout:
        w = page.widget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        return lay

    def _hlbl(self, title: str, key: str) -> QtWidgets.QLabel:
        lbl = ClickableLabel(title)
        lbl.setToolTip(self.HELP.get(key, ""))
        lbl.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        lbl.setStyleSheet("color: #79b8ff; text-decoration: underline;")
        lbl.clicked.connect(lambda: self._show_help(key, title))
        return lbl

    def _show_help(self, key: str, title: str):
        body = self.HELP.get(key, "No help available.")
        html = f"<h3>{title}</h3><p>{body}</p>"
        self.txt_help.setHtml(html)
        if not self.dock_help.isVisible():
            self.dock_help.setVisible(True)

    # ---------------------
    # Page: Files
    # ---------------------
    def _build_page_files(self, lay: QtWidgets.QVBoxLayout):
        sec_runner = CollapsibleSection("Runner", expanded=True)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        # Working dir
        self.ed_workdir = QtWidgets.QLineEdit()
        self.btn_workdir = QtWidgets.QToolButton()
        self.btn_workdir.setText("…")
        self.btn_workdir.clicked.connect(self._browse_workdir)
        wd_row = QtWidgets.QHBoxLayout()
        wd_row.addWidget(self.ed_workdir, 1)
        wd_row.addWidget(self.btn_workdir, 0)
        form.addRow(self._hlbl("Working directory", "workdir"), self._wrap(wd_row))

        sec_runner.content_lay.addLayout(form)
        lay.addWidget(sec_runner)

        sec_inputs = CollapsibleSection("Input files", expanded=True)
        f2 = QtWidgets.QFormLayout()
        f2.setHorizontalSpacing(18)
        f2.setVerticalSpacing(10)

        self.ed_xyz = QtWidgets.QLineEdit()
        self.ed_traj = QtWidgets.QLineEdit()
        self.ed_hess = QtWidgets.QLineEdit()
        self.ed_cnorm = QtWidgets.QLineEdit("cnorm.dat")

        for ed in (self.ed_xyz, self.ed_traj, self.ed_hess, self.ed_cnorm):
            ed.textChanged.connect(self._on_any_change)

        f2.addRow(*self._file_row(self._hlbl("Equilibrium XYZ", "xyz"), self.ed_xyz, self._browse_xyz))
        f2.addRow(*self._file_row(self._hlbl("Trajectory", "traj"), self.ed_traj, self._browse_traj))
        f2.addRow(*self._file_row(self._hlbl("Hessian", "hess"), self.ed_hess, self._browse_hess))
        f2.addRow(*self._file_row(self._hlbl("cnorm file", "cnorm"), self.ed_cnorm, self._browse_cnorm))

        sec_inputs.content_lay.addLayout(f2)
        lay.addWidget(sec_inputs)

        sec_out = CollapsibleSection("Output & plots", expanded=True)
        f3 = QtWidgets.QFormLayout()
        f3.setHorizontalSpacing(18)
        f3.setVerticalSpacing(10)

        self.ed_out_prefix = QtWidgets.QLineEdit("QCT_")
        self.cb_plot = QtWidgets.QCheckBox()
        self.ed_plotdir = QtWidgets.QLineEdit(".")
        self.btn_plotdir = QtWidgets.QToolButton(text="…")
        self.btn_plotdir.clicked.connect(self._browse_plotdir)
        self.sp_plotdpi = QtWidgets.QSpinBox()
        self.sp_plotdpi.setRange(30, 1200)
        self.sp_plotdpi.setValue(200)

        self.ed_out_prefix.textChanged.connect(self._on_any_change)
        self.cb_plot.toggled.connect(self._on_any_change)
        self.ed_plotdir.textChanged.connect(self._on_any_change)
        self.sp_plotdpi.valueChanged.connect(self._on_any_change)

        f3.addRow(self._hlbl("Output prefix", "out_prefix"), self.ed_out_prefix)

        row_plot = QtWidgets.QHBoxLayout()
        row_plot.addWidget(self.cb_plot)
        row_plot.addWidget(self._hlbl("Save plots", "plot"))
        row_plot.addStretch(1)
        f3.addRow(QtWidgets.QLabel(""), self._wrap(row_plot))

        plotdir_row = QtWidgets.QHBoxLayout()
        plotdir_row.addWidget(self.ed_plotdir, 1)
        plotdir_row.addWidget(self.btn_plotdir, 0)
        f3.addRow(self._hlbl("Plot directory", "plot_dir"), self._wrap(plotdir_row))
        f3.addRow(self._hlbl("Plot DPI", "plot_dpi"), self.sp_plotdpi)

        sec_out.content_lay.addLayout(f3)
        lay.addWidget(sec_out)

        lay.addStretch(1)

    def _file_row(self, label_widget: QtWidgets.QWidget, lineedit: QtWidgets.QLineEdit, browse_fn):
        btn = QtWidgets.QToolButton(text="…")
        btn.clicked.connect(browse_fn)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(lineedit, 1)
        row.addWidget(btn, 0)
        return label_widget, self._wrap(row)

    # ---------------------
    # Page: Dynamics
    # ---------------------
    def _build_page_dyn(self, lay: QtWidgets.QVBoxLayout):
        sec = CollapsibleSection("Dynamics", expanded=True)
        f = QtWidgets.QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(10)

        self.cb_nrt = QtWidgets.QComboBox()
        self.cb_nrt.addItems(["6", "5"])
        self.cb_nrt.currentTextChanged.connect(self._on_any_change)

        self.sp_nstart = QtWidgets.QSpinBox(); self.sp_nstart.setRange(0, 10_000_000); self.sp_nstart.setValue(1)
        self.sp_ncorr = QtWidgets.QSpinBox(); self.sp_ncorr.setRange(1, 10_000_000); self.sp_ncorr.setValue(2500)
        self.sp_nbeads = QtWidgets.QSpinBox(); self.sp_nbeads.setRange(0, 10_000_000); self.sp_nbeads.setValue(0)
        self.sp_nbeadsstep = QtWidgets.QSpinBox(); self.sp_nbeadsstep.setRange(1, 10_000_000); self.sp_nbeadsstep.setValue(1)

        self.sp_dt = QtWidgets.QDoubleSpinBox()
        self.sp_dt.setRange(0.0, 1e12)
        self.sp_dt.setDecimals(12)
        self.sp_dt.setValue(8.2682749151502)

        for w in [self.sp_nstart, self.sp_ncorr, self.sp_nbeads, self.sp_nbeadsstep, self.sp_dt]:
            w.valueChanged.connect(self._on_any_change)

        f.addRow(self._hlbl("nrototrasl", "nrototrasl"), self.cb_nrt)
        f.addRow(self._hlbl("nstart", "nstart"), self.sp_nstart)
        f.addRow(self._hlbl("ncorr", "ncorr"), self.sp_ncorr)
        f.addRow(self._hlbl("nbeads", "nbeads"), self.sp_nbeads)
        f.addRow(self._hlbl("nbeadsstep", "nbeadsstep"), self.sp_nbeadsstep)
        f.addRow(self._hlbl("dt (a.u.)", "dt"), self.sp_dt)

        sec.content_lay.addLayout(f)
        lay.addWidget(sec)

        sec2 = CollapsibleSection("Modes & damping", expanded=True)
        f2 = QtWidgets.QFormLayout()
        f2.setHorizontalSpacing(18)
        f2.setVerticalSpacing(10)

        self.cb_coord = QtWidgets.QComboBox()
        self.cb_coord.addItems(["nm", "cart"])
        self.cb_coord.currentTextChanged.connect(self._on_any_change)

        self.cb_ta = QtWidgets.QCheckBox()
        self.cb_ta.setChecked(True)
        self.cb_ta.toggled.connect(self._on_any_change)

        self.sp_alpha_pow = QtWidgets.QDoubleSpinBox()
        self.sp_alpha_pow.setRange(0.0, 1e12)
        self.sp_alpha_pow.setDecimals(12)
        self.sp_alpha_pow.setValue(0.0)
        self.sp_alpha_pow.valueChanged.connect(self._on_any_change)

        self.sp_alpha_dip = QtWidgets.QDoubleSpinBox()
        self.sp_alpha_dip.setRange(0.0, 1e12)
        self.sp_alpha_dip.setDecimals(12)
        self.sp_alpha_dip.setValue(1e-8)
        self.sp_alpha_dip.valueChanged.connect(self._on_any_change)

        self.ed_modes = QtWidgets.QLineEdit()
        self.ed_modes.setPlaceholderText("e.g. 1-5, 10..12, 20:22")
        self.ed_atoms = QtWidgets.QLineEdit()
        self.ed_atoms.setPlaceholderText("optional, e.g. 1 2 5 6")

        self.ed_modes.textChanged.connect(self._on_any_change)
        self.ed_atoms.textChanged.connect(self._on_any_change)

        row_ta = QtWidgets.QHBoxLayout()
        row_ta.addWidget(self.cb_ta)
        row_ta.addWidget(self._hlbl("Time-averaged", "ta"))
        row_ta.addStretch(1)

        f2.addRow(self._hlbl("coord", "coord"), self.cb_coord)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_ta))
        f2.addRow(self._hlbl("alpha_pow", "alpha_pow"), self.sp_alpha_pow)
        f2.addRow(self._hlbl("alpha_dip", "alpha_dip"), self.sp_alpha_dip)
        f2.addRow(self._hlbl("modes", "modes"), self.ed_modes)
        f2.addRow(self._hlbl("atoms", "atoms"), self.ed_atoms)

        sec2.content_lay.addLayout(f2)
        lay.addWidget(sec2)

        sec3 = CollapsibleSection("cnorm control", expanded=True)
        f3 = QtWidgets.QFormLayout()
        f3.setHorizontalSpacing(18)
        f3.setVerticalSpacing(10)

        self.cb_readcnorm = QtWidgets.QComboBox()
        self.cb_readcnorm.addItems(["0", "1"])
        self.cb_readcnorm.currentTextChanged.connect(self._on_any_change)

        self.cb_rm_cnorm = QtWidgets.QCheckBox()
        self.cb_rm_cnorm.toggled.connect(self._on_any_change)

        row_rm = QtWidgets.QHBoxLayout()
        row_rm.addWidget(self.cb_rm_cnorm)
        row_rm.addWidget(self._hlbl("Overwrite cnorm", "rm_cnorm"))
        row_rm.addStretch(1)

        f3.addRow(self._hlbl("readcnorm", "readcnorm"), self.cb_readcnorm)
        f3.addRow(QtWidgets.QLabel(""), self._wrap(row_rm))

        sec3.content_lay.addLayout(f3)
        lay.addWidget(sec3)

        lay.addStretch(1)

    # ---------------------
    # Page: Spectrum
    # ---------------------
    def _build_page_spec(self, lay: QtWidgets.QVBoxLayout):
        sec = CollapsibleSection("Spectrum grid", expanded=True)
        f = QtWidgets.QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(10)

        self.sp_init = QtWidgets.QDoubleSpinBox(); self.sp_init.setRange(-1e12, 1e12); self.sp_init.setDecimals(6); self.sp_init.setValue(0.0)
        self.sp_res  = QtWidgets.QDoubleSpinBox(); self.sp_res.setRange(0.1, 1e12); self.sp_res.setDecimals(6); self.sp_res.setValue(1.0)
        self.sp_span = QtWidgets.QDoubleSpinBox(); self.sp_span.setRange(0.0, 1e12); self.sp_span.setDecimals(6); self.sp_span.setValue(5000.0)

        for w in [self.sp_init, self.sp_res, self.sp_span]:
            w.valueChanged.connect(self._on_any_change)

        f.addRow(self._hlbl("init_wnumb", "init_wnumb"), self.sp_init)
        f.addRow(self._hlbl("spec_res", "spec_res"), self.sp_res)
        f.addRow(self._hlbl("wnumb_span", "wnumb_span"), self.sp_span)
        sec.content_lay.addLayout(f)
        lay.addWidget(sec)

        sec2 = CollapsibleSection("Post-processing", expanded=True)
        f2 = QtWidgets.QFormLayout()
        f2.setHorizontalSpacing(18)
        f2.setVerticalSpacing(10)

        self.sp_freq_offset = QtWidgets.QDoubleSpinBox(); self.sp_freq_offset.setRange(-1e12, 1e12); self.sp_freq_offset.setDecimals(6); self.sp_freq_offset.setValue(0.0)
        self.cb_norm1 = QtWidgets.QCheckBox()
        self.sp_freq_offset.valueChanged.connect(self._on_any_change)
        self.cb_norm1.toggled.connect(self._on_any_change)

        row_norm = QtWidgets.QHBoxLayout()
        row_norm.addWidget(self.cb_norm1)
        row_norm.addWidget(self._hlbl("Normalize max peak to 1", "norm1"))
        row_norm.addStretch(1)

        f2.addRow(self._hlbl("freq_offset", "freq_offset"), self.sp_freq_offset)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_norm))

        sec2.content_lay.addLayout(f2)
        lay.addWidget(sec2)

        lay.addStretch(1)

    # ---------------------
    # Page: Export
    # ---------------------
    def _build_page_export(self, lay: QtWidgets.QVBoxLayout):
        sec = CollapsibleSection("Excel / CSV output", expanded=True)
        f = QtWidgets.QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(10)

        self.cb_excel = QtWidgets.QCheckBox()
        self.cb_excel.toggled.connect(self._on_any_change)
        self.ed_excel_sep = QtWidgets.QLineEdit(",")
        self.ed_excel_sep.textChanged.connect(self._on_any_change)
        self.cb_excel_merge = QtWidgets.QCheckBox()
        self.cb_excel_merge.toggled.connect(self._on_any_change)

        row_excel = QtWidgets.QHBoxLayout()
        row_excel.addWidget(self.cb_excel)
        row_excel.addWidget(self._hlbl("Write CSV", "excel"))
        row_excel.addStretch(1)

        row_merge = QtWidgets.QHBoxLayout()
        row_merge.addWidget(self.cb_excel_merge)
        row_merge.addWidget(self._hlbl("Merged CSV", "excel_merge"))
        row_merge.addStretch(1)

        f.addRow(QtWidgets.QLabel(""), self._wrap(row_excel))
        f.addRow(self._hlbl("CSV delimiter", "excel_sep"), self.ed_excel_sep)
        f.addRow(QtWidgets.QLabel(""), self._wrap(row_merge))

        sec.content_lay.addLayout(f)
        lay.addWidget(sec)
        lay.addStretch(1)


    # ---------------------
    # Page: Results
    # ---------------------
    def _build_page_results(self, lay: QtWidgets.QVBoxLayout):
        sec_load = CollapsibleSection("Load & select spectra", expanded=True)
        f = QtWidgets.QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(10)

        # Add single file row (manual path + browse + add)
        self.ed_results_add = QtWidgets.QLineEdit()
        self.ed_results_add.setPlaceholderText("Add a spectrum file (.csv or .dat)")
        btn_browse_one = QtWidgets.QToolButton(text="…")
        btn_browse_one.clicked.connect(self._browse_results_one)
        btn_add_one = QtWidgets.QPushButton("Add")
        btn_add_one.clicked.connect(self._add_results_one_from_lineedit)

        row_add = QtWidgets.QHBoxLayout()
        row_add.addWidget(self.ed_results_add, 1)
        row_add.addWidget(btn_browse_one, 0)
        row_add.addWidget(btn_add_one, 0)
        f.addRow(self._hlbl("Spectrum file", "results_file"), self._wrap(row_add))

        # Add multiple + latest + remove/clear
        row_btns = QtWidgets.QHBoxLayout()
        self.btn_add_many = QtWidgets.QPushButton("Add multiple…")
        self.btn_add_many.clicked.connect(self._browse_results_many)
        self.btn_load_latest = QtWidgets.QPushButton("Add latest from workdir")
        self.btn_load_latest.clicked.connect(self._load_latest_from_workdir)
        self.btn_remove_selected = QtWidgets.QPushButton("Remove selected")
        self.btn_remove_selected.clicked.connect(self._remove_selected_datasets)
        self.btn_clear_all = QtWidgets.QPushButton("Clear all")
        self.btn_clear_all.clicked.connect(self._clear_all_datasets)

        row_btns.addWidget(self.btn_add_many)
        row_btns.addWidget(self.btn_load_latest)
        row_btns.addStretch(1)
        row_btns.addWidget(self.btn_remove_selected)
        row_btns.addWidget(self.btn_clear_all)
        f.addRow(QtWidgets.QLabel(""), self._wrap(row_btns))

        # Datasets + series tree
        self.tw_series = QtWidgets.QTreeWidget()
        self.tw_series.setHeaderLabels(["Dataset / series", "Source"])
        self.tw_series.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tw_series.setUniformRowHeights(True)
        self.tw_series.setAlternatingRowColors(True)
        self.tw_series.setMinimumHeight(220)
        self.tw_series.setItemDelegateForColumn(0, SeriesNameEditDelegate(self.tw_series))
        self.tw_series.itemChanged.connect(self._on_results_tree_changed)
        f.addRow(self._hlbl("Series", "results_series"), self.tw_series)

        # Hint
        hint = QtWidgets.QLabel("Tip: double-click a dataset name to rename it (legend updates automatically).")
        hint.setStyleSheet("color: #94a3b8;")
        f.addRow(QtWidgets.QLabel(""), hint)

        sec_load.content_lay.addLayout(f)
        lay.addWidget(sec_load)

        sec_plot = CollapsibleSection("Plot controls", expanded=True)
        f2 = QtWidgets.QFormLayout()
        f2.setHorizontalSpacing(18)
        f2.setVerticalSpacing(10)

        self.cb_res_norm = QtWidgets.QCheckBox()
        self.cb_res_norm.toggled.connect(self._on_results_controls_changed)
        row_norm = QtWidgets.QHBoxLayout()
        row_norm.addWidget(self.cb_res_norm)
        row_norm.addWidget(self._hlbl("Normalize max to 1", "results_norm"))
        row_norm.addStretch(1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_norm))

        self.sp_res_offset = QtWidgets.QDoubleSpinBox()
        self.sp_res_offset.setRange(-1e12, 1e12)
        self.sp_res_offset.setDecimals(6)
        self.sp_res_offset.setValue(0.0)
        self.sp_res_offset.valueChanged.connect(self._on_results_controls_changed)
        f2.addRow(self._hlbl("x offset (cm^-1)", "results_offset"), self.sp_res_offset)

        self.sp_res_smooth = QtWidgets.QSpinBox()
        self.sp_res_smooth.setRange(1, 10001)
        self.sp_res_smooth.setValue(1)
        self.sp_res_smooth.valueChanged.connect(self._on_results_controls_changed)
        f2.addRow(self._hlbl("Smoothing window (points)", "results_smooth"), self.sp_res_smooth)

        # x-limits
        row_xlim = QtWidgets.QHBoxLayout()
        self.ed_xmin = QtWidgets.QLineEdit()
        self.ed_xmax = QtWidgets.QLineEdit()
        self.ed_xmin.setPlaceholderText("xmin")
        self.ed_xmax.setPlaceholderText("xmax")
        self.ed_xmin.textChanged.connect(self._on_results_controls_changed)
        self.ed_xmax.textChanged.connect(self._on_results_controls_changed)
        row_xlim.addWidget(self.ed_xmin, 1)
        row_xlim.addWidget(self.ed_xmax, 1)
        f2.addRow(self._hlbl("x range", "results_xlim"), self._wrap(row_xlim))

        self.cb_logy = QtWidgets.QCheckBox()
        self.cb_logy.toggled.connect(self._on_results_controls_changed)
        row_logy = QtWidgets.QHBoxLayout()
        row_logy.addWidget(self.cb_logy)
        row_logy.addWidget(self._hlbl("Log y-scale", "results_logy"))
        row_logy.addStretch(1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_logy))

        row_fill = QtWidgets.QHBoxLayout()
        self.cb_res_fill = QtWidgets.QCheckBox()
        self.cb_res_fill.toggled.connect(self._on_results_controls_changed)
        row_fill.addWidget(self.cb_res_fill)
        row_fill.addWidget(self._hlbl("Fill area under curves", "results_fill"))
        row_fill.addSpacing(10)
        row_fill.addWidget(QtWidgets.QLabel("opacity"))
        self.sp_res_fill_alpha = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.sp_res_fill_alpha.setRange(0, 100)
        self.sp_res_fill_alpha.setValue(25)
        self.sp_res_fill_alpha.valueChanged.connect(self._on_results_controls_changed)
        row_fill.addWidget(self.sp_res_fill_alpha, 1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_fill))

        # ---- style (frame, grid, background, ticks) ----
        self.cb_res_frame = QtWidgets.QComboBox()
        self.cb_res_frame.addItems([
            "Box (all spines)",
            "Half-open (hide top/right)",
            "Open (no spines)",
        ])
        self.cb_res_frame.currentIndexChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("Frame / spines", "results_frame"), self.cb_res_frame)

        # Grid controls
        self.cb_res_grid = QtWidgets.QCheckBox()
        self.cb_res_grid.setChecked(True)
        self.cb_res_grid.toggled.connect(self._on_results_style_changed)
        row_grid = QtWidgets.QHBoxLayout()
        row_grid.addWidget(self.cb_res_grid)
        row_grid.addWidget(self._hlbl("Grid", "results_grid"))
        row_grid.addStretch(1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_grid))

        grid_opts = QtWidgets.QHBoxLayout()
        self.sp_grid_alpha = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.sp_grid_alpha.setRange(0, 100)
        self.sp_grid_alpha.setValue(25) 
        self.sp_grid_alpha.valueChanged.connect(self._on_results_style_changed)

        self.cb_grid_ls = QtWidgets.QComboBox()
        self.cb_grid_ls.addItems(["-", "--", ":", "-."])
        self.cb_grid_ls.setCurrentText("-")
        self.cb_grid_ls.currentIndexChanged.connect(self._on_results_style_changed)

        self.sp_grid_lw = QtWidgets.QDoubleSpinBox()
        self.sp_grid_lw.setRange(0.1, 10.0)
        self.sp_grid_lw.setDecimals(2)
        self.sp_grid_lw.setValue(0.8)
        self.sp_grid_lw.valueChanged.connect(self._on_results_style_changed)

        grid_opts.addWidget(QtWidgets.QLabel("opacity"))
        grid_opts.addWidget(self.sp_grid_alpha, 1)
        grid_opts.addSpacing(10)
        grid_opts.addWidget(QtWidgets.QLabel("style"))
        grid_opts.addWidget(self.cb_grid_ls)
        grid_opts.addSpacing(10)
        grid_opts.addWidget(QtWidgets.QLabel("lw"))
        grid_opts.addWidget(self.sp_grid_lw)
        f2.addRow(self._hlbl("Grid options", "results_grid_style"), self._wrap(grid_opts))

        # Background
        self.cb_res_bg = QtWidgets.QComboBox()
        self.cb_res_bg.addItems(["Default", "White", "Transparent"])
        self.cb_res_bg.currentIndexChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("Background", "results_bg"), self.cb_res_bg)

        # Tick spacing (spinboxes avoid heavy redraw while typing)
        self.sp_xtick = QtWidgets.QSpinBox()
        self.sp_xtick.setRange(0, 200000)
        self.sp_xtick.setSpecialValueText("auto")
        self.sp_xtick.setValue(0)
        self.sp_xtick.setSingleStep(50)
        self.sp_xtick.setKeyboardTracking(False)
        self.sp_xtick.valueChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("x tick step (cm^-1)", "results_xtick"), self.sp_xtick)

        self.sp_ytick = QtWidgets.QDoubleSpinBox()
        self.sp_ytick.setRange(0.0, 1e9)
        self.sp_ytick.setDecimals(6)
        self.sp_ytick.setSpecialValueText("auto")
        self.sp_ytick.setValue(0.0)
        self.sp_ytick.setSingleStep(0.1)
        self.sp_ytick.setKeyboardTracking(False)
        self.sp_ytick.valueChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("y tick step", "results_ytick"), self.sp_ytick)

        self.cb_minor_ticks = QtWidgets.QCheckBox()
        self.cb_minor_ticks.toggled.connect(self._on_results_style_changed)
        row_minor = QtWidgets.QHBoxLayout()
        row_minor.addWidget(self.cb_minor_ticks)
        row_minor.addWidget(self._hlbl("Minor ticks", "results_minor"))
        row_minor.addStretch(1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_minor))

        # ---- Legend styling ----
        row_leg = QtWidgets.QHBoxLayout()
        self.cb_legend_show = QtWidgets.QCheckBox()
        self.cb_legend_show.setChecked(True)
        self.cb_legend_show.toggled.connect(self._on_results_style_changed)
        row_leg.addWidget(self.cb_legend_show)
        row_leg.addWidget(self._hlbl("Show legend", "results_legend_show"))
        row_leg.addStretch(1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_leg))

        self.cb_legend_loc = QtWidgets.QComboBox()
        self.cb_legend_loc.addItems([
            "best", "upper right", "upper left", "lower left", "lower right",
            "center left", "center right", "lower center", "upper center", "center"
        ])
        self.cb_legend_loc.setCurrentText("best")
        self.cb_legend_loc.currentIndexChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("Legend location", "results_legend_loc"), self.cb_legend_loc)

        self.sp_legend_font = QtWidgets.QSpinBox()
        self.sp_legend_font.setRange(6, 32)
        self.sp_legend_font.setValue(8)
        self.sp_legend_font.setKeyboardTracking(False)
        self.sp_legend_font.valueChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("Legend font size", "results_legend_font"), self.sp_legend_font)

        self.sp_legend_ncol = QtWidgets.QSpinBox()
        self.sp_legend_ncol.setRange(1, 10)
        self.sp_legend_ncol.setValue(1)
        self.sp_legend_ncol.setKeyboardTracking(False)
        self.sp_legend_ncol.valueChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("Legend columns", "results_legend_ncol"), self.sp_legend_ncol)

        self.sp_legend_maxcurves = QtWidgets.QSpinBox()
        self.sp_legend_maxcurves.setRange(1, 9999)
        self.sp_legend_maxcurves.setValue(16)
        self.sp_legend_maxcurves.setKeyboardTracking(False)
        self.sp_legend_maxcurves.valueChanged.connect(self._on_results_style_changed)
        f2.addRow(self._hlbl("Legend max curves", "results_legend_max"), self.sp_legend_maxcurves)

        row_frame = QtWidgets.QHBoxLayout()
        self.cb_legend_frame = QtWidgets.QCheckBox()
        self.cb_legend_frame.setChecked(True)
        self.cb_legend_frame.toggled.connect(self._on_results_style_changed)
        row_frame.addWidget(self.cb_legend_frame)
        row_frame.addWidget(self._hlbl("Legend box/frame", "results_legend_frame"))
        row_frame.addStretch(1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_frame))

        row_lalpha = QtWidgets.QHBoxLayout()
        self.sp_legend_alpha = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.sp_legend_alpha.setRange(0, 100)
        self.sp_legend_alpha.setValue(85)
        self.sp_legend_alpha.valueChanged.connect(self._on_results_style_changed)
        row_lalpha.addWidget(QtWidgets.QLabel("opacity"))
        row_lalpha.addWidget(self.sp_legend_alpha, 1)
        f2.addRow(self._hlbl("Legend box alpha", "results_legend_alpha"), self._wrap(row_lalpha))


        self.sp_peak_marker_size = QtWidgets.QSpinBox()
        self.sp_peak_marker_size.setRange(1, 50)
        self.sp_peak_marker_size.setValue(6)
        self.sp_peak_marker_size.setKeyboardTracking(False)
        self.sp_peak_marker_size.valueChanged.connect(self._on_results_controls_changed)
        f2.addRow(QtWidgets.QLabel("Peak marker size"), self.sp_peak_marker_size)

        self.sp_peak_marker_font = QtWidgets.QSpinBox()
        self.sp_peak_marker_font.setRange(6, 32)
        self.sp_peak_marker_font.setValue(9)
        self.sp_peak_marker_font.setKeyboardTracking(False)
        self.sp_peak_marker_font.valueChanged.connect(self._on_results_controls_changed)
        f2.addRow(QtWidgets.QLabel("Peak marker font size"), self.sp_peak_marker_font)

        # Save plot
        self.btn_save_plot = QtWidgets.QPushButton("Save plot (PNG/SVG)…")
        self.btn_save_plot.clicked.connect(self._save_results_plot)
        f2.addRow(QtWidgets.QLabel(""), self.btn_save_plot)

        # Export plotted curves + metrics to CSV (publication-friendly numbers)
        self.btn_export_csv = QtWidgets.QPushButton("Export plotted spectra (CSV)…")
        self.btn_export_csv.clicked.connect(self._export_results_csv)
        f2.addRow(QtWidgets.QLabel(""), self.btn_export_csv)

        self.btn_popout = QtWidgets.QPushButton("Open large spectrum window")
        self.btn_popout.clicked.connect(self._open_popout_spectrum)
        f2.addRow(QtWidgets.QLabel(""), self.btn_popout)

        sec_plot.content_lay.addLayout(f2)
        lay.addWidget(sec_plot)

        # Analysis
        sec_an = CollapsibleSection("Analysis", expanded=True)
        fa = QtWidgets.QFormLayout()
        fa.setHorizontalSpacing(18)
        fa.setVerticalSpacing(10)

        self.cb_an_curve = QtWidgets.QComboBox()
        self.cb_an_curve.currentIndexChanged.connect(self._on_results_controls_changed)
        fa.addRow(self._hlbl("Pick curve", "analysis_curve"), self.cb_an_curve)

        row_pick = QtWidgets.QHBoxLayout()
        self.btn_pick_a = QtWidgets.QPushButton("Pick peak A")
        self.btn_pick_b = QtWidgets.QPushButton("Pick peak B")
        self.btn_pick_a.clicked.connect(lambda: self._analysis_set_pick_mode('A'))
        self.btn_pick_b.clicked.connect(lambda: self._analysis_set_pick_mode('B'))
        row_pick.addWidget(self.btn_pick_a)
        row_pick.addWidget(self.btn_pick_b)
        fa.addRow(self._hlbl("Interactive picking", "analysis_pick"), self._wrap(row_pick))

        row_math = QtWidgets.QHBoxLayout()
        self.btn_fwhm = QtWidgets.QPushButton("FWHM (peak A)")
        self.btn_dist = QtWidgets.QPushButton("Distance A–B")
        self.btn_fwhm.clicked.connect(self._analysis_compute_fwhm)
        self.btn_dist.clicked.connect(self._analysis_compute_distance)
        row_math.addWidget(self.btn_fwhm)
        row_math.addWidget(self.btn_dist)
        fa.addRow(self._hlbl("Metrics", "analysis_fwhm"), self._wrap(row_math))

        # Shading controls
        row_shade = QtWidgets.QHBoxLayout()
        self.cb_shade = QtWidgets.QCheckBox()
        self.cb_shade.toggled.connect(self._on_results_controls_changed)
        row_shade.addWidget(self.cb_shade)
        row_shade.addWidget(self._hlbl("Shade peak A region", "analysis_shade"))
        row_shade.addStretch(1)
        fa.addRow(QtWidgets.QLabel(""), self._wrap(row_shade))

        row_color = QtWidgets.QHBoxLayout()
        self.btn_shade_color = QtWidgets.QPushButton("Color…")
        self.btn_shade_color.clicked.connect(self._analysis_choose_color)
        self.sp_shade_alpha = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.sp_shade_alpha.setRange(0, 100)
        self.sp_shade_alpha.setValue(25)
        self.sp_shade_alpha.valueChanged.connect(self._analysis_on_shade_style_changed)
        row_color.addWidget(self._hlbl("Fill color", "analysis_color"))
        row_color.addWidget(self.btn_shade_color)
        row_color.addSpacing(12)
        row_color.addWidget(self._hlbl("Alpha", "analysis_alpha"))
        row_color.addWidget(self.sp_shade_alpha, 1)
        fa.addRow(QtWidgets.QLabel(""), self._wrap(row_color))

        self.lbl_pick_status = QtWidgets.QLabel("")
        self.lbl_pick_status.setStyleSheet("color: #94a3b8;")
        fa.addRow(QtWidgets.QLabel(""), self.lbl_pick_status)

        self.txt_analysis = QtWidgets.QPlainTextEdit()
        self.txt_analysis.setReadOnly(True)
        self.txt_analysis.setMaximumBlockCount(2000)
        self.txt_analysis.setMinimumHeight(110)
        fa.addRow(QtWidgets.QLabel("Results"), self.txt_analysis)

        row_clear = QtWidgets.QHBoxLayout()
        self.btn_undo_highlight = QtWidgets.QPushButton("Undo last highlight")
        self.btn_undo_highlight.clicked.connect(self._analysis_undo_highlight)
        row_clear.addWidget(self.btn_undo_highlight)
        row_clear.addSpacing(10)
        self.btn_clear_analysis = QtWidgets.QPushButton("Clear markers/highlight")
        self.btn_clear_analysis.clicked.connect(self._analysis_clear)
        row_clear.addWidget(self.btn_clear_analysis)
        row_clear.addStretch(1)
        fa.addRow(QtWidgets.QLabel(""), self._wrap(row_clear))

        sec_an.content_lay.addLayout(fa)
        lay.addWidget(sec_an)

        # Plot canvas
        plot_card = QtWidgets.QFrame()
        plot_card.setObjectName("PlotCard")
        v = QtWidgets.QVBoxLayout(plot_card)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        self.fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.nav = NavigationToolbar(self.canvas, self)

        v.addWidget(self.nav)
        v.addWidget(self.canvas, 1)

        lay.addWidget(plot_card, 1)
        lay.addStretch(1)

        # internal storage: path -> data
        self._datasets_map: Dict[str, Dict[str, Any]] = {}
        self._results_tree_guard = False

        # analysis state
        self._display_curves: Dict[str, Dict[str, Any]] = {}  # curve_id -> {label,x,y}
        self._analysis_pick_mode: Optional[str] = None  # 'A' or 'B'
        self._peak_a: Optional[Dict[str, Any]] = None  # {curve_id, x}
        self._peak_b: Optional[Dict[str, Any]] = None
        self._shade_regions: list[Dict[str, Any]] = []  # each: {curve_id, xmin, xmax, color, alpha}
        self._shade_color_hex: str = "#f59e0b"  # amber

        # connect plot click
        self._mpl_click_cid = self.canvas.mpl_connect('button_press_event', self._on_results_plot_click)

        # Debounced redraw timer (prevents UI freeze when editing tick spacing / sliders)
        self._results_update_timer = QtCore.QTimer(self)
        self._results_update_timer.setSingleShot(True)
        self._results_update_timer.timeout.connect(self._do_results_update)
        self._results_update_full = True

        # Zoom/pan sync between embedded plot and popout
        self._syncing_limits = False
        self._res_view_xlim = None
        self._res_view_ylim = None
        try:
            self.ax.callbacks.connect('xlim_changed', self._on_embedded_limits_changed)
            self.ax.callbacks.connect('ylim_changed', self._on_embedded_limits_changed)
        except Exception:
            pass
        self._analysis_set_color_button()

        # initial empty plot
        self._update_results_plot()

    # ---- Results: add/remove ----
    def _browse_results_one(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select spectrum file",
            str(Path(self.ed_workdir.text() or Path.cwd()).expanduser()),
            "Spectrum (*.csv *.dat);;CSV (*.csv);;DAT (*.dat);;All files (*)",
        )
        if p:
            self.ed_results_add.setText(p)

    def _add_results_one_from_lineedit(self):
        p = (self.ed_results_add.text() or "").strip()
        if p:
            self._add_results_files([p])

    def _browse_results_many(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select spectrum files",
            str(Path(self.ed_workdir.text() or Path.cwd()).expanduser()),
            "Spectrum (*.csv *.dat);;CSV (*.csv);;DAT (*.dat);;All files (*)",
        )
        if paths:
            self._add_results_files(paths)

    def _load_latest_from_workdir(self):
        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        if not wd.exists():
            self._err("Invalid workdir", f"Directory does not exist: {wd}")
            return

        cand = sorted(wd.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not cand:
            cand = sorted(wd.glob("*.dat"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not cand:
            self._err("No spectra found", f"No .csv or .dat files found in: {wd}")
            return
        self._add_results_files([str(cand[0])])

    def _remove_selected_datasets(self):
        # Remove selected top-level datasets (or parents of selected children)
        top_indices = set()
        for it in self.tw_series.selectedItems():
            top = it if it.parent() is None else it.parent()
            idx = self.tw_series.indexOfTopLevelItem(top)
            if idx >= 0:
                top_indices.add(idx)

        if not top_indices:
            return

        for idx in sorted(top_indices, reverse=True):
            top = self.tw_series.topLevelItem(idx)
            if top is None:
                continue
            key = top.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if key and key in self._datasets_map:
                del self._datasets_map[key]
            self.tw_series.takeTopLevelItem(idx)

        self._update_results_plot()

    def _clear_all_datasets(self):
        self._datasets_map.clear()
        self.tw_series.clear()
        self._update_results_plot()

    def _add_results_files(self, paths: list[str]):
        added = 0
        for path_txt in paths:
            p = self._resolve_in_workdir(path_txt)
            if not p.is_file():
                continue

            try:
                sets = self._read_spectrum_file(p)
            except Exception as e:
                self._err("Load failed", f"Could not read spectrum file:\n{p}\n\n{e}")
                continue

            base_key = str(p.resolve())
            for k, (set_name, x, series) in enumerate(sets):
                key = base_key if len(sets) == 1 else f"{base_key}::set{k+1}"
                if key in self._datasets_map:
                    continue

                top_label = p.stem if not set_name else f"{p.stem} — {set_name}"
                source_label = p.name if not set_name else f"{p.name} [{set_name}]"

                self._datasets_map[key] = {"x": x, "series": series, "path": key, "fname": p.name}

                # Add to tree
                self._results_tree_guard = True
                try:
                    top = QtWidgets.QTreeWidgetItem([top_label, source_label])
                    top.setData(0, QtCore.Qt.ItemDataRole.UserRole, key)
                    top.setFlags(top.flags()
                                 | QtCore.Qt.ItemFlag.ItemIsEditable
                                 | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                                 | QtCore.Qt.ItemFlag.ItemIsSelectable
                                 | QtCore.Qt.ItemFlag.ItemIsEnabled)
                    top.setCheckState(0, QtCore.Qt.CheckState.Checked)

                    for sname in series.keys():
                        child = QtWidgets.QTreeWidgetItem([str(sname), ""])
                        child.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(sname))  # original key
                        child.setFlags(child.flags()
                                       | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                                       | QtCore.Qt.ItemFlag.ItemIsSelectable
                                       | QtCore.Qt.ItemFlag.ItemIsEnabled)
                        child.setCheckState(0, QtCore.Qt.CheckState.Checked)
                        top.addChild(child)

                    top.setExpanded(True)
                    self.tw_series.addTopLevelItem(top)
                finally:
                    self._results_tree_guard = False

                added += 1
                self._append_log(f"\n[Results] Added: {source_label}  (series={len(series)})\n")

        if added:
            self._update_results_plot()
    def _on_results_tree_changed(self, item: QtWidgets.QTreeWidgetItem, col: int):
        if self._results_tree_guard:
            return

        if item.parent() is None:
            state = item.checkState(0)
            self._results_tree_guard = True
            try:
                for j in range(item.childCount()):
                    item.child(j).setCheckState(0, state)
            finally:
                self._results_tree_guard = False

        # Any change: update plot 
        self._schedule_results_update(full=True)

    def _schedule_results_update(self, *, full: bool):
        """Debounce Results redraws to keep the UI responsive."""
        # If any caller needs a full redraw, keep that requirement.
        if full:
            self._results_update_full = True
        # (Re)start timer: rapid UI changes collapse into one redraw.
        try:
            self._results_update_timer.start(120)
        except Exception:
            # Fallback (should not happen if the timer is initialized)
            self._update_results_plot()

    def _on_results_controls_changed(self, *args):
        """Results controls that affect data (recompute curves)."""
        self._schedule_results_update(full=True)

    def _on_results_style_changed(self, *args):
        """Results controls that affect only style (fast refresh)."""
        self._schedule_results_update(full=False)

    def _do_results_update(self):
        """Timer callback for debounced Results updates."""
        if getattr(self, "_results_update_full", True):
            self._update_results_plot()
        else:
            self._update_results_style_only()
        self._results_update_full = False

    # ---- Results: file reading ----
    def _read_spectrum_file(self, p: Path) -> list[tuple[str, np.ndarray, Dict[str, np.ndarray]]]:
        """Read a spectrum file.

        Returns a list of *sets* found in the file:
          [(set_name, x, {series_name: y, ...}), ...]

        For normal .dat / single-block CSV, the list has length 1.
        For "all spectra" CSV files (multiple blocks separated by blank lines / repeated headers),
        the list has length > 1 so the user can select which set(s) to plot.
        """
        ext = p.suffix.lower()

        if ext == ".dat":
            x, y = [], []
            for line in p.read_text().splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                parts = s.split()
                if len(parts) < 2:
                    continue
                try:
                    x.append(float(parts[0]))
                    y.append(float(parts[1].replace("D", "E")))
                except ValueError:
                    continue
            if not x:
                raise ValueError("No numeric x y data found in .dat file.")
            x_arr = np.asarray(x, dtype=float)
            y_arr = np.asarray(y, dtype=float)
            return [("", x_arr, {"intensity": y_arr})]

        raw = p.read_text().splitlines()
        if not raw:
            raise ValueError("Empty file.")

        # Detect delimiter robustly (files may start with titles/comments).
        candidates = [",", ";", "\t"]
        score = {c: 0 for c in candidates}
        for line in raw[:80]:
            if not line.strip():
                continue
            for c in candidates:
                score[c] += line.count(c)
        delim = max(score, key=lambda k: score[k]) if any(score.values()) else ","

        rows = list(csv.reader(raw, delimiter=delim))
        if not rows:
            raise ValueError("No rows found.")

        def _is_float(s: str) -> bool:
            s = (s or "").strip()
            if not s:
                return False
            try:
                float(s.replace("D", "E"))
                return True
            except ValueError:
                return False

        def _is_blank_row(r: list[str]) -> bool:
            return (not r) or all((c.strip() == "" for c in r))

        def _is_title_row(r: list[str]) -> bool:
            if _is_blank_row(r):
                return False
            nonempty = [c.strip() for c in r if c.strip() != ""]
            if len(nonempty) != 1:
                return False
            return (not _is_float(nonempty[0])) and (not nonempty[0].lstrip().startswith("#"))

        def _looks_like_header(r: list[str]) -> bool:
            if _is_blank_row(r) or len(r) < 2:
                return False
            if _is_float(r[0]):
                return False
            nonempty = [c.strip() for c in r if c.strip() != ""]
            if len(nonempty) < 2:
                return False
            return any(any(ch.isalpha() for ch in cell) for cell in nonempty)

        def _build_set(header: list[str], cols: list[list[float]], title: str) -> tuple[str, np.ndarray, Dict[str, np.ndarray]]:
            header = [h.strip() for h in (header or [])]
            if len(header) < 2 or any(h == "" for h in header):
                header = ["wn_cm-1"] + [f"col{i}" for i in range(1, len(cols))]
            x_arr = np.asarray(cols[0], dtype=float)
            if x_arr.size == 0:
                raise ValueError("No numeric rows found in CSV set.")
            series: Dict[str, np.ndarray] = {}
            if len(cols) == 2:
                series[header[1] or "intensity"] = np.asarray(cols[1], dtype=float)
            else:
                for i in range(1, len(cols)):
                    name = header[i] if i < len(header) else f"col{i}"
                    name = name or f"col{i}"
                    series[name] = np.asarray(cols[i], dtype=float)
            return (title or "", x_arr, series)

        sets: list[tuple[str, np.ndarray, Dict[str, np.ndarray]]] = []

        # Parse multiple CSV blocks (title row optional, then header row, then numeric rows)
        i = 0
        pending_title: str = ""
        while i < len(rows):
            r = [c.strip() for c in rows[i]]
            if _is_blank_row(r):
                i += 1
                continue
            if r[0].lstrip().startswith("#"):
                i += 1
                continue

            if _is_title_row(r):
                pending_title = (r[0] or "").strip()
                i += 1
                continue

            if _looks_like_header(r):
                header = r
                i += 1
                cols: list[list[float]] = [[] for _ in range(len(header))]

                while i < len(rows):
                    rr = [c.strip() for c in rows[i]]
                    if _is_blank_row(rr):
                        break
                    if rr[0].lstrip().startswith("#"):
                        i += 1
                        continue
                    if _is_title_row(rr) or _looks_like_header(rr):
                        break

                    if len(rr) < len(header):
                        rr = rr + [""] * (len(header) - len(rr))
                    try:
                        vals = [float(c.replace("D", "E")) if c.strip() != "" else None for c in rr[:len(header)]]
                    except ValueError:
                        i += 1
                        continue
                    if vals[0] is None:
                        i += 1
                        continue
                    for j, v in enumerate(vals):
                        cols[j].append(float("nan") if v is None else float(v))
                    i += 1

                if len(cols) >= 2 and len(cols[0]) > 0:
                    sets.append(_build_set(header, cols, pending_title))
                    pending_title = ""
                continue

            i += 1

        # Fallback: plain numeric CSV without headers (or header not detected)
        if not sets:
            first_idx = None
            first_row = None
            for idx, r in enumerate(rows):
                rr = [c.strip() for c in r]
                if _is_blank_row(rr) or (rr and rr[0].lstrip().startswith("#")):
                    continue
                first_idx = idx
                first_row = rr
                break
            if first_row is None or first_idx is None:
                raise ValueError("No data found.")

            if not _is_float(first_row[0]):
                header = [h.strip() for h in first_row]
                data_rows = rows[first_idx + 1 :]
            else:
                ncol = max(2, len(first_row))
                header = ["wn_cm-1"] + [f"col{i}" for i in range(1, ncol)]
                data_rows = rows[first_idx :]

            cols: list[list[float]] = [[] for _ in range(len(header))]
            for r in data_rows:
                rr = [c.strip() for c in r]
                if _is_blank_row(rr) or (rr and rr[0].lstrip().startswith("#")):
                    continue
                if len(rr) < len(header):
                    rr = rr + [""] * (len(header) - len(rr))
                try:
                    vals = [float(c.replace("D", "E")) if c.strip() != "" else None for c in rr[:len(header)]]
                except ValueError:
                    continue
                if vals[0] is None:
                    continue
                for j, v in enumerate(vals):
                    cols[j].append(float("nan") if v is None else float(v))
            if len(cols[0]) == 0:
                raise ValueError("No numeric rows found in CSV.")
            sets.append(_build_set(header, cols, ""))

        return sets
    def _iter_checked_curves(self) -> list[tuple[str, np.ndarray, np.ndarray, str]]:
        """
        Returns a list of curves to plot as:
          (legend_label, x, y, curve_id)
        """
        curves: list[tuple[str, np.ndarray, np.ndarray, str]] = []
        for i in range(self.tw_series.topLevelItemCount()):
            top = self.tw_series.topLevelItem(i)
            if top.checkState(0) != QtCore.Qt.CheckState.Checked:
                continue

            dataset_key = top.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if not dataset_key or dataset_key not in self._datasets_map:
                continue

            ds = self._datasets_map[dataset_key]
            x = np.asarray(ds["x"], dtype=float)
            base = (top.text(0) or "").strip() or Path(str(dataset_key)).stem

            checked_children = []
            for j in range(top.childCount()):
                ch = top.child(j)
                if ch.checkState(0) == QtCore.Qt.CheckState.Checked:
                    checked_children.append(ch)

            for ch in checked_children:
                series_key = str(ch.data(0, QtCore.Qt.ItemDataRole.UserRole))
                y = ds["series"].get(series_key)
                if y is None:
                    continue
                y = np.asarray(y, dtype=float)

                series_label = (ch.text(0) or "").strip() or series_key

                if len(ds["series"]) == 1:
                    legend_label = base
                else:
                    legend_label = f"{base}:{series_label}"

                curve_id = f"{dataset_key}:::{series_key}"
                curves.append((legend_label, x, y, curve_id))

        return curves



    def _apply_results_style(self, ax):
        """Apply frame/grid/background/ticks settings to the given axes."""
        # --- frame / spines ---
        frame = ""
        try:
            frame = str(self.cb_res_frame.currentText())
        except Exception:
            frame = "Box (all spines)"

        if frame.startswith("Half"):
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(True)
            ax.spines["bottom"].set_visible(True)
        elif frame.startswith("Open"):
            for sp in ax.spines.values():
                sp.set_visible(False)
        else:
            for sp in ax.spines.values():
                sp.set_visible(True)

        # --- background ---
        bg = ""
        try:
            bg = str(self.cb_res_bg.currentText()).lower()
        except Exception:
            bg = "default"

        if bg.startswith("white"):
            ax.set_facecolor("white")
            ax.figure.patch.set_facecolor("white")
            ax.figure.patch.set_alpha(1.0)
        elif bg.startswith("transparent"):
            ax.set_facecolor("none")
            ax.figure.patch.set_alpha(0.0)
        else:
            # default matplotlib styling
            ax.set_facecolor("white")
            ax.figure.patch.set_alpha(1.0)

        # --- ticks (major + optional minor) ---
        def _parse_float(s: str):
            s = (s or "").strip()
            if not s:
                return None
            try:
                return float(s)
            except ValueError:
                return None

        xt = None
        yt = None
        
        # Prefer spinboxes (v12+); fall back to text fields if present
        if hasattr(self, "sp_xtick"):
            try:
                v = int(self.sp_xtick.value())
                xt = float(v) if v > 0 else None
            except Exception:
                xt = None
        else:
            xt = _parse_float(self.ed_xtick.text() if hasattr(self, "ed_xtick") else "")
        
        if hasattr(self, "sp_ytick"):
            try:
                v = float(self.sp_ytick.value())
                yt = float(v) if v > 0 else None
            except Exception:
                yt = None
        else:
            yt = _parse_float(self.ed_ytick.text() if hasattr(self, "ed_ytick") else "")

        if xt is not None and xt > 0:
            ax.xaxis.set_major_locator(MultipleLocator(xt))
        else:
            ax.xaxis.set_major_locator(AutoLocator())

        if yt is not None and yt > 0:
            ax.yaxis.set_major_locator(MultipleLocator(yt))
        else:
            ax.yaxis.set_major_locator(AutoLocator())

        minor_on = bool(getattr(self, "cb_minor_ticks", None) and self.cb_minor_ticks.isChecked())
        if minor_on:
            ax.minorticks_on()
            if xt is not None and xt > 0:
                ax.xaxis.set_minor_locator(MultipleLocator(xt / 2.0))
            else:
                ax.xaxis.set_minor_locator(AutoMinorLocator())
            if yt is not None and yt > 0:
                ax.yaxis.set_minor_locator(MultipleLocator(yt / 2.0))
            else:
                ax.yaxis.set_minor_locator(AutoMinorLocator())
        else:
            ax.minorticks_off()

        # --- grid ---
        show_grid = bool(getattr(self, "cb_res_grid", None) and self.cb_res_grid.isChecked())
        alpha = 0.25
        ls = "-"
        lw = 0.8
        try:
            alpha = float(self.sp_grid_alpha.value()) / 100.0
        except Exception:
            pass
        try:
            ls = str(self.cb_grid_ls.currentText())
        except Exception:
            pass
        try:
            lw = float(self.sp_grid_lw.value())
        except Exception:
            pass

        ax.grid(False)
        if show_grid:
            ax.grid(True, which="major", alpha=alpha, linestyle=ls, linewidth=lw)
            if minor_on:
                ax.grid(True, which="minor", alpha=max(0.0, alpha * 0.6), linestyle=ls, linewidth=max(0.1, lw * 0.7))



    def _apply_results_legend(self, ax, ncurves: int):
        """Create/update the legend using the GUI legend style controls."""
        # default behavior if UI controls are missing
        show = True
        maxcurves = 16
        loc = "best"
        fontsize = 8
        ncol = 1
        frameon = True
        frame_alpha = 0.85

        try:
            if hasattr(self, "cb_legend_show"):
                show = bool(self.cb_legend_show.isChecked())
            if hasattr(self, "sp_legend_maxcurves"):
                maxcurves = int(self.sp_legend_maxcurves.value())
            if hasattr(self, "cb_legend_loc"):
                loc = str(self.cb_legend_loc.currentText() or "best")
            if hasattr(self, "sp_legend_font"):
                fontsize = int(self.sp_legend_font.value())
            if hasattr(self, "sp_legend_ncol"):
                ncol = int(self.sp_legend_ncol.value())
            if hasattr(self, "cb_legend_frame"):
                frameon = bool(self.cb_legend_frame.isChecked())
            if hasattr(self, "sp_legend_alpha"):
                frame_alpha = float(self.sp_legend_alpha.value()) / 100.0
        except Exception:
            pass

        # Remove legend if disabled or too many curves
        if (not show) or (ncurves <= 0) or (ncurves > maxcurves):
            leg = ax.get_legend()
            if leg is not None:
                leg.remove()
            return

        handles, labels = ax.get_legend_handles_labels()
        h2, l2 = [], []
        for h, l in zip(handles, labels):
            if not l or l == "_nolegend_":
                continue
            h2.append(h)
            l2.append(l)

        if not l2:
            leg = ax.get_legend()
            if leg is not None:
                leg.remove()
            return

        leg = ax.legend(h2, l2, loc=loc, fontsize=fontsize, ncol=ncol, frameon=frameon)
        if leg is None:
            return

        fr = leg.get_frame()
        if not frameon:
            fr.set_visible(False)
        else:
            fr.set_alpha(frame_alpha)

    def _render_results_axes(self, ax, *, for_export: bool = False):
        """Draw the current Results plot onto any matplotlib Axes."""
        ax.clear()
        curves = self._iter_checked_curves()

        # reset display cache on every draw
        self._display_curves = {}

        if not curves:
            ax.set_title("Add one or more spectrum files to plot")
            ax.set_xlabel("Wavenumber (cm$^{-1}$)")
            ax.set_ylabel("Intensity")
            self._apply_results_style(ax)
            return

        do_norm = bool(self.cb_res_norm.isChecked())
        smooth_n = int(self.sp_res_smooth.value())
        x_offset = float(self.sp_res_offset.value())

        def _parse_float(s: str) -> Optional[float]:
            s = (s or "").strip()
            if not s:
                return None
            try:
                return float(s)
            except ValueError:
                return None

        xmin = _parse_float(self.ed_xmin.text())
        xmax = _parse_float(self.ed_xmax.text())

        fill_curves = bool(getattr(self, "cb_res_fill", None) and self.cb_res_fill.isChecked())
        fill_alpha = 0.25
        try:
            fill_alpha = float(self.sp_res_fill_alpha.value()) / 100.0
        except Exception:
            pass

        for legend_label, x0, y0, curve_id in curves:
            x = np.array(x0, dtype=float) + x_offset
            y = np.array(y0, dtype=float)

            if smooth_n > 1 and y.size >= smooth_n:
                kernel = np.ones(smooth_n, dtype=float) / float(smooth_n)
                y = np.convolve(y, kernel, mode="same")

            if do_norm:
                ymax = np.nanmax(np.abs(y))
                if ymax and np.isfinite(ymax) and ymax > 0:
                    y = y / ymax

            (line,) = ax.plot(x, y, label=legend_label)
            if fill_curves and fill_alpha > 0:
                if self.cb_logy.isChecked():
                    mask = np.isfinite(x) & np.isfinite(y) & (y > 0)
                    pos = y[np.isfinite(y) & (y > 0)]
                    baseline = float(pos.min()) * 0.5 if pos.size else 1e-12
                else:
                    mask = np.isfinite(x) & np.isfinite(y)
                    baseline = 0.0
                if mask.any():
                    ax.fill_between(
                        x[mask],
                        y[mask],
                        baseline,
                        color=line.get_color(),
                        alpha=fill_alpha,
                        linewidth=0,
                        label="_nolegend_",
                        zorder=max(line.get_zorder() - 1, 0),
                    )
            self._display_curves[curve_id] = {"label": legend_label, "x": x, "y": y}

        if xmin is not None or xmax is not None:
            ax.set_xlim(left=xmin if xmin is not None else None, right=xmax if xmax is not None else None)

        if self.cb_logy.isChecked():
            ax.set_yscale("log")
        # ----- highlighted regions -----
        if self.cb_shade.isChecked() and getattr(self, "_shade_regions", None):
            for reg in list(self._shade_regions):
                try:
                    cid = reg.get("curve_id")
                    xmin_s = float(reg.get("xmin"))
                    xmax_s = float(reg.get("xmax"))
                    data = self._display_curves.get(cid)
                    if data is None:
                        continue
                    x = data["x"]
                    y = data["y"]
                    lo, hi = (xmin_s, xmax_s) if xmin_s <= xmax_s else (xmax_s, xmin_s)
                    mask = (x >= lo) & (x <= hi)
                    if not mask.any():
                        continue
                    alpha = float(reg.get("opacity", 0.25))
                    color = str(reg.get("color", self._shade_color_hex))
                    if self.cb_logy.isChecked():
                        pos = y[np.isfinite(y) & (y > 0)]
                        baseline = float(pos.min()) * 0.5 if pos.size else 1e-12
                    else:
                        baseline = 0.0
                    ax.fill_between(x[mask], y[mask], baseline, color=color, alpha=alpha, linewidth=0, label="_nolegend_")
                except Exception:
                    # never let shading break plotting
                    continue

        # ----- peak markers (A/B) -----
        # Skip during export so the saved figure does not include selection markers.
        if not for_export:

            def _mark_peak(peak, tag: str):
                if peak is None:
                    return
                cid = peak.get("curve_id")
                xpk = float(peak.get("x"))
                data = self._display_curves.get(cid)
                if data is None:
                    return
                x = data["x"]
                y = data["y"]
                if x.size == 0:
                    return
                idx = int(np.nanargmin(np.abs(x - xpk)))
                xp = float(x[idx])
                yp = float(y[idx])
                ms = 6
                fs = 9
                try:
                    ms = int(self.sp_peak_marker_size.value())
                except Exception:
                    pass
                try:
                    fs = int(self.sp_peak_marker_font.value())
                except Exception:
                    pass
                ax.plot([xp], [yp], marker="o", markersize=ms, linestyle="None", label="_nolegend_")
                ax.axvline(xp, linewidth=1.0, alpha=0.5, label="_nolegend_")
                ax.annotate(tag, xy=(xp, yp), xytext=(6, 6), textcoords="offset points",
                            fontsize=fs, fontweight="bold")

            _mark_peak(self._peak_a, "A")
            _mark_peak(self._peak_b, "B")


        ax.set_xlabel("Wavenumber (cm$^{-1}$)")
        ax.set_ylabel("Intensity")
        self._apply_results_legend(ax, ncurves=len(curves))
        self._apply_results_style(ax)

    
    def _update_results_plot(self):
        # Full redraw (data/layout)
        self._render_results_axes(self.ax)
        self._apply_results_view(self.ax)
        self.canvas.draw_idle()

        # refresh analysis curve list (uses cached displayed curves)
        self._analysis_refresh_curve_list()

        # Pop-out (if open)
        if self._popout_win is not None and self._popout_win.isVisible():
            self._render_results_axes(self._popout_win.ax)
            self._apply_results_view(self._popout_win.ax)
            self._popout_win.canvas.draw_idle()

    def _update_results_style_only(self):
        try:
            self._apply_results_style(self.ax)
            self._apply_results_legend(self.ax, ncurves=len(getattr(self, "_display_curves", {})))
            self.canvas.draw_idle()

            if self._popout_win is not None and self._popout_win.isVisible():
                self._apply_results_style(self._popout_win.ax)
                self._apply_results_legend(self._popout_win.ax, ncurves=len(getattr(self, "_display_curves", {})))
                self._popout_win.canvas.draw_idle()
        except Exception:
            # If anything gets out of sync, fall back to a full redraw.
            self._update_results_plot()

    def _store_results_view(self, ax):
        """Remember the current zoom/pan view so we can keep it after redraws."""
        try:
            self._res_view_xlim = ax.get_xlim()
            self._res_view_ylim = ax.get_ylim()
        except Exception:
            return

    def _apply_results_view(self, ax):
        """Restore last remembered view, unless the user forced x-range via fields."""
        try:
            if (self.ed_xmin.text().strip() or self.ed_xmax.text().strip()):
                return
        except Exception:
            pass

        if getattr(self, "_res_view_xlim", None) is None or getattr(self, "_res_view_ylim", None) is None:
            return

        self._syncing_limits = True
        try:
            ax.set_xlim(self._res_view_xlim)
            # y-lims can fail on log scale if <= 0
            try:
                y0, y1 = self._res_view_ylim
                if ax.get_yscale() == "log" and (y0 <= 0 or y1 <= 0):
                    return
                ax.set_ylim(self._res_view_ylim)
            except Exception:
                pass
        finally:
            self._syncing_limits = False

    def _on_embedded_limits_changed(self, ax):
        """When the user zooms/pans the embedded plot, mirror limits to the popout."""
        if getattr(self, "_syncing_limits", False):
            return
        self._store_results_view(ax)

        if self._popout_win is None or (not self._popout_win.isVisible()):
            return

        self._syncing_limits = True
        try:
            if getattr(self, "_res_view_xlim", None) is not None:
                self._popout_win.ax.set_xlim(self._res_view_xlim)
            if getattr(self, "_res_view_ylim", None) is not None:
                try:
                    y0, y1 = self._res_view_ylim
                    if self._popout_win.ax.get_yscale() == "log" and (y0 <= 0 or y1 <= 0):
                        pass
                    else:
                        self._popout_win.ax.set_ylim(self._res_view_ylim)
                except Exception:
                    pass
            self._popout_win.canvas.draw_idle()
        finally:
            self._syncing_limits = False

    def _on_popout_limits_changed(self, ax):
        """When the user zooms/pans the popout plot, mirror limits to the embedded plot."""
        if getattr(self, "_syncing_limits", False):
            return
        self._store_results_view(ax)

        self._syncing_limits = True
        try:
            if getattr(self, "_res_view_xlim", None) is not None:
                self.ax.set_xlim(self._res_view_xlim)
            if getattr(self, "_res_view_ylim", None) is not None:
                try:
                    y0, y1 = self._res_view_ylim
                    if self.ax.get_yscale() == "log" and (y0 <= 0 or y1 <= 0):
                        pass
                    else:
                        self.ax.set_ylim(self._res_view_ylim)
                except Exception:
                    pass
            self.canvas.draw_idle()
        finally:
            self._syncing_limits = False
    def _open_popout_spectrum(self):
        """Open (or focus) a large detached spectrum window."""
        if self._popout_win is None:
            self._popout_win = SpectrumPopoutWindow(self)
            self._popout_win.destroyed.connect(lambda *a: setattr(self, "_popout_win", None))

            # Mirror zoom/pan between embedded plot and popout
            try:
                self._popout_win.ax.callbacks.connect('xlim_changed', self._on_popout_limits_changed)
                self._popout_win.ax.callbacks.connect('ylim_changed', self._on_popout_limits_changed)
            except Exception:
                pass

            # Store the connection id on the popout window to avoid double-connecting.
            try:
                if not hasattr(self._popout_win, "_mpl_click_cid") or self._popout_win._mpl_click_cid is None:
                    self._popout_win._mpl_click_cid = self._popout_win.canvas.mpl_connect(
                        'button_press_event', self._on_results_plot_click
                    )
            except Exception:
                pass

        self._popout_win.show()
        self._popout_win.raise_()
        self._popout_win.activateWindow()

        # Immediately sync plot + view
        self._render_results_axes(self._popout_win.ax)
        self._apply_results_view(self._popout_win.ax)
        self._popout_win.canvas.draw_idle()


    def _save_results_plot(self):
        default_png = "spectrum.png"
        default_svg = "spectrum.svg"

        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        if not wd.exists():
            wd = Path.cwd()

        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save plot",
            str(wd / default_svg),
            "SVG (*.svg);;PNG (*.png)",
        )
        if not path:
            return

        p = Path(path)
        # If user omitted extension, add based on filter
        if p.suffix.lower() not in (".png", ".svg"):
            if "SVG" in selected_filter:
                p = p.with_suffix(".svg")
            else:
                p = p.with_suffix(".png")

        try:
            transparent_bg = False
            try:
                transparent_bg = (hasattr(self, 'cb_res_bg') and str(self.cb_res_bg.currentText()).lower().startswith('transparent'))
            except Exception:
                transparent_bg = False

            # Save what you see in the *popout*
            src_fig = self.fig
            src_ax = self.ax
            try:
                if getattr(self, "_popout_win", None) is not None:
                    # Use popout figure sizing + current view when available
                    src_fig = self._popout_win.fig
                    src_ax = self._popout_win.ax
                else:
                    src_fig = Figure(figsize=(10, 7), dpi=100)
                    src_ax = self.ax
            except Exception:
                src_fig = Figure(figsize=(10, 7), dpi=100)
                src_ax = self.ax
            # Create an off-screen figure that matches the popout size,
            # and re-render the plot without peak-selection markers for clean exports.
            export_fig = Figure(figsize=src_fig.get_size_inches(), dpi=src_fig.dpi)
            export_ax = export_fig.add_subplot(111)
            self._render_results_axes(export_ax, for_export=True)

            try:
                export_ax.set_xlim(src_ax.get_xlim())
            except Exception:
                pass
            try:
                y0, y1 = src_ax.get_ylim()
                if export_ax.get_yscale() == "log" and (y0 <= 0 or y1 <= 0):
                    pass
                else:
                    export_ax.set_ylim((y0, y1))
            except Exception:
                pass

            if p.suffix.lower() == ".svg":
                export_fig.savefig(str(p), format="svg", bbox_inches="tight", transparent=transparent_bg)
            else:
                export_fig.savefig(str(p), format="png", dpi=200, bbox_inches="tight", transparent=transparent_bg)
            QtWidgets.QMessageBox.information(self, "Saved", f"Plot saved:\n{p}")
        except Exception as e:
            self._err("Save failed", str(e))

    def _export_results_csv(self):
        """Export the *currently plotted* spectra (as displayed) to a simple, wide CSV.

        The export is Excel-friendly:

        1) SUMMARY BLOCK (few rows)
           Columns:
             dataset, x_peak, y_peak, fwhm, fwhm_left, fwhm_right,
             view_xmin, view_xmax, norm_max_to_1, smooth_window_pts, x_offset_cm-1, log_y

        2) DATA BLOCK (wide table)
           First column is x, then one column per dataset (y values).
           All curves are interpolated onto a common x-grid.

        """
        default_csv = "spectrum_export.csv"

        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        if not wd.exists():
            wd = Path.cwd()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export plotted spectra to CSV",
            str(wd / default_csv),
            "CSV (*.csv)",
        )
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() != ".csv":
            p = p.with_suffix(".csv")

        try:
            # Ensure display cache exists (it is refreshed on every redraw).
            if not getattr(self, "_display_curves", None):
                self._update_results_plot()

            # Visible range: popout if open, otherwise embedded
            src_ax = self.ax
            try:
                if getattr(self, "_popout_win", None) is not None and self._popout_win.isVisible():
                    src_ax = self._popout_win.ax
            except Exception:
                pass

            x0, x1 = src_ax.get_xlim()
            view_xmin, view_xmax = (float(x0), float(x1)) if x0 <= x1 else (float(x1), float(x0))

            # Provenance (current display settings)
            do_norm = bool(self.cb_res_norm.isChecked())
            smooth_n = int(self.sp_res_smooth.value())
            x_offset = float(self.sp_res_offset.value())
            logy = bool(self.cb_logy.isChecked())

            # Collect visible curves
            curves = []
            for cid, d in (self._display_curves or {}).items():
                label = str(d.get("label", cid))
                x = np.asarray(d.get("x", []), dtype=float)
                y = np.asarray(d.get("y", []), dtype=float)

                m = np.isfinite(x) & np.isfinite(y) & (x >= view_xmin) & (x <= view_xmax)
                x_vis = x[m]
                y_vis = y[m]

                # If zoom is extremely narrow and removes everything, fall back to full displayed arrays
                if x_vis.size < 3:
                    m = np.isfinite(x) & np.isfinite(y)
                    x_vis = x[m]
                    y_vis = y[m]

                if x_vis.size < 3:
                    continue

                # sort by x for interpolation/metrics
                order = np.argsort(x_vis)
                x_vis = x_vis[order]
                y_vis = y_vis[order]

                curves.append((cid, label, x_vis, y_vis))

            if not curves:
                raise RuntimeError("No curves available to export (nothing is plotted).")

            # Pick reference x-grid: densest visible curve
            ref_cid, ref_label, ref_x, ref_y = max(curves, key=lambda t: int(t[2].size))
            ref_x = np.unique(ref_x)  # sorted unique x

            # Build unique column headers
            used = {}
            headers = []
            for cid, label, *_ in curves:
                key = label
                used[key] = used.get(key, 0) + 1
                if used[key] > 1:
                    key = f"{label} ({cid})"
                headers.append(key)

            # Precompute metrics (no areas)
            metrics_rows = []
            for (cid, label, x_vis, y_vis), colname in zip(curves, headers):
                met = self._compute_peak_metrics(x_vis, y_vis)
                metrics_rows.append([
                    colname,
                    met.get("x_peak", float("nan")),
                    met.get("y_peak", float("nan")),
                    met.get("fwhm", float("nan")),
                    met.get("fwhm_left", float("nan")),
                    met.get("fwhm_right", float("nan")),
                    view_xmin,
                    view_xmax,
                    int(do_norm),
                    smooth_n,
                    x_offset,
                    int(logy),
                ])

            # Interpolate all curves onto ref_x
            ycols = []
            for cid, label, x_vis, y_vis in curves:
                # np.interp requires increasing x (we ensured sorting)
                yi = np.interp(ref_x, x_vis, y_vis, left=np.nan, right=np.nan)
                ycols.append(yi)

            # Write CSV: summary block + blank line + wide data block
            with p.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)

                w.writerow([
                    "dataset", "x_peak", "y_peak", "fwhm", "fwhm_left", "fwhm_right",
                    "view_xmin", "view_xmax", "norm_max_to_1", "smooth_window_pts", "x_offset_cm-1", "log_y"
                ])
                for row in metrics_rows:
                    w.writerow(row)

                w.writerow([])  # blank separator row

                w.writerow(["x"] + headers)
                for i, xi in enumerate(ref_x.tolist()):
                    row = [float(xi)]
                    for yi in ycols:
                        v = yi[i]
                        row.append("" if not np.isfinite(v) else float(v))
                    w.writerow(row)

            QtWidgets.QMessageBox.information(self, "Exported", f"CSV exported:\n{p}")
        except Exception as e:
            self._err("CSV export failed", str(e))

    @staticmethod
    def _compute_peak_metrics(x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Compute peak x/y, FWHM around the maximum, and areas (trap).
        """
        # default NaNs
        out = {
            "x_peak": float("nan"),
            "y_peak": float("nan"),
            "fwhm": float("nan"),
            "fwhm_left": float("nan"),
            "fwhm_right": float("nan"),
            "area_total": float("nan"),
            "area_fwhm": float("nan"),
            "area_fwhm_norm": float("nan"),
        }

        if x is None or y is None:
            return out
        x = np.asarray(x, dtype=float).ravel()
        y = np.asarray(y, dtype=float).ravel()
        if x.size < 3 or y.size != x.size:
            return out

        m = np.isfinite(x) & np.isfinite(y)
        x = x[m]
        y = y[m]
        if x.size < 3:
            return out

        # Ensure increasing x for interp/integration
        order = np.argsort(x)
        x = x[order]
        y = y[order]

        # Peak (maximum)
        idx = int(np.argmax(y))
        xpk = float(x[idx])
        ypk = float(y[idx])
        out["x_peak"] = xpk
        out["y_peak"] = ypk

        # Total area over provided range (absolute value)
        try:
            area_total = float(np.trapz(y, x))
            if np.isfinite(area_total):
                out["area_total"] = abs(area_total)
        except Exception:
            pass

        # FWHM around maximum (requires positive peak height)
        if not np.isfinite(ypk) or ypk <= 0:
            return out

        half = 0.5 * ypk
        xl = float("nan")
        xr = float("nan")

        # left crossing
        for i in range(idx, 0, -1):
            y1 = float(y[i])
            y0 = float(y[i - 1])
            if (y1 >= half and y0 < half) or (y1 <= half and y0 > half):
                denom = (y1 - y0)
                if denom != 0:
                    xl = float(x[i - 1] + (half - y0) * (x[i] - x[i - 1]) / denom)
                else:
                    xl = float(x[i - 1])
                break

        # right crossing
        for i in range(idx, x.size - 1):
            y0 = float(y[i])
            y1 = float(y[i + 1])
            if (y0 >= half and y1 < half) or (y0 <= half and y1 > half):
                denom = (y1 - y0)
                if denom != 0:
                    xr = float(x[i] + (half - y0) * (x[i + 1] - x[i]) / denom)
                else:
                    xr = float(x[i + 1])
                break

        if np.isfinite(xl) and np.isfinite(xr):
            out["fwhm_left"] = xl
            out["fwhm_right"] = xr
            out["fwhm"] = abs(xr - xl)

            # area under the peak within FWHM window (absolute)
            try:
                lo, hi = (xl, xr) if xl <= xr else (xr, xl)
                lo = max(lo, float(x[0]))
                hi = min(hi, float(x[-1]))
                if hi > lo:
                    mask = (x >= lo) & (x <= hi)
                    xs = x[mask]
                    ys = y[mask]
                    y_lo = float(np.interp(lo, x, y))
                    y_hi = float(np.interp(hi, x, y))
                    x_int = np.concatenate(([lo], xs, [hi]))
                    y_int = np.concatenate(([y_lo], ys, [y_hi]))
                    o2 = np.argsort(x_int)
                    x_int = x_int[o2]
                    y_int = y_int[o2]
                    area_fwhm = float(np.trapz(y_int, x_int))
                    out["area_fwhm"] = abs(area_fwhm)
                    if np.isfinite(out["area_total"]) and out["area_total"] > 0:
                        out["area_fwhm_norm"] = out["area_fwhm"] / out["area_total"]
            except Exception:
                pass

        return out



    # ---- Analysis (Results) ----
    def _analysis_refresh_curve_list(self):
        if not hasattr(self, "cb_an_curve"):
            return
        prev = self.cb_an_curve.currentData()
        self.cb_an_curve.blockSignals(True)
        try:
            self.cb_an_curve.clear()
            for cid, d in self._display_curves.items():
                self.cb_an_curve.addItem(str(d.get("label", cid)), cid)
            # restore previous selection if possible
            if prev is not None:
                idx = self.cb_an_curve.findData(prev)
                if idx >= 0:
                    self.cb_an_curve.setCurrentIndex(idx)
        finally:
            self.cb_an_curve.blockSignals(False)

    def _analysis_set_color_button(self):
        if not hasattr(self, "btn_shade_color"):
            return
        self.btn_shade_color.setStyleSheet(
            f"background: {self._shade_color_hex}; border: 1px solid #1f2937; border-radius: 10px; padding: 8px 12px;"
        )

    def _analysis_choose_color(self):
        col = QtWidgets.QColorDialog.getColor(QtGui.QColor(self._shade_color_hex), self, "Choose fill color")
        if not col.isValid():
            return
        self._shade_color_hex = col.name()
        self._analysis_set_color_button()
        self._analysis_apply_shade_style_to_regions()
        self._update_results_plot()

    def _analysis_apply_shade_style_to_regions(self):
        if not getattr(self, "_shade_regions", None):
            return
        alpha = float(self.sp_shade_alpha.value()) / 100.0
        for reg in self._shade_regions:
            reg["color"] = self._shade_color_hex
            reg["opacity"] = alpha

    def _analysis_on_shade_style_changed(self, *args):
        self._analysis_apply_shade_style_to_regions()
        self._schedule_results_update(full=True)

    def _analysis_set_pick_mode(self, which: str):
        """Arm the next mouse click to pick peak A or B."""
        which = str(which).upper()
        if which not in ("A", "B"):
            return
        self._analysis_pick_mode = which
        # hint for the user
        label = self.cb_an_curve.currentText() if hasattr(self, "cb_an_curve") else ""
        if hasattr(self, "lbl_pick_status"):
            self.lbl_pick_status.setText(
                f"Click near a peak on the plot (embedded or popout) to pick peak {which} (curve: {label})"
            )

    def _on_results_plot_click(self, event):
        # Only react on left-click inside the axes and only if picking is armed
        if event is None or getattr(event, "inaxes", None) is None:
            return
        if self._analysis_pick_mode is None:
            return
        if event.button != 1:
            return
        if event.xdata is None:
            return

        # which curve to use for snapping
        cid = None
        if hasattr(self, "cb_an_curve"):
            cid = self.cb_an_curve.currentData()
        if cid is None and self._display_curves:
            cid = next(iter(self._display_curves.keys()))

        if cid is None or cid not in self._display_curves:
            return

        x = np.asarray(self._display_curves[cid]["x"], dtype=float)
        y = np.asarray(self._display_curves[cid]["y"], dtype=float)

        xpk, ypk = self._analysis_snap_to_peak(x, y, float(event.xdata))
        if xpk is None:
            return

        peak = {"curve_id": cid, "x": float(xpk)}
        if self._analysis_pick_mode == "A":
            self._peak_a = peak
            msg = f"Peak A: x={xpk:.3f} cm^-1, y={ypk:.6g}  (curve: {self._display_curves[cid]['label']})"
        else:
            self._peak_b = peak
            msg = f"Peak B: x={xpk:.3f} cm^-1, y={ypk:.6g}  (curve: {self._display_curves[cid]['label']})"

        if hasattr(self, "txt_analysis"):
            self.txt_analysis.appendPlainText(msg)

        self._analysis_pick_mode = None
        if hasattr(self, "lbl_pick_status"):
            self.lbl_pick_status.setText("")

        self._update_results_plot()

    def _analysis_snap_to_peak(self, x: np.ndarray, y: np.ndarray, x_click: float, window_pts: int = 60):
        """Snap a click x to nearest local maximum within a point window."""
        if x.size == 0:
            return None, None
        idx0 = int(np.nanargmin(np.abs(x - x_click)))
        lo = max(0, idx0 - window_pts)
        hi = min(x.size, idx0 + window_pts + 1)
        if hi - lo < 3:
            return float(x[idx0]), float(y[idx0])

        seg = y[lo:hi]
        # Use argmax on y; if spectrum might be negative, user likely still wants maxima.
        j = int(np.nanargmax(seg))
        idx = lo + j
        return float(x[idx]), float(y[idx])

    def _analysis_compute_fwhm(self):
        try:
            if self._peak_a is None:
                self._err("Missing peak A", "Pick peak A first.")
                return
            cid = self._peak_a["curve_id"]
            data = self._display_curves.get(cid)
            if data is None:
                self._err("Curve not available", "The selected curve is not currently plotted.")
                return

            x = np.asarray(data["x"], dtype=float)
            y = np.asarray(data["y"], dtype=float)
            xpk = float(self._peak_a["x"])

            res = self._analysis_fwhm(x, y, xpk)
            if res is None:
                self._err("FWHM failed", "Could not determine FWHM (peak may be truncated by range or too noisy).")
                return

            xL, xR, fwhm = res
            hwhm = 0.5 * fwhm            # store region for optional shading (append; keep previous highlights)
            alpha = float(self.sp_shade_alpha.value()) / 100.0
            self._shade_regions.append({"curve_id": cid, "xmin": float(xL), "xmax": float(xR), "color": self._shade_color_hex, "opacity": alpha})

            # area under peak within FWHM
            mask = (x >= xL) & (x <= xR)
            trap = getattr(np, "trapezoid", None) or getattr(np, "trapz", None)
            area = float(trap(y[mask], x[mask])) if (mask.any() and trap is not None) else float("nan")

            msg = (
                f"FWHM (A): {fwhm:.3f} cm^-1  (HWHM={hwhm:.3f})\n"
                f"  xL={xL:.3f}, xR={xR:.3f}, area≈{area:.6g}  (curve: {data['label']})"
            )
            if hasattr(self, "txt_analysis"):
                self.txt_analysis.appendPlainText(msg)

            self._update_results_plot()

        except Exception as e:
            self._err('FWHM error', str(e))
            return

    def _analysis_fwhm(self, x: np.ndarray, y: np.ndarray, x_peak: float):
        """Compute FWHM around a peak located near x_peak. Returns (xL, xR, width)."""
        if x.size < 5:
            return None
        ipk = int(np.nanargmin(np.abs(x - x_peak)))
        ypk = float(y[ipk])
        half = 0.5 * ypk

        # left crossing
        i = ipk
        while i > 0 and (np.isnan(y[i]) or y[i] > half):
            i -= 1
        if i == 0:
            return None
        # interpolate between i and i+1 (y[i] <= half < y[i+1])
        y1, y2 = float(y[i]), float(y[i + 1])
        x1, x2 = float(x[i]), float(x[i + 1])
        if y2 == y1:
            return None
        xL = x1 + (half - y1) * (x2 - x1) / (y2 - y1)

        # right crossing
        i = ipk
        while i < x.size - 1 and (np.isnan(y[i]) or y[i] > half):
            i += 1
        if i >= x.size - 1:
            return None
        # interpolate between i-1 and i (y[i] <= half < y[i-1])
        y1, y2 = float(y[i - 1]), float(y[i])
        x1, x2 = float(x[i - 1]), float(x[i])
        if y2 == y1:
            return None
        xR = x1 + (half - y1) * (x2 - x1) / (y2 - y1)

        return float(xL), float(xR), float(xR - xL)

    def _analysis_compute_distance(self):
        if self._peak_a is None or self._peak_b is None:
            self._err("Missing peaks", "Pick both peak A and peak B first.")
            return
        xA = float(self._peak_a["x"])
        xB = float(self._peak_b["x"])
        dist = abs(xB - xA)
        msg = f"Distance A–B: {dist:.3f} cm^-1   (A={xA:.3f}, B={xB:.3f})"
        if hasattr(self, "txt_analysis"):
            self.txt_analysis.appendPlainText(msg)
        # no need to redraw

    def _analysis_clear(self):
        self._analysis_pick_mode = None
        self._peak_a = None
        self._peak_b = None
        self._shade_regions = []
        if hasattr(self, "lbl_pick_status"):
            self.lbl_pick_status.setText("")
        if hasattr(self, "txt_analysis"):
            self.txt_analysis.appendPlainText("Cleared markers/highlight.")
        self._update_results_plot()


    def _analysis_undo_highlight(self):
        if not getattr(self, '_shade_regions', None):
            return
        self._shade_regions.pop()
        if hasattr(self, 'txt_analysis'):
            self.txt_analysis.appendPlainText('Removed last highlight.')
        self._update_results_plot()


    # ---------------------
    # Page: About
    # ---------------------
    def _build_page_about(self, lay: QtWidgets.QVBoxLayout):
        card = QtWidgets.QFrame()
        card.setObjectName("AboutCard")
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QtWidgets.QLabel("Flying Nimbus GUI")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        v.addWidget(title)

        txt = QtWidgets.QLabel(
        "• See Documentation: \n"
        "• You like it or use it? Please CITE: \n"
        "• Authors: Giacomo Mandelli, Giacomo Botti "
        )
        txt.setStyleSheet("color: #cbd5e1;")
        v.addWidget(txt)

        btn = QtWidgets.QPushButton("Open working directory")
        btn.clicked.connect(self._open_workdir)
        v.addWidget(btn)
        v.addStretch(1)

        lay.addWidget(card)
        lay.addStretch(1)


    # ---------------------
    # Build core configuration (kwargs for nimbus.Config)
    # ---------------------
    def build_cfg_kwargs(self) -> Dict[str, Any]:
        """Collect current UI values and build a dict compatible with flying_nimbus_core.Config.

        Notes:
          - nat is always read from the XYZ file (first line).
          - Paths are kept as typed (can be relative); core is run inside workdir.
          - This returns *only* core parameters; workdir is handled separately by the worker.
        """
        xyz = (self.ed_xyz.text() or "").strip()
        nat = safe_read_nat_from_xyz(str(self._resolve_in_workdir(xyz)))

        coord = str(self.cb_coord.currentText() or "nm")
        modes = parse_range_list(self.ed_modes.text()) if coord == "nm" else parse_range_list(self.ed_modes.text())
        atoms = parse_int_list(self.ed_atoms.text())

        cfg: Dict[str, Any] = {
            # system
            "nat": int(nat),
            "nrototrasl": int(self.cb_nrt.currentText() or 6),

            # time/correlation
            "nstart": int(self.sp_nstart.value()),
            "ncorr": int(self.sp_ncorr.value()),
            "nbeads": int(self.sp_nbeads.value()),
            "nbeadsstep": int(self.sp_nbeadsstep.value()),
            "dt": float(self.sp_dt.value()),

            # spectrum grid
            "init_wnumb": float(self.sp_init.value()),
            "spec_res": float(self.sp_res.value()),
            "wnumb_span": float(self.sp_span.value()),

            # switches
            "ta": bool(self.cb_ta.isChecked()),
            "coord": coord,

            # damping
            "alpha_pow": float(self.sp_alpha_pow.value()),
            "alpha_dip": float(self.sp_alpha_dip.value()),

            # selection
            "modes": list(modes),
            "atoms": list(atoms),

            # files
            "zmat_filename": xyz,
            "hess_filename": (self.ed_hess.text() or "").strip(),
            "traj_filename": (self.ed_traj.text() or "").strip(),

            # cnorm control
            "readcnorm": int(self.cb_readcnorm.currentText() or 0),
            "cnorm_path": ensure_cnorm_path(self.ed_cnorm.text()),
            "rm_cnorm": bool(self.cb_rm_cnorm.isChecked()),

            # output
            "root_out_filename": (self.ed_out_prefix.text() or "QCT_").strip() or "QCT_",

            # plotting / csv
            "plot": bool(self.cb_plot.isChecked()),
            "plot_dir": (self.ed_plotdir.text() or ".").strip() or ".",
            "plot_dpi": int(self.sp_plotdpi.value()),
            "plot_logy": False,
            "plot_show": False,

            "excel": bool(self.cb_excel.isChecked()),
            "excel_sep": normalize_sep(self.ed_excel_sep.text()),
            "excel_merge": bool(self.cb_excel_merge.isChecked()),

            # post-processing
            "freq_offset": float(self.sp_freq_offset.value()),
            "norm1": bool(self.cb_norm1.isChecked()),
        }
        return cfg

    def pseudo_command(self) -> str:
        # For debugging / reproducibility. Safe even if nat not ready.
        cfg = self.build_cfg_kwargs()
        xyz = (cfg["zmat_filename"] or "").strip()
        if not xyz or not self._resolve_in_workdir(xyz).is_file():
            return "Select an XYZ file to preview configuration…"
        if cfg["nat"] <= 0:
            return "Could not read nat from XYZ."
        parts = ["flying_nimbus_core"]
        parts += ["-N", str(cfg["nat"])]
        parts += ["--nrototrasl", str(cfg["nrototrasl"])]
        parts += ["--nstart", str(cfg["nstart"]), "--ncorr", str(cfg["ncorr"])]
        parts += ["--nbeads", str(cfg["nbeads"]), "--nbeadsstep", str(cfg["nbeadsstep"])]
        parts += ["--dt", str(cfg["dt"])]
        parts += ["--init-wnumb", str(cfg["init_wnumb"]), "--spec-res", str(cfg["spec_res"]), "--wnumb-span", str(cfg["wnumb_span"])]
        parts += ["--coord", cfg["coord"]]
        if cfg["ta"]:
            parts += ["--ta"]
        parts += ["--alpha-pow", str(cfg["alpha_pow"]), "--alpha-dip", str(cfg["alpha_dip"])]
        if cfg["modes"]:
            parts += ["--modes"] + [str(x) for x in cfg["modes"]]
        if cfg["atoms"]:
            parts += ["--atoms"] + [str(x) for x in cfg["atoms"]]
        parts += ["--xyz", cfg["zmat_filename"], "--traj", cfg["traj_filename"]]
        parts += ["--readcnorm", str(cfg["readcnorm"]), "--cnorm", cfg["cnorm_path"]]
        if cfg["hess_filename"]:
            parts += ["--hess", cfg["hess_filename"]]
        parts += ["-o", cfg["root_out_filename"]]
        if cfg["plot"]:
            parts += ["--plot", "--plot-dir", cfg["plot_dir"], "--plot-dpi", str(cfg["plot_dpi"])]
        if cfg["excel"]:
            parts += ["--excel", "--excel-sep", "tab" if cfg["excel_sep"] == "\t" else cfg["excel_sep"]]
            if cfg["excel_merge"]:
                parts += ["--excel-merge"]
        if abs(cfg["freq_offset"]) > 0.0:
            parts += ["--freq-offset", str(cfg["freq_offset"])]
        if cfg["norm1"]:
            parts += ["--norm1"]
        if cfg.get("rm_cnorm", False):
            parts += ["--rm-cnorm"]
        return " ".join(parts)

    def _update_preview_safe(self):
        try:
            self.txt_preview.setPlainText(self.pseudo_command())
        except Exception:
            self.txt_preview.setPlainText("Preview unavailable:\n" + traceback.format_exc())

    def _refresh_nat_badge(self):
        nat = safe_read_nat_from_xyz(str(self._resolve_in_workdir(self.ed_xyz.text())))
        self.lbl_nat.setText(f"nat: {nat}" if nat > 0 else "nat: —")

    def _on_any_change(self, *args):
        self._refresh_nat_badge()
        self._update_preview_safe()
        self._save_settings()

    # ---------------------
    # Validation
    # ---------------------
    def validate_inputs(self) -> bool:
        cfg = self.build_cfg_kwargs()
        # workdir
        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        if not wd.exists():
            self._err("Invalid working directory", f"Directory does not exist: {wd}")
            return False
        # xyz
        xyz = self._resolve_in_workdir(cfg["zmat_filename"])
        if not xyz.is_file():
            self._err("Missing XYZ", "Please select an existing equilibrium XYZ file.")
            return False
        if cfg["nat"] <= 0:
            self._err("Invalid XYZ", "Could not read nat from the XYZ file.")
            return False
        # traj
        traj = self._resolve_in_workdir(cfg["traj_filename"])
        if not traj.is_file():
            self._err("Missing trajectory", "Please select an existing trajectory file.")
            return False
        # readcnorm logic
        if cfg["readcnorm"] == 0:
            hess = self._resolve_in_workdir(cfg["hess_filename"])
            if not hess.is_file():
                self._err("Missing Hessian", "Hessian is required when readcnorm = 0.")
                return False
        else:
            cn = self._resolve_in_workdir(cfg["cnorm_path"])
            if not cn.is_file():
                self._err("Missing cnorm", f"readcnorm = 1 but cnorm file not found: {cn}")
                return False
        # nm requires modes
        if cfg["coord"] == "nm" and not cfg["modes"]:
            self._err("Missing modes", "coord = nm requires a non-empty modes list.")
            return False
        # rm cnorm safety
        cn = self._resolve_in_workdir(cfg["cnorm_path"])
        if cfg["readcnorm"] == 0 and cn.exists() and cn.is_dir():
            self._err("Invalid cnorm path", "cnorm path must be a file name, not a directory.")
            return False
        return True

    def _err(self, title: str, msg: str):
        QtWidgets.QMessageBox.critical(self, title, msg)

    # ---------------------
    # Run / stop
    # ---------------------
    def _set_running(self, running: bool):
        self.act_run.setEnabled(not running)
        self.act_stop.setEnabled(running)
        self.sidebar.setEnabled(not running)

    def _run(self):
        if self.worker is not None and self.worker.isRunning():
            QtWidgets.QMessageBox.information(self, "Already running", "A run is already in progress.")
            return
        if not self.validate_inputs():
            return

        cfg = self.build_cfg_kwargs()
        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()

        self.txt_log.clear()
        self.txt_log.appendPlainText(self.pseudo_command())
        self.txt_log.appendPlainText(f"\n[cwd: {wd}]\n")

        self.worker = NimbusWorker(cfg, wd, overwrite_cnorm=bool(self.cb_rm_cnorm.isChecked()), parent=self)
        self.worker.log.connect(self._append_log)
        self.worker.done.connect(self._on_done)
        self.worker.start()
        self._set_running(True)

    def _stop(self):
        if self.worker is None:
            return
        self.worker.request_cancel()
        self._append_log("\n[GUI] Cancel requested (best-effort).\n")

    def _append_log(self, s: str):
        if not s:
            return
        self.txt_log.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.txt_log.insertPlainText(s)
        self.txt_log.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def _on_done(self, code: int):
        self._append_log(f"\n[done: exit code {code}]\n")
        self._set_running(False)

    # ---------------------
    # Browse helpers
    # ---------------------

    def _workdir_path(self) -> Path:
        return Path((self.ed_workdir.text() or "").strip() or ".").expanduser()

    def _resolve_in_workdir(self, path_text: str) -> Path:
        s = (path_text or "").strip()
        if not s:
            return Path()
        p = Path(s).expanduser()
        if p.is_absolute():
            return p
        return self._workdir_path() / p

    def _file_dialog_dir(self, path_text: str) -> str:
        s = (path_text or "").strip()
        if s:
            p = self._resolve_in_workdir(s)
            if p.exists():
                if p.is_dir():
                    return str(p)
                return str(p.parent)
        wd = self._workdir_path()
        if wd.exists():
            return str(wd)
        return str(Path.cwd())
    def _browse_workdir(self):
        cur = (self.ed_workdir.text() or "").strip() or str(Path.cwd())
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Select working directory", cur)
        if p:
            self.ed_workdir.setText(p)

    def _browse_plotdir(self):
        cur = self._file_dialog_dir(self.ed_plotdir.text())
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Select plot directory", cur)
        if p:
            self.ed_plotdir.setText(p)

    def _browse_xyz(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select equilibrium XYZ", self._file_dialog_dir(self.ed_xyz.text()), "XYZ (*.xyz);;All files (*)")
        if p:
            self.ed_xyz.setText(p)

    def _browse_traj(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select trajectory", self._file_dialog_dir(self.ed_traj.text()), "XYZ (*.xyz);;All files (*)")
        if p:
            self.ed_traj.setText(p)

    def _browse_hess(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Hessian file", self._file_dialog_dir(self.ed_hess.text()), "All files (*)")
        if p:
            self.ed_hess.setText(p)

    def _browse_cnorm(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select cnorm file", self._file_dialog_dir(self.ed_cnorm.text()), "DAT (*.dat);;All files (*)")
        if p:
            self.ed_cnorm.setText(p)

    def _open_workdir(self):
        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        if wd.exists():
            open_in_file_manager(wd)

    # ---------------------
    # Presets (JSON)
    # ---------------------
    def _collect_preset(self) -> Dict[str, Any]:
        return {
            "workdir": (self.ed_workdir.text() or "").strip(),
            "xyz": (self.ed_xyz.text() or "").strip(),
            "traj": (self.ed_traj.text() or "").strip(),
            "hess": (self.ed_hess.text() or "").strip(),
            "cnorm": ensure_cnorm_path(self.ed_cnorm.text()),
            "out_prefix": (self.ed_out_prefix.text() or "").strip(),
            "plot": bool(self.cb_plot.isChecked()),
            "plot_dir": (self.ed_plotdir.text() or "").strip(),
            "plot_dpi": int(self.sp_plotdpi.value()),
            "nrototrasl": int(self.cb_nrt.currentText()),
            "nstart": int(self.sp_nstart.value()),
            "ncorr": int(self.sp_ncorr.value()),
            "nbeads": int(self.sp_nbeads.value()),
            "nbeadsstep": int(self.sp_nbeadsstep.value()),
            "dt": float(self.sp_dt.value()),
            "coord": str(self.cb_coord.currentText()),
            "ta": bool(self.cb_ta.isChecked()),
            "alpha_pow": float(self.sp_alpha_pow.value()),
            "alpha_dip": float(self.sp_alpha_dip.value()),
            "modes": (self.ed_modes.text() or "").strip(),
            "atoms": (self.ed_atoms.text() or "").strip(),
            "readcnorm": int(self.cb_readcnorm.currentText()),
            "rm_cnorm": bool(self.cb_rm_cnorm.isChecked()),
            "init_wnumb": float(self.sp_init.value()),
            "spec_res": float(self.sp_res.value()),
            "wnumb_span": float(self.sp_span.value()),
            "freq_offset": float(self.sp_freq_offset.value()),
            "norm1": bool(self.cb_norm1.isChecked()),
            "excel": bool(self.cb_excel.isChecked()),
            "excel_sep": (self.ed_excel_sep.text() or ",").strip(),
            "excel_merge": bool(self.cb_excel_merge.isChecked()),
        }

    def _apply_preset(self, p: Dict[str, Any]):
        self.ed_workdir.setText(p.get("workdir", self.ed_workdir.text()))
        self.ed_xyz.setText(p.get("xyz", self.ed_xyz.text()))
        self.ed_traj.setText(p.get("traj", self.ed_traj.text()))
        self.ed_hess.setText(p.get("hess", self.ed_hess.text()))
        self.ed_cnorm.setText(p.get("cnorm", self.ed_cnorm.text()) or "cnorm.dat")
        self.ed_out_prefix.setText(p.get("out_prefix", self.ed_out_prefix.text()))
        self.cb_plot.setChecked(bool(p.get("plot", self.cb_plot.isChecked())))
        self.ed_plotdir.setText(p.get("plot_dir", self.ed_plotdir.text()) or ".")
        self.sp_plotdpi.setValue(int(p.get("plot_dpi", self.sp_plotdpi.value())))

        self.cb_nrt.setCurrentText(str(p.get("nrototrasl", int(self.cb_nrt.currentText()))))
        self.sp_nstart.setValue(int(p.get("nstart", self.sp_nstart.value())))
        self.sp_ncorr.setValue(int(p.get("ncorr", self.sp_ncorr.value())))
        self.sp_nbeads.setValue(int(p.get("nbeads", self.sp_nbeads.value())))
        self.sp_nbeadsstep.setValue(int(p.get("nbeadsstep", self.sp_nbeadsstep.value())))
        self.sp_dt.setValue(float(p.get("dt", self.sp_dt.value())))

        self.cb_coord.setCurrentText(str(p.get("coord", self.cb_coord.currentText())))
        self.cb_ta.setChecked(bool(p.get("ta", self.cb_ta.isChecked())))
        self.sp_alpha_pow.setValue(float(p.get("alpha_pow", self.sp_alpha_pow.value())))
        self.sp_alpha_dip.setValue(float(p.get("alpha_dip", self.sp_alpha_dip.value())))
        self.ed_modes.setText(str(p.get("modes", self.ed_modes.text())))
        self.ed_atoms.setText(str(p.get("atoms", self.ed_atoms.text())))

        self.cb_readcnorm.setCurrentText(str(p.get("readcnorm", int(self.cb_readcnorm.currentText()))))
        self.cb_rm_cnorm.setChecked(bool(p.get("rm_cnorm", self.cb_rm_cnorm.isChecked())))

        self.sp_init.setValue(float(p.get("init_wnumb", self.sp_init.value())))
        self.sp_res.setValue(float(p.get("spec_res", self.sp_res.value())))
        self.sp_span.setValue(float(p.get("wnumb_span", self.sp_span.value())))

        self.sp_freq_offset.setValue(float(p.get("freq_offset", self.sp_freq_offset.value())))
        self.cb_norm1.setChecked(bool(p.get("norm1", self.cb_norm1.isChecked())))

        self.cb_excel.setChecked(bool(p.get("excel", self.cb_excel.isChecked())))
        self.ed_excel_sep.setText(str(p.get("excel_sep", self.ed_excel_sep.text())))
        self.cb_excel_merge.setChecked(bool(p.get("excel_merge", self.cb_excel_merge.isChecked())))

    def _save_preset(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save preset", str(Path.cwd() / "nimbus_preset.json"), "JSON (*.json)")
        if not path:
            return
        data = self._collect_preset()
        Path(path).write_text(json.dumps(data, indent=2))
        QtWidgets.QMessageBox.information(self, "Saved", f"Preset saved:\n{path}")

    def _load_preset(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load preset", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return
        data = json.loads(Path(path).read_text())
        self._apply_preset(data)
        self._on_any_change()

    # ---------------------
    # Settings persistence
    # ---------------------
    def _restore_settings(self):
        # Window geometry
        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        state = self.settings.value("windowState")
        if state is not None:
            self.restoreState(state)

        # last values
        self.ed_workdir.setText(self.settings.value("workdir", str(Path.cwd())))
        self.ed_plotdir.setText(self.settings.value("plotdir", "."))
        self.ed_out_prefix.setText(self.settings.value("outprefix", "QCT_"))
        self.ed_excel_sep.setText(self.settings.value("excelsep", ","))

        self.ed_xyz.setText(self.settings.value("xyz", ""))
        self.ed_traj.setText(self.settings.value("traj", ""))
        self.ed_hess.setText(self.settings.value("hess", ""))
        self.ed_cnorm.setText(self.settings.value("cnorm", "cnorm.dat"))

    def _save_settings(self):
        self.settings.setValue("workdir", (self.ed_workdir.text() or "").strip())
        self.settings.setValue("plotdir", (self.ed_plotdir.text() or "").strip())
        self.settings.setValue("outprefix", (self.ed_out_prefix.text() or "").strip())
        self.settings.setValue("excelsep", (self.ed_excel_sep.text() or "").strip())
        self.settings.setValue("xyz", (self.ed_xyz.text() or "").strip())
        self.settings.setValue("traj", (self.ed_traj.text() or "").strip())
        self.settings.setValue("hess", (self.ed_hess.text() or "").strip())
        self.settings.setValue("cnorm", ensure_cnorm_path(self.ed_cnorm.text()))

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self._save_settings()
        super().closeEvent(event)

    # ---------------------
    # Theme
    # ---------------------
    def _apply_theme(self, dark: bool = True):
        # keep action in sync
        self.act_toggle_dark.blockSignals(True)
        self.act_toggle_dark.setChecked(bool(dark))
        self.act_toggle_dark.blockSignals(False)

        # Palette
        app = QtWidgets.QApplication.instance()
        pal = QtGui.QPalette()
        if dark:
            pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#0b1220"))
            pal.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#e5e7eb"))
            pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#0f172a"))
            pal.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#111827"))
            pal.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor("#111827"))
            pal.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor("#e5e7eb"))
            pal.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#e5e7eb"))
            pal.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#111827"))
            pal.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#e5e7eb"))
            pal.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#2563eb"))
            pal.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#ffffff"))
        else:
            pal = app.style().standardPalette()
        app.setPalette(pal)

        # QSS
        qss_dark = """
        QMainWindow { background: #0b1220; }
        QListWidget { background: #0f172a; border: 1px solid #1f2937; border-radius: 14px; padding: 6px; }
        QListWidget::item { padding: 10px 10px; border-radius: 12px; }
        QListWidget::item:selected { background: #1d4ed8; }
        QToolBar { background: transparent; border: none; spacing: 8px; }
        QToolButton, QPushButton {
            background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 8px 12px;
        }
        QToolButton:hover, QPushButton:hover { background: #0f172a; }
        QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox, QSpinBox, QDoubleSpinBox {
            background: #0f172a; border: 1px solid #1f2937; border-radius: 12px; padding: 8px;
        }
        QComboBox::drop-down { border: none; padding-right: 6px; }
        QDockWidget { titlebar-close-icon: none; titlebar-normal-icon: none; }
        QDockWidget::title { background: #111827; padding: 8px; border: 1px solid #1f2937; }
        QScrollArea { border: none; }
        QFrame#AboutCard { background: #0f172a; border: 1px solid #1f2937; border-radius: 18px; }
        QFrame#PlotCard { background: #0f172a; border: 1px solid #1f2937; border-radius: 18px; }
        QToolButton:checked { background: #0f172a; }
        """
        qss_light = ""  # keep default for now

        self.setStyleSheet(qss_dark if dark else qss_light)

    # ---------------------
    # Tiny layout helper
    # ---------------------
    def _wrap(self, layout: QtWidgets.QLayout) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setLayout(layout)
        return w


def main():
    try:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    except Exception:
        pass

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("FlyingNimbusGUIHeavy")

    app.setQuitOnLastWindowClosed(False)

    # Font
    f = QtGui.QFont()
    f.setPointSize(10)
    app.setFont(f)

    splash_txt = (ASCII_BANNER or "").rstrip("\n")
    splash = AsciiSplash(splash_txt) if splash_txt.strip() else None

    win_holder = {"w": None}

    def launch_main():
        if win_holder["w"] is not None:
            return
        w = NimbusMainWindow()
        win_holder["w"] = w
        w.show()
        try:
            w.raise_()
            w.activateWindow()
        except Exception:
            pass
        # closing main window quits
        app.setQuitOnLastWindowClosed(True)

    if splash is not None:
        splash.splashClosed.connect(launch_main)
        splash.showFullScreen()
        try:
            splash.raise_()
            splash.activateWindow()
        except Exception:
            pass
        # keep a reference
        app._startup_splash = splash
    else:
        launch_main()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
