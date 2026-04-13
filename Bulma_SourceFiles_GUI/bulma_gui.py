#!/usr/bin/env python3
from __future__ import annotations

import shlex
import subprocess
import sys
import traceback
import html
import os
import io
import contextlib
import runpy
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

#SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#Authors: Giacomo Mandelli, Giacomo Botti


ASCII_BANNER = r"""
      ##~~~~~~~#~#~##~~#~~~#~~##~##.~##~~~~~##~,~##....##~.#~#~~##.#~#~~~~~~~~~~##,
     ,##~~~~~~~#~#~##~~#~~##~~#~~#.#~#~~~~~~#~.~.##....##~#.~~#~##.#~#~~~~~~~~~~##,
     ,##~~~~~~~#~#~##~#~~~#~~##~~#.#~##~~~~##~.~##.....##~#.#~#~##.#~#.#~~~~~~~~##,
     ,##~~~#~~~~~~~##~#~~~#~##~~~#.#~~#~~~~#~#.~##......###.#~~~~#.#~#.#~~~~~~~~##,
     ,##~~~#~~~~~~~~#~#~~~#~##~~####~~##~~~#.##~##......######~#~#.#~#.#~~~~~~~~##,
      ##~~~#~~~~~~~~#~#~~~#~##~~####~~##~~~#.##~##......######~~~#.#~#~#~~~~~~~~##
      ##~~~#~~~~~~~~#~#~~~#~#~~~####~~#~#~~##.#~##......######~~##.#~#~~~~.~~~~~##
      ##~~~#~~#~~~~~#~#~~~~~#~~~####~~#~#~~~#.#.#.......####.#~.~~##~~~~~~~~~~~~##
      ,#~~~#~~#~~~~~~~~~~~~~~####..##############.....#..##############~~#~~~~~~##
       ##~~#~~#~~~~~~~###########....########.##.........#...##......#..#~~~~~~~#,
       ##~~#~#~#~~~######...#...##...#..............##.####...#.#...##..~~#~~~~##,
       ###~#~#~##..##......##...#######.............####O##...#.#...#==.#~~~~~~##
        ##~~~~~~~===##....###...########............##.,OO##..#.#...#==,#~~~~~~##
        ##~~~~#~~..==##...#.#...##O#####............#######...#....#..=~#~~~~~~#,
        ,##~~~#~~~.===##..#..#...#######............######.....#..##...~~~~~.~~#
         ##~~~~~#~...#=.##.#.....######........##.................#=..,~~~~#.~##
         ,#~~~~~~~~##...,##...................##=................##..#~~~~~#.~#,
          ##~~~~~~~~####..##..............####....##............###~~.#~~~~~.~#
           #~~~~~~~~~~.~..~##............######vv###..........####~~~#~~~~~.~~#
           ##~~~~~~~~~~~~~~~###...........##...vv.##.......#####~~~~~#~~~~~.~#
            ##~~~~~~~~~~###########........##....##......######.~##.#~~~~~~~~#
            ##~~~~~~~~~#################....######....#######....,  #~~~~~.~.
             ####~~~~~#        .,###########.......####===##       ##~####..
              ####~~~~##                ##....######===##.#######  .###,
                 ####~~##          ##########..=====##=...#########..
                    ####.        #####=#=#....######.......#======####
                      ,#.,     ####=====##.................##=======###
                            #####======###...................=###====######
                         ######====######................##============##########

                         ██████╗ ██╗   ██╗██╗     ███╗   ███╗ █████╗
                         ██╔══██╗██║   ██║██║     ████╗ ████║██╔══██╗
                         ██████╔╝██║   ██║██║     ██╔████╔██║███████║
                         ██╔══██╗██║   ██║██║     ██║╚██╔╝██║██╔══██║
                         ██████╔╝╚██████╔╝███████╗██║ ╚═╝ ██║██║  ██║
                         ╚═════╝  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝

                        Batch Utilities for Log parsing, hessian Matrix
                                        and Automation
                                
                                  Click anywere to proceed =)
"""


class AsciiSplash(QtWidgets.QWidget):

    splashClosed = QtCore.pyqtSignal()

    def __init__(self, text: str, parent=None, title: str = "Running"):
        flags = (QtCore.Qt.WindowType.SplashScreen
                 | QtCore.Qt.WindowType.FramelessWindowHint
                 | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        super().__init__(None, flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle(title)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)

        self.lbl = QtWidgets.QLabel()
        self.lbl.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.lbl.setText(text)

        fixed = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.lbl.setFont(fixed)
        self.lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)

        # A simple frame for readability (uses palette colors)
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        frame_lay = QtWidgets.QVBoxLayout(frame)
        frame_lay.setContentsMargins(12, 12, 12, 12)
        frame_lay.addWidget(self.lbl)

        lay.addWidget(frame)

        self.adjustSize()

    def closeEvent(self, ev):
        # Emit a signal so the app can react (e.g., show the main window).
        try:
            self.splashClosed.emit()
        except Exception:
            pass
        super().closeEvent(ev)


    def mousePressEvent(self, ev):  # click anywhere to close
        self.close()

    def keyPressEvent(self, ev):
        if ev.key() in (QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            self.close()
            return
        super().keyPressEvent(ev)


# ---------------------------
# UI helpers
# ---------------------------
class CollapsibleSection(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None, expanded: bool = True):
        super().__init__(parent)
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
        exp = self.btn.isChecked()
        self.btn.setArrowType(QtCore.Qt.ArrowType.DownArrow if exp else QtCore.Qt.ArrowType.RightArrow)
        self.content.setVisible(exp)


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        self.clicked.emit()
        super().mousePressEvent(e)


class FileCell(QtWidgets.QWidget):
    """Small (lineedit + browse) widget for file paths, suitable for tables."""
    changed = QtCore.pyqtSignal()

    def __init__(self, *, title="Select file", flt="All files (*)", parent=None):
        super().__init__(parent)
        self._title = title
        self._flt = flt
        self.ed = QtWidgets.QLineEdit()
        self.btn = QtWidgets.QToolButton(text="…")
        self.btn.setFixedWidth(28)

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self.ed, 1)
        lay.addWidget(self.btn, 0)

        self.ed.textChanged.connect(self.changed.emit)
        self.btn.clicked.connect(self._browse)

    def _browse(self):
        start = (self.ed.text() or "").strip() or str(Path.cwd())
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, self._title, start, self._flt)
        if p:
            self.ed.setText(p)

    def text(self) -> str:
        return (self.ed.text() or "").strip()

    def setText(self, s: str):
        self.ed.setText(s)


def open_in_file_manager(path: Path) -> None:
    p = str(path.expanduser().resolve())
    if sys.platform.startswith("linux"):
        env = os.environ.copy()
        if "LD_LIBRARY_PATH_ORIG" in env:
            env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
        else:
            env.pop("LD_LIBRARY_PATH", None)
        env.pop("LD_PRELOAD", None)
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        try:
            subprocess.Popen(["xdg-open", p], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            pass
    url = QtCore.QUrl.fromLocalFile(p)
    QtGui.QDesktopServices.openUrl(url)


# ---------------------------
# Worker thread
# ---------------------------
@dataclass
class BulmaJob:
    workdir: Path
    pyexe: Path
    bulma_script: Path
    argv: List[str]


class BulmaWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(int)

    def __init__(self, job: BulmaJob, parent=None):
        super().__init__(parent)
        self.job = job
        self._proc: Optional[subprocess.Popen] = None

    def request_cancel(self):
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def run(self):
        try:
            self.job.workdir.mkdir(parents=True, exist_ok=True)
            cmd = [str(self.job.pyexe), str(self.job.bulma_script)] + list(self.job.argv)

            self.log.emit("[cmd] " + " ".join(shlex.quote(c) for c in cmd) + "\n")
            self.log.emit(f"[cwd] {self.job.workdir}\n\n")

            if getattr(sys, "frozen", False):
                self.log.emit("[mode] in-process\n")

                old_cwd = os.getcwd()
                old_argv = sys.argv[:]
                old_path = sys.path[:]

                class _Emitter(io.TextIOBase):
                    def __init__(self, emit):
                        super().__init__()
                        self._emit = emit
                        self._buf = ""

                    def write(self, s):
                        if not s:
                            return 0
                        self._buf += s
                        while "\n" in self._buf:
                            line, self._buf = self._buf.split("\n", 1)
                            self._emit(line + "\n")
                        return len(s)

                    def flush(self):
                        if self._buf:
                            self._emit(self._buf)
                            self._buf = ""

                rc = 0
                try:
                    os.chdir(str(self.job.workdir))
                    sys.path.insert(0, str(self.job.bulma_script.parent))
                    sys.argv = [str(self.job.bulma_script)] + list(self.job.argv)

                    em = _Emitter(self.log.emit)
                    with contextlib.redirect_stdout(em), contextlib.redirect_stderr(em):
                        try:
                            runpy.run_path(str(self.job.bulma_script), run_name="__main__")
                        except SystemExit as e:
                            rc = int(e.code) if isinstance(e.code, int) else (0 if e.code is None else 1)
                    try:
                        em.flush()
                    except Exception:
                        pass
                finally:
                    sys.argv = old_argv
                    os.chdir(old_cwd)
                    sys.path[:] = old_path

                self.done.emit(int(rc))
                return

            self._proc = subprocess.Popen(
                cmd,
                cwd=str(self.job.workdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            assert self._proc.stdout is not None
            for line in self._proc.stdout:
                self.log.emit(line)
            rc = self._proc.wait()
            self.done.emit(int(rc))
        except Exception:
            self.log.emit("\n" + traceback.format_exc() + "\n")
            self.done.emit(1)


# ---------------------------
# Main window
# ---------------------------
class BulmaMainWindow(QtWidgets.QMainWindow):
    HELP = {
        "workdir": "Working directory where Bulma writes all outputs.",
        "pyexe": "Python executable used to run bulma.py.",
        "bulma": "Path to the bulma.py script to execute.",

        "optgen_xyz": "Equilibrium geometry (XYZ). Required to generate OPT/FREQ inputs.",
        "optgen_variant": "Select what to generate (OPT/FREQ) and the engine-specific variant.",
        "optgen_output": "Default output filename hint for the generated input (written in the workdir).",
        "optext_out": "output file (.out/.log) to parse and extract the last optimized geometry.",
        "optext_tmpl": "XYZ template (Gaussian only) to preserve atom order/symbols when extracting geometry.",
        "optext_geoout": "Output XYZ name for the extracted optimized geometry (written in the workdir).",

        "hess_code": "Engine/type of Hessian input (Gaussian output, ORCA .hess, or Q-Chem HESS).",
        "hess_in": "Hessian source file (depends on the selected code).",
        "mat_out": "Output filename for the lower-triangular Hessian matrix (Bulma format).",
        "vec_out": "Output filename for the flattened 1-column Hessian vector.",

        "bomd_xyz": "Equilibrium geometry (XYZ) used to generate dynamics inputs.",
        "bomd_vel": "Optional velocity file used by the selected engine (if supported).",

        "qc_theory": "Electronic structure method keyword passed to Bulma (--THEORY).",
        "qc_bs": "Basis set keyword passed to Bulma (--BS).",
        "qc_conv": "Convergence keyword passed to Bulma (--convergence).",
        "qc_nproc": "Number of CPU cores (--Nproc).",
        "qc_mem": "Memory string (--mem).",
        "qc_charge": "Molecular charge (--charge).",
        "qc_mult": "Spin multiplicity (--mult).",
        "optgen_disp": "Optional dispersion keyword/value. Gaussian expects the EmpiricalDispersion value, ORCA expects a keyword such as D4, Q-Chem expects the DFT_D value.",
        "gau_disp": "Optional Gaussian EmpiricalDispersion value (--gau-dispersion), for example GD3BJ.",
        "orca_disp": "Optional ORCA dispersion keyword (--orca-dispersion), for example D4.",
        "qchem_dft_d": "Optional Q-Chem DFT_D value (--qchem-dft-d), for example D4.",

        "gau_stepsize": "Gaussian BOMD time step parameter (--stepsize).",
        "gau_npoints": "Gaussian BOMD number of points/steps (--npoints).",
        "gau_dyn_out": "Gaussian BOMD input filename (--dyn-out).",

        "orca_vel_unit": "ORCA velocity units for the input file (--orca-vel-unit).",
        "orca_dt": "ORCA QMD time step in fs (--qmd-timestep).",
        "orca_run": "ORCA QMD number of steps (--qmd-run).",
        "orca_prefix": "Optional ORCA QMD prefix used for generated filenames (--qmd-prefix).",

        "qchem_dt": "Q-Chem AIMD time step in a.u. (--qchem-timestep).",
        "qchem_steps": "Q-Chem number of AIMD steps (--qchem-steps).",
        "qchem_print": "Q-Chem printing frequency (--qchem-print).",
        "qchem_dyn_out": "Q-Chem dynamics input filename (--qchem-qmd-out).",

        "parse_gau_out": "Gaussian dynamics output (.out/.log) to parse.",
        "parse_gau_xyz": "Equilibrium XYZ template required for Gaussian parsing (--xyz).",
        "parse_orca_traj": "ORCA trajectory.xyz file to parse.",
        "parse_orca_vel": "ORCA velocity.xyz file to parse.",
        "parse_qchem_out": "Q-Chem AIMD/QMD .out file to parse.",
        "parse_i": "Start step index (-i / --inizio when required).",
        "parse_f": "End step index (-f / --fine when required).",
        "parse_outbase": "Base name for parsed outputs (-o).",
        "parse_nimbus_out": "Optional explicit output trajectory name (--nimbus-out).",
        "parse_epot_out": "Optional output filename for E_pot column (--epot-out).",
        "parse_total": "Gaussian-only: write total energies file (--total).",

        "custom_args": "Run any bulma.py command: arguments are passed verbatim after `python bulma.py`.",
    }

    OPT_ROWS = ["GAU", "ORCA", "QCHEM"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BULMA GUI")
        self.resize(1400, 920)

        self._ui_ready = False  # block early signal storms during UI construction

        self.worker: Optional[BulmaWorker] = None
        self._banner: Optional[AsciiSplash] = None
        self.settings = QtCore.QSettings("Bulma", "BulmaGUI")
        self._help_key = None
        self._help_title = None


        self._build_actions()
        self._build_ui()
        self._apply_theme(True)
        self._restore_settings()

        self._ui_ready = True
        self._update_help()

    # ---------------- ASCII banner ----------------
    def _show_run_banner(self, text: str | None = None):
        """Show a temporary, user-closable banner while a job is running."""
        if self._banner is not None and self._banner.isVisible():
            return
        banner_txt = text if text is not None else ASCII_BANNER
        if not (banner_txt or "").strip():
            return
        self._banner = AsciiSplash(banner_txt, parent=self, title="BULMA running")
        # Place it near the main window
        try:
            g = self.geometry()
            self._banner.move(g.center() - QtCore.QPoint(self._banner.width() // 2, self._banner.height() // 2))
        except Exception:
            pass
        self._banner.show()

    def _hide_run_banner(self):
        if self._banner is None:
            return
        try:
            self._banner.close()
        except Exception:
            pass
        self._banner = None

    # ---------------- actions ----------------
    def _build_actions(self):
        self.act_run = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay), "Run", self)
        self.act_stop = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaStop), "Stop", self)
        self.act_open_workdir = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon), "Open workdir", self)
        self.act_toggle_dark = QtGui.QAction("Dark theme", self, checkable=True)
        self.act_toggle_dark.setChecked(True)

        self.act_show_log = QtGui.QAction("Show log", self, checkable=True)
        self.act_show_help = QtGui.QAction("Show help", self, checkable=True)

        self.act_run.triggered.connect(self._run)
        self.act_stop.triggered.connect(self._stop)
        self.act_open_workdir.triggered.connect(self._open_workdir)
        self.act_toggle_dark.toggled.connect(self._apply_theme)

    def _build_menu(self):
        m_file = self.menuBar().addMenu("File")
        m_file.addAction("Quit", self.close)

        m_view = self.menuBar().addMenu("View")
        m_view.addAction(self.act_toggle_dark)

        m_view.addSeparator()
        m_view.addAction(self.act_show_log)
        m_view.addAction(self.act_show_help)

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

    # ---------------- layout ----------------
    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # sidebar
        self.sidebar = QtWidgets.QListWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setSpacing(4)
        self.sidebar.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        def add_nav(title: str, icon: QtGui.QIcon):
            it = QtWidgets.QListWidgetItem(icon, title)
            it.setSizeHint(QtCore.QSize(200, 44))
            self.sidebar.addItem(it)

        add_nav("Opt", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogNewFolder))
        add_nav("Hessian", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView))
        add_nav("BOMD", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon))
        add_nav("About", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation))

        # pages
        self.pages = QtWidgets.QStackedWidget()
        self.page_opt = self._make_scroll_page()
        self.page_hess = self._make_scroll_page()
        self.page_bomd = self._make_scroll_page()
        self.page_about = self._make_scroll_page()
        self.pages.addWidget(self.page_opt)
        self.pages.addWidget(self.page_hess)
        self.pages.addWidget(self.page_bomd)
        self.pages.addWidget(self.page_about)

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.currentRowChanged.connect(self._on_any_change)
        self.sidebar.setCurrentRow(0)

        # right side: Runner ONCE + pages
        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(12)
        right.addWidget(self._runner_section())
        right.addWidget(self.pages, 1)

        root.addWidget(self.sidebar)
        root.addLayout(right, 1)


        # docks
        self.dock_log = QtWidgets.QDockWidget("Log", self)
        self.dock_help = QtWidgets.QDockWidget("Help", self)

        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(200000)
        self.dock_log.setWidget(self.txt_log)

        self.txt_help = QtWidgets.QTextBrowser()
        self.txt_help.setOpenExternalLinks(False)
        self.txt_help.setHtml("<h3>Help</h3><p>Click a parameter name to see its explanation.</p>")
        self.dock_help.setWidget(self.txt_help)

        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_log)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self.dock_help)


        self.act_show_log.setChecked(True)
        self.act_show_help.setChecked(True)

        self.act_show_log.toggled.connect(self.dock_log.setVisible)
        self.act_show_help.toggled.connect(self.dock_help.setVisible)

        self.dock_log.visibilityChanged.connect(self.act_show_log.setChecked)
        self.dock_help.visibilityChanged.connect(self.act_show_help.setChecked)

        # build pages
        self._build_page_opt(self._page_layout(self.page_opt))
        self._build_page_hess(self._page_layout(self.page_hess))
        self._build_page_bomd(self._page_layout(self.page_bomd))
        self._build_page_about(self._page_layout(self.page_about))

        self._set_running(False)

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

    def _wrap(self, layout: QtWidgets.QLayout) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setLayout(layout)
        return w

    def _hlbl(self, title: str, key: str) -> QtWidgets.QLabel:
        lbl = ClickableLabel(title)
        lbl.setToolTip(self.HELP.get(key, ""))
        lbl.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        lbl.setStyleSheet("color: #79b8ff; text-decoration: underline;")
        lbl.clicked.connect(lambda: self._show_help(key, title))
        return lbl

    def _show_help(self, key: str, title: str):
        if self._help_key == key:
            self._help_key = None
            self._help_title = None
        else:
            self._help_key = key
            self._help_title = title
        self._update_help()
        if not self.dock_help.isVisible():
            self.dock_help.setVisible(True)


    # ---------------- Runner section ----------------


    def _runner_section(self) -> CollapsibleSection:
        sec = CollapsibleSection("Runner", expanded=True)
        form = QtWidgets.QFormLayout()
        form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.DontWrapRows)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.ed_workdir = getattr(self, "ed_workdir", QtWidgets.QLineEdit(str(Path.cwd())))
        self.ed_workdir.textChanged.connect(self._on_any_change)

        # workdir
        wdrow = QtWidgets.QHBoxLayout()
        wdrow.addWidget(self.ed_workdir, 1)
        b = QtWidgets.QToolButton(text="…")
        b.clicked.connect(self._browse_workdir)
        wdrow.addWidget(b, 0)
        _lbl = self._hlbl("Workdir", "workdir")
        _lblw = QtWidgets.QWidget()
        _lbll = QtWidgets.QVBoxLayout(_lblw)
        _lbll.setContentsMargins(0, 0, 0, 0)
        _lbll.setSpacing(0)
        _lbll.addStretch(1)
        _lbll.addWidget(_lbl, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        _lbll.addStretch(1)
        form.addRow(_lblw, self._wrap(wdrow))

        # python

        # bulma.py

        sec.content_lay.addLayout(form)
        return sec

    def _browse_workdir(self):
        start = (self.ed_workdir.text() or "").strip() or str(Path.cwd())
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Select directory", start)
        if p:
            self.ed_workdir.setText(p)

    def _browse_into(self, lineedit: QtWidgets.QLineEdit, filter_str: str):
        start = (lineedit.text() or "").strip() or str(Path.cwd())
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file", start, filter_str)
        if p:
            lineedit.setText(p)

    # ---------------- OPT page (two tables) ----------------
    def _build_page_opt(self, lay: QtWidgets.QVBoxLayout):
        """OPT page:
        - Tab 1: create optimization input (GAU/ORCA/QCHEM)
        - Tab 2: extract optimized geometry (GAU/ORCA/QCHEM)
        """
        sec = CollapsibleSection("Opt", expanded=True)

        self.opt_tabs = QtWidgets.QTabWidget()
        self.opt_tabs.currentChanged.connect(self._on_any_change)

        codes = ["GAU", "ORCA", "QCHEM"]
        outputs = {"GAU": "geom.com", "ORCA": "geom.inp", "QCHEM": "opt.inp"}
        defaults = dict(theory="B3LYP", bs="Def2TZVP", conv="VeryTight", nproc=48, mem="300Gb", charge=0, mult=1)

        # ---------- Tab 1 ----------
        tab_gen = QtWidgets.QWidget()
        gen_lay = QtWidgets.QVBoxLayout(tab_gen)
        gen_lay.setSpacing(10)

        self.tbl_opt_gen = QtWidgets.QTableWidget(3, 12)
        self.tbl_opt_gen.setHorizontalHeaderLabels([
            "Code", "XYZ", "Job", "THEORY", "BS", "conv.",
            "Nproc", "mem", "charge", "mult", "disp.", "Output"
        ])
        self.tbl_opt_gen.verticalHeader().setVisible(False)
        self.tbl_opt_gen.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_opt_gen.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_opt_gen.horizontalHeader().setStretchLastSection(True)
        self.tbl_opt_gen.setAlternatingRowColors(True)
        self.tbl_opt_gen.setMinimumHeight(240)
        self.tbl_opt_gen.horizontalHeader().sectionClicked.connect(self._on_optgen_header_clicked)

        for r, code in enumerate(codes):
            it = QtWidgets.QTableWidgetItem(code)
            it.setFlags(it.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tbl_opt_gen.setItem(r, 0, it)

            fc = FileCell(title=f"Select {code} XYZ", flt="XYZ (*.xyz);;All files (*)")
            fc.changed.connect(self._on_any_change)
            self.tbl_opt_gen.setCellWidget(r, 1, fc)

            cb = QtWidgets.QComboBox()
            if code == "GAU":
                cb.addItems(["opt (--opt)", "freq (--freq)"])
            elif code == "ORCA":
                cb.addItems(["opt (--orca-opt)", "freq (--orca-freq)"])
            else:
                cb.addItems(["opt single (--qchem-opt-single)", "opt multi (--qchem-opt)", "freq single (--qchem-freq)"])
            cb.currentIndexChanged.connect(lambda _idx, rr=r: self._on_optgen_variant_changed(rr))
            self.tbl_opt_gen.setCellWidget(r, 2, cb)

            for c, key in [(3, "theory"), (4, "bs"), (5, "conv"), (7, "mem")]:
                ed = QtWidgets.QLineEdit(str(defaults[key]))
                ed.textChanged.connect(self._on_any_change)
                self.tbl_opt_gen.setCellWidget(r, c, ed)

            sp_n = QtWidgets.QSpinBox(); sp_n.setRange(1, 9999); sp_n.setValue(defaults["nproc"])
            sp_n.valueChanged.connect(self._on_any_change)
            self.tbl_opt_gen.setCellWidget(r, 6, sp_n)

            sp_c = QtWidgets.QSpinBox(); sp_c.setRange(-50, 50); sp_c.setValue(defaults["charge"])
            sp_c.valueChanged.connect(self._on_any_change)
            self.tbl_opt_gen.setCellWidget(r, 8, sp_c)

            sp_m = QtWidgets.QSpinBox(); sp_m.setRange(1, 99); sp_m.setValue(defaults["mult"])
            sp_m.valueChanged.connect(self._on_any_change)
            self.tbl_opt_gen.setCellWidget(r, 9, sp_m)

            ed_disp = QtWidgets.QLineEdit("")
            ed_disp.textChanged.connect(self._on_any_change)
            self.tbl_opt_gen.setCellWidget(r, 10, ed_disp)

            it2 = QtWidgets.QTableWidgetItem(outputs[code])
            it2.setFlags(it2.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tbl_opt_gen.setItem(r, 11, it2)
            self._update_optgen_output_row(r)

        self.tbl_opt_gen.selectRow(0)
        self.tbl_opt_gen.itemSelectionChanged.connect(self._on_any_change)

        gen_lay.addWidget(QtWidgets.QLabel("Create OPT or FREQ input (select a row, set mode/variant, edit fields, then Run)."))
        gen_lay.addWidget(self.tbl_opt_gen, 1)

        # ---------- Tab 2 ----------
        tab_ext = QtWidgets.QWidget()
        ext_lay = QtWidgets.QVBoxLayout(tab_ext)
        ext_lay.setSpacing(10)

        self.tbl_opt_ext = QtWidgets.QTableWidget(3, 4)
        self.tbl_opt_ext.setHorizontalHeaderLabels([
            "Code", "OUT file(.out/.log)", "XYZ template (GAU only)", "geo-out"
        ])
        self.tbl_opt_ext.verticalHeader().setVisible(False)
        self.tbl_opt_ext.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_opt_ext.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_opt_ext.horizontalHeader().setStretchLastSection(True)
        self.tbl_opt_ext.setAlternatingRowColors(True)
        self.tbl_opt_ext.setMinimumHeight(210)
        self.tbl_opt_ext.horizontalHeader().sectionClicked.connect(self._on_optext_header_clicked)

        for r, code in enumerate(codes):
            it = QtWidgets.QTableWidgetItem(code)
            it.setFlags(it.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.tbl_opt_ext.setItem(r, 0, it)

            fout = FileCell(title=f"Select {code} output file", flt="All files (*)")
            fout.changed.connect(self._on_any_change)
            self.tbl_opt_ext.setCellWidget(r, 1, fout)

            ftempl = FileCell(title="Select XYZ template", flt="XYZ (*.xyz);;All files (*)")
            ftempl.changed.connect(self._on_any_change)
            if code != "GAU":
                ftempl.setEnabled(False)
            self.tbl_opt_ext.setCellWidget(r, 2, ftempl)

            ed = QtWidgets.QLineEdit("geo_opt.xyz")
            ed.textChanged.connect(self._on_any_change)
            self.tbl_opt_ext.setCellWidget(r, 3, ed)

        self.tbl_opt_ext.selectRow(0)
        self.tbl_opt_ext.itemSelectionChanged.connect(self._on_any_change)

        ext_lay.addWidget(QtWidgets.QLabel("Extract optimized geometry (select a row, set output, then Run)."))
        ext_lay.addWidget(self.tbl_opt_ext, 1)

        self.opt_tabs.addTab(tab_gen, "Create OPT/FREQ input")
        self.opt_tabs.addTab(tab_ext, "Extract optimized geometry")

        sec.content_lay.addWidget(self.opt_tabs)
        lay.addWidget(sec)
        lay.addStretch(1)


    # ---- OPT generator helpers (mode/variant -> output + CLI flag) ----
    def _optgen_output_name(self, code: str, variant_idx: int) -> str:
        """
        Return the default output filename for the OPT/FREQ generator table row.
        This is only a UI hint: bulma.py writes fixed filenames for these modes.
        """
        if code == "GAU":
            return "geom.com" if variant_idx == 0 else "geom_freq.com"
        if code == "ORCA":
            return "geom.inp" if variant_idx == 0 else "geom_freq.inp"
        # QCHEM
        return "opt.inp" if variant_idx in (0, 1) else "freq.inp"

    def _update_optgen_output_row(self, r: int) -> None:
        try:
            code_item = self.tbl_opt_gen.item(r, 0)
            if code_item is None:
                return
            code = (code_item.text() or "").strip().upper()
            cb = self.tbl_opt_gen.cellWidget(r, 2)
            idx = cb.currentIndex() if isinstance(cb, QtWidgets.QComboBox) else 0
            out = self._optgen_output_name(code, idx)

            it = self.tbl_opt_gen.item(r, 11)
            if it is None:
                it = QtWidgets.QTableWidgetItem(out)
                it.setFlags(it.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tbl_opt_gen.setItem(r, 10, it)
            else:
                it.setText(out)
        except Exception:
            pass

    def _on_optgen_variant_changed(self, r: int) -> None:
        # update output filename hint immediately, even while restoring settings
        self._update_optgen_output_row(r)
        self._on_any_change()

    def _on_optgen_header_clicked(self, col: int):
        m = {1: "optgen_xyz", 2: "optgen_variant", 3: "qc_theory", 4: "qc_bs", 5: "qc_conv", 6: "qc_nproc", 7: "qc_mem", 8: "qc_charge", 9: "qc_mult", 10: "optgen_disp", 11: "optgen_output"}
        key = m.get(int(col))
        if not key:
            return
        it = self.tbl_opt_gen.horizontalHeaderItem(int(col))
        title = it.text() if it is not None else key
        self._show_help(key, title)

    def _on_optext_header_clicked(self, col: int):
        m = {1: "optext_out", 2: "optext_tmpl", 3: "optext_geoout"}
        key = m.get(int(col))
        if not key:
            return
        it = self.tbl_opt_ext.horizontalHeaderItem(int(col))
        title = it.text() if it is not None else key
        self._show_help(key, title)


    # ---------------- Hessian page ----------------
    def _build_page_hess(self, lay: QtWidgets.QVBoxLayout):
        sec = CollapsibleSection("Hessian", expanded=True)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.cb_hess_code = QtWidgets.QComboBox()
        self.cb_hess_code.addItems(["GAU", "ORCA", "QCHEM"])
        self.cb_hess_code.currentIndexChanged.connect(self._on_any_change)

        self.fc_hess_in = FileCell(title="Select Hessian input file", flt="All files (*)")
        self.fc_hess_in.changed.connect(self._on_any_change)

        self.ed_mat_out = QtWidgets.QLineEdit("Hessian.out")
        self.ed_vec_out = QtWidgets.QLineEdit("Hessian_flat.out")
        self.ed_mat_out.textChanged.connect(self._on_any_change)
        self.ed_vec_out.textChanged.connect(self._on_any_change)

        form.addRow(self._hlbl("Code", "hess_code"), self.cb_hess_code)
        form.addRow(self._hlbl("Input", "hess_in"), self.fc_hess_in)
        form.addRow(self._hlbl("Matrix Output (-m)", "mat_out"), self.ed_mat_out)
        form.addRow(self._hlbl("Vector Output (-v)", "vec_out"), self.ed_vec_out)

        sec.content_lay.addLayout(form)
        lay.addWidget(sec)
        lay.addStretch(1)

    # ---------------- BOMD page ----------------
    def _build_page_bomd(self, lay: QtWidgets.QVBoxLayout):
        sec = CollapsibleSection("BOMD", expanded=True)

        self.bomd_tabs = QtWidgets.QTabWidget()
        self.bomd_tabs.currentChanged.connect(self._on_any_change)

        # ---- Tab: Generate ----
        tab_g = QtWidgets.QWidget()
        gl = QtWidgets.QVBoxLayout(tab_g); gl.setSpacing(10)

        self.cb_bomd_code = QtWidgets.QComboBox()
        self.cb_bomd_code.addItems(["GAU", "ORCA", "QCHEM"])
        self.cb_bomd_code.currentIndexChanged.connect(self._on_any_change)
        gl.addWidget(self.cb_bomd_code)

        self.fc_bomd_xyz = FileCell(title="Select equilibrium XYZ", flt="XYZ (*.xyz);;All files (*)")
        self.fc_bomd_vel = FileCell(title="Select velocity file", flt="All files (*)")
        self.fc_bomd_xyz.changed.connect(self._on_any_change)
        self.fc_bomd_vel.changed.connect(self._on_any_change)

        f = QtWidgets.QFormLayout()
        f.addRow(self._hlbl("XYZ", "bomd_xyz"), self.fc_bomd_xyz)
        f.addRow(self._hlbl("Velocity file", "bomd_vel"), self.fc_bomd_vel)
        gl.addLayout(f)

        # QC settings (reused for BOMD)
        qc = CollapsibleSection("ab initio settings", expanded=True)
        ff = QtWidgets.QFormLayout()
        self.ed_theory = getattr(self, "ed_theory", QtWidgets.QLineEdit("B3LYP"))
        self.ed_bs = getattr(self, "ed_bs", QtWidgets.QLineEdit("Def2TZVP"))
        self.ed_conv = getattr(self, "ed_conv", QtWidgets.QLineEdit("VeryTight"))
        self.sp_nproc = getattr(self, "sp_nproc", QtWidgets.QSpinBox()); self.sp_nproc.setRange(1, 9999); self.sp_nproc.setValue(int(getattr(self.sp_nproc, "value", lambda: 48)()))
        self.ed_mem = getattr(self, "ed_mem", QtWidgets.QLineEdit("300Gb"))
        self.sp_charge = getattr(self, "sp_charge", QtWidgets.QSpinBox()); self.sp_charge.setRange(-50, 50)
        self.sp_mult = getattr(self, "sp_mult", QtWidgets.QSpinBox()); self.sp_mult.setRange(1, 99)

        for w in (self.ed_theory, self.ed_bs, self.ed_conv, self.ed_mem):
            w.textChanged.connect(self._on_any_change)
        for w in (self.sp_nproc, self.sp_charge, self.sp_mult):
            w.valueChanged.connect(self._on_any_change)

        ff.addRow(self._hlbl("THEORY", "qc_theory"), self.ed_theory)
        ff.addRow(self._hlbl("BS", "qc_bs"), self.ed_bs)
        ff.addRow(self._hlbl("conv.", "qc_conv"), self.ed_conv)
        ff.addRow(self._hlbl("Nproc", "qc_nproc"), self.sp_nproc)
        ff.addRow(self._hlbl("mem", "qc_mem"), self.ed_mem)
        ff.addRow(self._hlbl("charge", "qc_charge"), self.sp_charge)
        ff.addRow(self._hlbl("mult", "qc_mult"), self.sp_mult)
        qc.content_lay.addLayout(ff)
        gl.addWidget(qc)

        # engine-specific params
        self.bomd_gen_stack = QtWidgets.QStackedWidget()

        # GAU dyn params
        w = QtWidgets.QWidget(); ff = QtWidgets.QFormLayout(w)
        self.sp_stepsize = QtWidgets.QSpinBox(); self.sp_stepsize.setRange(1, 10**9); self.sp_stepsize.setValue(2000)
        self.sp_npoints = QtWidgets.QSpinBox(); self.sp_npoints.setRange(1, 10**9); self.sp_npoints.setValue(2500)
        self.ed_dyn_out = QtWidgets.QLineEdit("dyn.com")
        self.ed_gau_disp = QtWidgets.QLineEdit("")
        for ww in (self.sp_stepsize, self.sp_npoints):
            ww.valueChanged.connect(self._on_any_change)
        self.ed_dyn_out.textChanged.connect(self._on_any_change)
        self.ed_gau_disp.textChanged.connect(self._on_any_change)
        ff.addRow(self._hlbl("stepsize", "gau_stepsize"), self.sp_stepsize)
        ff.addRow(self._hlbl("npoints", "gau_npoints"), self.sp_npoints)
        ff.addRow(self._hlbl("dyn-out", "gau_dyn_out"), self.ed_dyn_out)
        ff.addRow(self._hlbl("dispersion (optional)", "gau_disp"), self.ed_gau_disp)
        self.bomd_gen_stack.addWidget(w)

        # ORCA qmd params
        w = QtWidgets.QWidget(); ff = QtWidgets.QFormLayout(w)
        self.cb_orca_vel_unit = QtWidgets.QComboBox(); self.cb_orca_vel_unit.addItems(["au", "angfs"])
        self.sp_orca_dt = QtWidgets.QDoubleSpinBox(); self.sp_orca_dt.setDecimals(3); self.sp_orca_dt.setRange(0.001, 1000.0); self.sp_orca_dt.setValue(0.200)
        self.sp_orca_run = QtWidgets.QSpinBox(); self.sp_orca_run.setRange(1, 10**9); self.sp_orca_run.setValue(2501)
        self.ed_orca_prefix = QtWidgets.QLineEdit("")
        self.ed_orca_disp = QtWidgets.QLineEdit("")
        self.cb_orca_vel_unit.currentIndexChanged.connect(self._on_any_change)
        self.sp_orca_dt.valueChanged.connect(self._on_any_change)
        self.sp_orca_run.valueChanged.connect(self._on_any_change)
        self.ed_orca_prefix.textChanged.connect(self._on_any_change)
        self.ed_orca_disp.textChanged.connect(self._on_any_change)
        ff.addRow(self._hlbl("vel-unit", "orca_vel_unit"), self.cb_orca_vel_unit)
        ff.addRow(self._hlbl("timestep (fs)", "orca_dt"), self.sp_orca_dt)
        ff.addRow(self._hlbl("run steps", "orca_run"), self.sp_orca_run)
        ff.addRow(self._hlbl("prefix (optional)", "orca_prefix"), self.ed_orca_prefix)
        ff.addRow(self._hlbl("dispersion (optional)", "orca_disp"), self.ed_orca_disp)
        self.bomd_gen_stack.addWidget(w)

        # QCHEM qmd params
        w = QtWidgets.QWidget(); ff = QtWidgets.QFormLayout(w)
        self.sp_qchem_dt = QtWidgets.QSpinBox(); self.sp_qchem_dt.setRange(1, 10**9); self.sp_qchem_dt.setValue(8)
        self.sp_qchem_steps = QtWidgets.QSpinBox(); self.sp_qchem_steps.setRange(1, 10**9); self.sp_qchem_steps.setValue(2500)
        self.sp_qchem_print = QtWidgets.QSpinBox(); self.sp_qchem_print.setRange(1, 10**9); self.sp_qchem_print.setValue(1)
        self.ed_qchem_dyn_out = QtWidgets.QLineEdit("dyn.inp")
        self.ed_qchem_dft_d = QtWidgets.QLineEdit("")
        for ww in (self.sp_qchem_dt, self.sp_qchem_steps, self.sp_qchem_print):
            ww.valueChanged.connect(self._on_any_change)
        self.ed_qchem_dyn_out.textChanged.connect(self._on_any_change)
        self.ed_qchem_dft_d.textChanged.connect(self._on_any_change)
        ff.addRow(self._hlbl("Time_step (a.u.)", "qchem_dt"), self.sp_qchem_dt)
        ff.addRow(self._hlbl("aimd_steps", "qchem_steps"), self.sp_qchem_steps)
        ff.addRow(self._hlbl("aimd_print", "qchem_print"), self.sp_qchem_print)
        ff.addRow(self._hlbl("dyn-out", "qchem_dyn_out"), self.ed_qchem_dyn_out)
        ff.addRow(self._hlbl("DFT_D (optional)", "qchem_dft_d"), self.ed_qchem_dft_d)
        self.bomd_gen_stack.addWidget(w)

        gl.addWidget(self.bomd_gen_stack)
        self.cb_bomd_code.currentIndexChanged.connect(lambda idx: self.bomd_gen_stack.setCurrentIndex(idx))
        self.bomd_gen_stack.setCurrentIndex(0)

        gl.addStretch(1)

        # ---- Tab: Parse -> Nimbus ----
        tab_p = QtWidgets.QWidget()
        pl = QtWidgets.QVBoxLayout(tab_p); pl.setSpacing(10)

        self.cb_parse_code = QtWidgets.QComboBox()
        self.cb_parse_code.addItems(["GAU", "ORCA", "QCHEM"])
        self.cb_parse_code.currentIndexChanged.connect(self._on_any_change)
        pl.addWidget(self.cb_parse_code)

        self.parse_stack = QtWidgets.QStackedWidget()

        # GAU parse inputs
        w = QtWidgets.QWidget(); ff = QtWidgets.QFormLayout(w)
        self.fc_gau_out = FileCell(title="Select Gaussian output", flt="All files (*)")
        self.fc_gau_xyz = FileCell(title="Select XYZ template", flt="XYZ (*.xyz);;All files (*)")
        self.fc_gau_out.changed.connect(self._on_any_change)
        self.fc_gau_xyz.changed.connect(self._on_any_change)
        ff.addRow(self._hlbl("Gaussian out", "parse_gau_out"), self.fc_gau_out)
        ff.addRow(self._hlbl("XYZ template", "parse_gau_xyz"), self.fc_gau_xyz)
        self.parse_stack.addWidget(w)

        # ORCA parse inputs
        w = QtWidgets.QWidget(); ff = QtWidgets.QFormLayout(w)
        self.fc_orca_traj = FileCell(title="Select trajectory.xyz", flt="XYZ (*.xyz);;All files (*)")
        self.fc_orca_vel = FileCell(title="Select velocity.xyz", flt="XYZ (*.xyz);;All files (*)")
        self.fc_orca_traj.setText("trajectory.xyz")
        self.fc_orca_vel.setText("velocity.xyz")
        self.fc_orca_traj.changed.connect(self._on_any_change)
        self.fc_orca_vel.changed.connect(self._on_any_change)
        ff.addRow(self._hlbl("trajectory.xyz", "parse_orca_traj"), self.fc_orca_traj)
        ff.addRow(self._hlbl("velocity.xyz", "parse_orca_vel"), self.fc_orca_vel)
        self.parse_stack.addWidget(w)

        # QCHEM parse inputs
        w = QtWidgets.QWidget(); ff = QtWidgets.QFormLayout(w)
        self.fc_qchem_out = FileCell(title="Select Q-Chem QMD .out", flt="All files (*)")
        self.fc_qchem_out.changed.connect(self._on_any_change)
        ff.addRow(self._hlbl("Q-Chem .out", "parse_qchem_out"), self.fc_qchem_out)
        self.parse_stack.addWidget(w)

        self.cb_parse_code.currentIndexChanged.connect(lambda idx: self.parse_stack.setCurrentIndex(idx))
        pl.addWidget(self.parse_stack)

        # shared parse options
        row = QtWidgets.QHBoxLayout()
        self.sp_i = QtWidgets.QSpinBox(); self.sp_i.setRange(0, 10**9); self.sp_i.setValue(0)
        self.sp_f = QtWidgets.QSpinBox(); self.sp_f.setRange(0, 10**9); self.sp_f.setValue(0)
        self.sp_i.valueChanged.connect(self._on_any_change)
        self.sp_f.valueChanged.connect(self._on_any_change)
        row.addWidget(self._hlbl("start (-i)", "parse_i")); row.addWidget(self.sp_i)
        row.addWidget(self._hlbl("end (-f)", "parse_f")); row.addWidget(self.sp_f)
        row.addStretch(1)
        pl.addLayout(row)

        form = QtWidgets.QFormLayout()
        self.ed_outbase = QtWidgets.QLineEdit("parsed_log")
        self.ed_nimbus_out = QtWidgets.QLineEdit("")
        self.ed_epot_out = QtWidgets.QLineEdit("")
        self.cb_total = QtWidgets.QCheckBox()
        self.ed_outbase.textChanged.connect(self._on_any_change)
        self.ed_nimbus_out.textChanged.connect(self._on_any_change)
        self.ed_epot_out.textChanged.connect(self._on_any_change)
        self.cb_total.stateChanged.connect(self._on_any_change)
        form.addRow(self._hlbl("output base (-o)", "parse_outbase"), self.ed_outbase)
        form.addRow(self._hlbl("nimbus-out (optional)", "parse_nimbus_out"), self.ed_nimbus_out)
        form.addRow(self._hlbl("epot-out (optional)", "parse_epot_out"), self.ed_epot_out)
        row_total = QtWidgets.QHBoxLayout()
        row_total.addWidget(self.cb_total)
        row_total.addWidget(self._hlbl("write energies (--total) [Gaussian only]", "parse_total"))
        row_total.addStretch(1)
        form.addRow(QtWidgets.QLabel(""), self._wrap(row_total))
        pl.addLayout(form)
        pl.addStretch(1)

        # ---- Tab: Custom args ----
        tab_c = QtWidgets.QWidget()
        cl = QtWidgets.QVBoxLayout(tab_c); cl.setSpacing(10)
        cl.addWidget(QtWidgets.QLabel("Custom Bulma args (run ANY command from GUI).\n"
                                      "Write exactly what you would type after `python bulma.py`.\n"
                                      "Example:  geo.xyz --orca-qmd --orca-vel-file velocity.xyz"))
        self.ed_custom_args = QtWidgets.QPlainTextEdit()
        self.ed_custom_args.setPlaceholderText("e.g.\ngeo.xyz --opt --THEORY B3LYP --BS Def2TZVP --Nproc 48 --mem 300Gb --charge 0 --mult 1")
        self.ed_custom_args.textChanged.connect(self._on_any_change)
        cl.addWidget(self.ed_custom_args, 1)

        self.bomd_tabs.addTab(tab_g, "Generate")
        self.bomd_tabs.addTab(tab_p, "Parse → Nimbus")
        self.bomd_tabs.addTab(tab_c, "Custom args")

        sec.content_lay.addWidget(self.bomd_tabs)
        lay.addWidget(sec)
        lay.addStretch(1)

    def _build_page_about(self, lay: QtWidgets.QVBoxLayout):
        card = QtWidgets.QFrame()
        card.setObjectName("AboutCard")
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QtWidgets.QLabel("BULMA GUI")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        v.addWidget(title)

        txt = QtWidgets.QLabel(
            "• See Documentation: \n"
            "• You like it or use it? Please CITE: \n"
            "• Authors: Giacomo Mandelli, Giacomo Botti \n"
        )
        txt.setStyleSheet("color: #cbd5e1;")
        v.addWidget(txt)

        btn = QtWidgets.QPushButton("Open working directory")
        btn.clicked.connect(self._open_workdir)
        v.addWidget(btn)
        v.addStretch(1)

        lay.addWidget(card)
        lay.addStretch(1)


    # ---------------- command builder ----------------
    def _bulma_job(self) -> BulmaJob:
        workdir = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        pyexe = Path(sys.executable).expanduser()

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            bulma = exe_dir / "bulma.py"
            if not bulma.is_file():
                base = Path(getattr(sys, "_MEIPASS", exe_dir))
                bulma = base / "bulma.py"
        else:
            bulma = Path(__file__).resolve().with_name("bulma.py")

        if not bulma.is_file():
            raise FileNotFoundError(f"bulma.py not found: {bulma}")

        page = self.sidebar.currentRow()
        argv: List[str] = []

        # -------- OPT --------
        if page == 0:
            codes = ["GAU", "ORCA", "QCHEM"]
            tab = self.opt_tabs.currentIndex()

            if tab == 0:
                r = self.tbl_opt_gen.currentRow()
                if r < 0:
                    r = 0
                code = codes[r]

                xyz_cell = self.tbl_opt_gen.cellWidget(r, 1)
                xyz = xyz_cell.text() if isinstance(xyz_cell, FileCell) else ""
                if not xyz:
                    raise ValueError(f"{code}: XYZ is required.")

                theory = (self.tbl_opt_gen.cellWidget(r, 3).text() or "B3LYP").strip()      # type: ignore
                bs     = (self.tbl_opt_gen.cellWidget(r, 4).text() or "Def2TZVP").strip()   # type: ignore
                conv   = (self.tbl_opt_gen.cellWidget(r, 5).text() or "VeryTight").strip()  # type: ignore
                nproc  = int(self.tbl_opt_gen.cellWidget(r, 6).value())                     # type: ignore
                mem    = (self.tbl_opt_gen.cellWidget(r, 7).text() or "300Gb").strip()      # type: ignore
                charge = int(self.tbl_opt_gen.cellWidget(r, 8).value())                     # type: ignore
                mult   = int(self.tbl_opt_gen.cellWidget(r, 9).value())                     # type: ignore
                disp   = (self.tbl_opt_gen.cellWidget(r, 10).text() or "").strip()          # type: ignore

                argv.append(xyz)
                argv.extend(["--THEORY", theory, "--BS", bs, "--convergence", conv])
                argv.extend(["--Nproc", str(nproc), "--mem", mem, "--charge", str(charge), "--mult", str(mult)])

                cb = self.tbl_opt_gen.cellWidget(r, 2)
                idx = cb.currentIndex() if isinstance(cb, QtWidgets.QComboBox) else 0

                if code == "GAU":
                    argv.append("--opt" if idx == 0 else "--freq")
                    if disp:
                        argv.extend(["--gau-dispersion", disp])
                elif code == "ORCA":
                    argv.append("--orca-opt" if idx == 0 else "--orca-freq")
                    if disp:
                        argv.extend(["--orca-dispersion", disp])
                else:
                    if idx == 0:
                        argv.append("--qchem-opt-single")
                    elif idx == 1:
                        argv.append("--qchem-opt")
                    else:
                        argv.append("--qchem-freq")
                    if disp:
                        argv.extend(["--qchem-dft-d", disp])

            else:
                r = self.tbl_opt_ext.currentRow()
                if r < 0:
                    r = 0
                code = codes[r]

                out_cell = self.tbl_opt_ext.cellWidget(r, 1)
                out_file = out_cell.text() if isinstance(out_cell, FileCell) else ""
                if not out_file:
                    raise ValueError(f"{code}: output file is required.")

                geo_out = (self.tbl_opt_ext.cellWidget(r, 3).text() or "geo_opt.xyz").strip()  # type: ignore

                argv.append(out_file)
                argv.append("--extract-geo")
                argv.extend(["--geo-out", geo_out])

                if code == "GAU":
                    tmpl_cell = self.tbl_opt_ext.cellWidget(r, 2)
                    tmpl = tmpl_cell.text() if isinstance(tmpl_cell, FileCell) else ""
                    if tmpl:
                        argv.extend(["--xyz-template", tmpl])

        # -------- HESSIAN --------
        elif page == 1:
            code = self.cb_hess_code.currentText()
            inp = self.fc_hess_in.text()
            if not inp:
                raise ValueError("Hessian input is required.")
            argv.append(inp)
            argv.extend(["-m", (self.ed_mat_out.text() or "Hessian.out").strip()])
            argv.extend(["-v", (self.ed_vec_out.text() or "Hessian_flat.out").strip()])
            if code == "ORCA":
                argv.append("--orca-hess")
            elif code == "QCHEM":
                argv.append("--qchem-hess")

        # -------- BOMD --------
        elif page == 2:
            tab = self.bomd_tabs.currentIndex()
            if tab == 2:
                # custom args
                s = (self.ed_custom_args.toPlainText() or "").strip()
                if not s:
                    raise ValueError("Custom args are empty.")
                argv = shlex.split(s)
            elif tab == 0:
                # generate
                code = self.cb_bomd_code.currentText()
                xyz = self.fc_bomd_xyz.text()
                vel = self.fc_bomd_vel.text()
                if not xyz:
                    raise ValueError("BOMD: XYZ is required.")

                argv.append(xyz)
                argv.extend(["--THEORY", (self.ed_theory.text() or "B3LYP").strip()])
                argv.extend(["--BS", (self.ed_bs.text() or "Def2TZVP").strip()])
                argv.extend(["--convergence", (self.ed_conv.text() or "VeryTight").strip()])
                argv.extend(["--Nproc", str(int(self.sp_nproc.value()))])
                argv.extend(["--mem", (self.ed_mem.text() or "300Gb").strip()])
                argv.extend(["--charge", str(int(self.sp_charge.value()))])
                argv.extend(["--mult", str(int(self.sp_mult.value()))])

                if code == "GAU":
                    argv.append("--dyn")
                    if vel:
                        argv.extend(["--vel-file", vel])
                    argv.extend(["--stepsize", str(int(self.sp_stepsize.value()))])
                    argv.extend(["--npoints", str(int(self.sp_npoints.value()))])
                    argv.extend(["--dyn-out", (self.ed_dyn_out.text() or "dyn.com").strip()])
                    if (self.ed_gau_disp.text() or "").strip():
                        argv.extend(["--gau-dispersion", (self.ed_gau_disp.text() or "").strip()])
                elif code == "ORCA":
                    argv.append("--orca-qmd")
                    if vel:
                        argv.extend(["--orca-vel-file", vel])
                    argv.extend(["--orca-vel-unit", self.cb_orca_vel_unit.currentText()])
                    argv.extend(["--qmd-timestep", f"{float(self.sp_orca_dt.value()):.3f}"])
                    argv.extend(["--qmd-run", str(int(self.sp_orca_run.value()))])
                    if (self.ed_orca_prefix.text() or "").strip():
                        argv.extend(["--qmd-prefix", (self.ed_orca_prefix.text() or "").strip()])
                    if (self.ed_orca_disp.text() or "").strip():
                        argv.extend(["--orca-dispersion", (self.ed_orca_disp.text() or "").strip()])
                else:
                    argv.append("--qchem-qmd")
                    if vel:
                        argv.extend(["--qchem-vel-file", vel])
                    argv.extend(["--qchem-qmd-out", (self.ed_qchem_dyn_out.text() or "dyn.inp").strip()])
                    argv.extend(["--qchem-timestep", str(int(self.sp_qchem_dt.value()))])
                    argv.extend(["--qchem-steps", str(int(self.sp_qchem_steps.value()))])
                    argv.extend(["--qchem-print", str(int(self.sp_qchem_print.value()))])
                    if (self.ed_qchem_dft_d.text() or "").strip():
                        argv.extend(["--qchem-dft-d", (self.ed_qchem_dft_d.text() or "").strip()])

            else:
                # parse -> nimbus
                code = self.cb_parse_code.currentText()
                outbase = (self.ed_outbase.text() or "parsed_log").strip() or "parsed_log"
                nimbus_out = (self.ed_nimbus_out.text() or "").strip()
                epot_out = (self.ed_epot_out.text() or "").strip()
                i0 = int(self.sp_i.value())
                i1 = int(self.sp_f.value())

                if code == "GAU":
                    gout = self.fc_gau_out.text()
                    gxyz = self.fc_gau_xyz.text()
                    if not gout or not gxyz:
                        raise ValueError("Gaussian parse needs Gaussian out + xyz template.")
                    # NOTE: bulma.py requires -i/--inizio and -f/--fine with --parse-dyn
                    if i0 <= 0 or i1 <= 0:
                        raise ValueError("Gaussian parse requires start (-i/--inizio) and end (-f/--fine) > 0.")

                    argv.append(gout)
                    argv.append("--parse-dyn")
                    argv.extend(["-i", str(i0), "-f", str(i1)])
                    # Always write flying_nimbus trajectory in this tab
                    argv.extend(["--xyz", gxyz, "-o", outbase, "--nimbus-traj"])
                    if nimbus_out: argv.extend(["--nimbus-out", nimbus_out])
                    if self.cb_total.isChecked(): argv.append("--total")
                elif code == "ORCA":
                    traj = self.fc_orca_traj.text()
                    vel = self.fc_orca_vel.text()
                    if not traj or not vel:
                        raise ValueError("ORCA parse needs trajectory.xyz + velocity.xyz.")
                    argv.append(traj)
                    argv.append("--parse-orca-qmd")
                    if i0 > 0: argv.extend(["-i", str(i0)])
                    if i1 > 0: argv.extend(["-f", str(i1)])
                    argv.extend(["--orca-traj", traj, "--orca-vel", vel, "-o", outbase])
                    if nimbus_out: argv.extend(["--nimbus-out", nimbus_out])
                    if epot_out: argv.extend(["--epot-out", epot_out])
                else:
                    qout = self.fc_qchem_out.text()
                    if not qout:
                        raise ValueError("Q-Chem parse needs the Q-Chem .out file.")
                    argv.append(qout)
                    argv.append("--parse-qchem-qmd")
                    if i0 > 0: argv.extend(["-i", str(i0)])
                    if i1 > 0: argv.extend(["-f", str(i1)])
                    argv.extend(["-o", outbase])
                    if nimbus_out: argv.extend(["--nimbus-out", nimbus_out])
                    if epot_out: argv.extend(["--epot-out", epot_out])

        else:
            raise ValueError("Select Opt, Hessian, or BOMD to run.")

        return BulmaJob(workdir=workdir, pyexe=pyexe, bulma_script=bulma, argv=argv)

    # ---------------- run/stop/log ----------------
    def _set_running(self, running: bool):
        self.act_run.setEnabled(not running)
        self.act_stop.setEnabled(running)
        self.sidebar.setEnabled(not running)

    def _run(self):
        if self.worker is not None and self.worker.isRunning():
            QtWidgets.QMessageBox.information(self, "Already running", "A run is already in progress.")
            return
        try:
            job = self._bulma_job()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Invalid settings", str(e))
            return

        self.txt_log.clear()
        self.worker = BulmaWorker(job, parent=self)
        self.worker.log.connect(self._append_log)
        self.worker.done.connect(self._on_done)
        self.worker.start()
        self._set_running(True)

    def _stop(self):
        if self.worker is None:
            return
        self.worker.request_cancel()
        self._append_log("\n[GUI] Cancel requested.\n")
        # Banner is user-closable; keep it unless you want to force-close on cancel.

    def _append_log(self, s: str):
        if not s:
            return
        self.txt_log.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.txt_log.insertPlainText(s)
        self.txt_log.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def _on_done(self, code: int):
        self._append_log(f"\n[done] exit code {code}\n")
        self._set_running(False)


    # ---------------- help + settings ----------------
    def _try_build_cmd_preview(self) -> tuple[str | None, Path | None, str | None]:
        try:
            job = self._bulma_job()
            cmd = [str(job.pyexe), str(job.bulma_script)] + job.argv
            cmd_s = " ".join(shlex.quote(c) for c in cmd)
            return cmd_s, job.workdir, None
        except Exception as e:
            return None, None, str(e)

    def _help_text_for_current_ui(self, page: int) -> str:
        """Return a human-readable explanation of the currently selected GUI action."""
        lines: list[str] = []

        # -------- OPT --------
        if page == 0:
            tab = self.opt_tabs.currentIndex()

            # Tab: create OPT/FREQ input
            if tab == 0:
                r = self.tbl_opt_gen.currentRow()
                if r < 0:
                    r = 0
                code_item = self.tbl_opt_gen.item(r, 0)
                code = (code_item.text() if code_item else "GAU").strip().upper()

                cb = self.tbl_opt_gen.cellWidget(r, 2)
                idx = cb.currentIndex() if isinstance(cb, QtWidgets.QComboBox) else 0
                mode_txt = cb.currentText() if isinstance(cb, QtWidgets.QComboBox) else ""

                if code == "GAU":
                    flag = "--opt" if idx == 0 else "--freq"
                    out = "geom.com" if idx == 0 else "geom_freq.com"
                elif code == "ORCA":
                    flag = "--orca-opt" if idx == 0 else "--orca-freq"
                    out = "geom.inp" if idx == 0 else "geom_freq.inp"
                else:
                    if idx == 0:
                        flag, out = "--qchem-opt-single", "opt.inp"
                    elif idx == 1:
                        flag, out = "--qchem-opt", "opt.inp"
                    else:
                        flag, out = "--qchem-freq", "freq.inp"

                lines += [
                    "Opt → Create OPT/FREQ input",
                    f"Selected: {code}  |  {mode_txt}",
                    "",
                    "What it does:",
                    f"- Reads an equilibrium XYZ geometry and writes an input file for {code}.",
                    "",
                    "Outputs (written in the workdir):",
                    f"- {out}   (NOTE: Bulma writes fixed filenames; the table 'Output' column is only a hint.)",
                    "",
                    "Required:",
                    "- XYZ (equilibrium geometry)",
                    "",
                    "ab initio settings used:",
                    "- THEORY, BS, charge, mult, Nproc, mem",
                ]
                if flag in ("--opt", "--orca-opt", "--qchem-opt", "--qchem-opt-single"):
                    lines.append("- convergence (used for OPT)")

                lines += [
                    "",
                    "CLI flag used:",
                    f"- {flag}",
                ]

                if code == "QCHEM":
                    lines += [
                        "",
                        "Q-Chem notes:",
                        "- 'single' variants generate a template-like single job.",
                        "- 'multi' optimization (--qchem-opt) writes an opt.inp with multiple jobs.",
                    ]

            # Tab: extract optimized geometry
            else:
                r = self.tbl_opt_ext.currentRow()
                if r < 0:
                    r = 0
                code_item = self.tbl_opt_ext.item(r, 0)
                code = (code_item.text() if code_item else "GAU").strip().upper()

                geo_out_w = self.tbl_opt_ext.cellWidget(r, 3)
                geo_out = (geo_out_w.text() if isinstance(geo_out_w, QtWidgets.QLineEdit) else "geo_opt.xyz").strip() or "geo_opt.xyz"

                lines += [
                    "Opt → Extract optimized geometry",
                    f"Selected: {code}",
                    "",
                    "What it does:",
                    "- Extracts the last optimized geometry from the chosen output and writes an XYZ file.",
                    "",
                    "Output (written in the workdir):",
                    f"- {geo_out}",
                    "",
                    "Required:",
                    "- OUT (.out/.log) for the chosen code",
                ]
                if code == "GAU":
                    lines += [
                        "",
                        "Gaussian note:",
                        "- You can provide an XYZ template (symbols/order) via --xyz-template (optional but recommended).",
                    ]

                lines += [
                    "",
                    "CLI flag used:",
                    "- --extract-geo  (plus --geo-out <file>)",
                ]

        # -------- HESSIAN --------
        elif page == 1:
            code = self.cb_hess_code.currentText().strip().upper()
            lines += [
                "Hessian → Extract Hessian (matrix + flattened vector)",
                f"Selected: {code}",
                "",
                "What it does:",
                "- Writes the lower-triangular Hessian in Bulma format (Hessian.out) and a flattened 1-column vector (Hessian_flat.out).",
                "",
                "Inputs:",
            ]
            if code == "GAU":
                lines += ["- Gaussian output (.out/.log) (default mode: no extra flag)"]
            elif code == "ORCA":
                lines += ["- ORCA .hess file (uses --orca-hess)"]
            else:
                lines += ["- Q-Chem HESS file (uses --qchem-hess)"]

            lines += [
                "",
                "Outputs (written in the workdir):",
                "- Hessian.out        (matrix-out)",
                "- Hessian_flat.out   (vector-out)",
            ]

        # -------- BOMD --------
        elif page == 2:
            tab = self.bomd_tabs.currentIndex()

            # Tab: Generate
            if tab == 0:
                code = self.cb_bomd_code.currentText().strip().upper()
                lines += [
                    "BOMD → Generate inputs",
                    f"Selected: {code}",
                    "",
                    "What it does:",
                    "- Generates an input for a dynamics run starting from an equilibrium XYZ (and optional velocities).",
                    "",
                    "Required:",
                    "- XYZ (equilibrium geometry)",
                ]
                if code == "GAU":
                    lines += [
                        "",
                        "Outputs (written in the workdir):",
                        "- dyn.com  (Gaussian BOMD input)",
                        "",
                        "Extra inputs/options:",
                        "- --vel-file velocity_gau.xyz (optional but normally used)",
                        "- --stepsize, --npoints, --dyn-out",
                        "",
                        "CLI flag used:",
                        "- --dyn",
                    ]
                elif code == "ORCA":
                    lines += [
                        "",
                        "Outputs (written in the workdir):",
                        "- <prefix>_qmd.inp",
                        "- <prefix>_qmd.mdrestart",
                        "",
                        "Extra inputs/options:",
                        "- --orca-vel-file velocity_orca.xyz (optional but normally used)",
                        "- --orca-vel-unit (au / angfs), --qmd-timestep (fs), --qmd-run, --qmd-prefix",
                        "",
                        "CLI flag used:",
                        "- --orca-qmd",
                    ]
                else:
                    lines += [
                        "",
                        "Outputs (written in the workdir):",
                        "- dyn.inp  (Q-Chem AIMD/QMD input)",
                        "",
                        "Extra inputs/options:",
                        "- --qchem-vel-file velocity.xyz (optional but normally used)",
                        "- --qchem-qmd-out, --qchem-timestep (a.u.), --qchem-steps, --qchem-print",
                        "",
                        "CLI flag used:",
                        "- --qchem-qmd",
                    ]

                lines += [
                    "",
                    "ab initio settings used (shared):",
                    "- THEORY, BS, convergence, Nproc, mem, charge, mult",
                ]

            # Tab: Parse → Nimbus
            elif tab == 1:
                code = self.cb_parse_code.currentText().strip().upper()
                lines += [
                    "BOMD → Parse → Nimbus trajectory",
                    f"Selected: {code}",
                    "",
                    "What it does:",
                    "- Converts dynamics outputs into a flying_nimbus-compatible trajectory (x in Å; v in bohr/au_time).",
                    "",
                    "Main output (written in the workdir):",
                    "- <output>_traj.xyz  (or custom --nimbus-out)",
                ]
                if code == "GAU":
                    lines += [
                        "",
                        "Required:",
                        "- Gaussian output (.out/.log)",
                        "- XYZ template at equilibrium (--xyz) for symbols/order",
                        "- Start/end steps (-i/--inizio and -f/--fine) are required",
                        "",
                        "Optional:",
                        "- --total writes <output>_energies.dat (Ekin/Epot/Etot)",
                        "",
                        "CLI flag used:",
                        "- --parse-dyn  (GUI always adds --nimbus-traj)",
                    ]
                elif code == "ORCA":
                    lines += [
                        "",
                        "Required:",
                        "- trajectory.xyz and velocity.xyz dumps",
                        "",
                        "Optional:",
                        "- --epot-out writes an E_pot column vector parsed from trajectory.xyz comments",
                        "",
                        "CLI flag used:",
                        "- --parse-orca-qmd",
                    ]
                else:
                    lines += [
                        "",
                        "Required:",
                        "- Q-Chem AIMD/QMD .out file",
                        "",
                        "Optional:",
                        "- --epot-out writes an E_pot column vector parsed from Q-Chem output",
                        "",
                        "CLI flag used:",
                        "- --parse-qchem-qmd",
                    ]

            # Tab: Custom args
            else:
                lines += [
                    "BOMD → Custom args",
                    "",
                    "What it does:",
                    "- Runs ANY bulma.py command from the GUI.",
                    "- The text box is passed verbatim as arguments after:  python bulma.py",
                    "",
                    "Tip:",
                    "- Use this when the GUI does not expose a specific Bulma option yet.",
                ]

        else:
            lines += [
                "About",
                "",
                "BULMA GUI",
                "",
                "Authors: Giacomo Mandelli, Giacomo Botti",
            ]

        return "\n".join(lines).rstrip() + "\n"

    def _update_help(self):
        page = self.sidebar.currentRow()
        txt = self._help_text_for_current_ui(page)

        if self._help_key:
            title = self._help_title or self._help_key
            body = self.HELP.get(self._help_key, "No help available.")
            h = f"<h3>{html.escape(title)}</h3><p>{html.escape(body)}</p><hr><pre>{html.escape(txt)}</pre>"
        else:
            h = f"<pre>{html.escape(txt)}</pre>"

        self.txt_help.setHtml(h)


    def _on_any_change(self, *args):
        if not getattr(self, "_ui_ready", False):
            return
        self._update_help()
        self._save_settings()

    def _save_settings(self):
        if not getattr(self, "_ui_ready", False):
            return
        self.settings.setValue("workdir", (self.ed_workdir.text() or "").strip())

        # Hess
        if hasattr(self, "cb_hess_code"):
            self.settings.setValue("hess_code", int(self.cb_hess_code.currentIndex()))
        if hasattr(self, "fc_hess_in"):
            self.settings.setValue("hess_in", self.fc_hess_in.text())
        if hasattr(self, "ed_mat_out"):
            self.settings.setValue("mat_out", (self.ed_mat_out.text() or "").strip())
        if hasattr(self, "ed_vec_out"):
            self.settings.setValue("vec_out", (self.ed_vec_out.text() or "").strip())

        # BOMD
        self.settings.setValue("bomd_code", int(self.cb_bomd_code.currentIndex()))
        self.settings.setValue("bomd_xyz", self.fc_bomd_xyz.text())
        self.settings.setValue("bomd_vel", self.fc_bomd_vel.text())
        self.settings.setValue("theory", (self.ed_theory.text() or "").strip())
        self.settings.setValue("bs", (self.ed_bs.text() or "").strip())
        self.settings.setValue("conv", (self.ed_conv.text() or "").strip())
        self.settings.setValue("nproc", int(self.sp_nproc.value()))
        self.settings.setValue("mem", (self.ed_mem.text() or "").strip())
        self.settings.setValue("charge", int(self.sp_charge.value()))
        self.settings.setValue("mult", int(self.sp_mult.value()))
        self.settings.setValue("dyn_stepsize", int(self.sp_stepsize.value()))
        self.settings.setValue("dyn_npoints", int(self.sp_npoints.value()))
        self.settings.setValue("dyn_out", (self.ed_dyn_out.text() or "").strip())
        self.settings.setValue("gau_disp", (self.ed_gau_disp.text() or "").strip())
        self.settings.setValue("orca_vel_unit", int(self.cb_orca_vel_unit.currentIndex()))
        self.settings.setValue("orca_dt", float(self.sp_orca_dt.value()))
        self.settings.setValue("orca_run", int(self.sp_orca_run.value()))
        self.settings.setValue("orca_prefix", (self.ed_orca_prefix.text() or "").strip())
        self.settings.setValue("orca_disp", (self.ed_orca_disp.text() or "").strip())
        self.settings.setValue("qchem_dt", int(self.sp_qchem_dt.value()))
        self.settings.setValue("qchem_steps", int(self.sp_qchem_steps.value()))
        self.settings.setValue("qchem_print", int(self.sp_qchem_print.value()))
        self.settings.setValue("qchem_dyn_out", (self.ed_qchem_dyn_out.text() or "").strip())
        self.settings.setValue("qchem_dft_d", (self.ed_qchem_dft_d.text() or "").strip())

        # Parse
        self.settings.setValue("parse_code", int(self.cb_parse_code.currentIndex()))
        self.settings.setValue("gau_out", self.fc_gau_out.text())
        self.settings.setValue("gau_xyz", self.fc_gau_xyz.text())
        self.settings.setValue("orca_traj", self.fc_orca_traj.text())
        self.settings.setValue("orca_vel", self.fc_orca_vel.text())
        self.settings.setValue("qchem_out", self.fc_qchem_out.text())
        self.settings.setValue("i0", int(self.sp_i.value()))
        self.settings.setValue("i1", int(self.sp_f.value()))
        self.settings.setValue("outbase", (self.ed_outbase.text() or "").strip())
        self.settings.setValue("nimbus_out", (self.ed_nimbus_out.text() or "").strip())
        self.settings.setValue("epot_out", (self.ed_epot_out.text() or "").strip())
        self.settings.setValue("total", bool(self.cb_total.isChecked()))
        self.settings.setValue("custom_args", (self.ed_custom_args.toPlainText() or "").strip())

        # OPT tables
        try:
            codes = ["GAU", "ORCA", "QCHEM"]
            for r, code in enumerate(codes):
                fc = self.tbl_opt_gen.cellWidget(r, 1)
                self.settings.setValue(f"optgen_{code}_xyz", fc.text() if isinstance(fc, FileCell) else "")
                cb = self.tbl_opt_gen.cellWidget(r, 2)
                if isinstance(cb, QtWidgets.QComboBox):
                    self.settings.setValue(f"optgen_{code}_variant", int(cb.currentIndex()))
                for c, key in [(3, "theory"), (4, "bs"), (5, "conv"), (7, "mem"), (10, "disp")]:
                    ed = self.tbl_opt_gen.cellWidget(r, c)
                    if isinstance(ed, QtWidgets.QLineEdit):
                        self.settings.setValue(f"optgen_{code}_{key}", ed.text())
                sp = self.tbl_opt_gen.cellWidget(r, 6)
                if isinstance(sp, QtWidgets.QSpinBox):
                    self.settings.setValue(f"optgen_{code}_nproc", int(sp.value()))
                sp = self.tbl_opt_gen.cellWidget(r, 8)
                if isinstance(sp, QtWidgets.QSpinBox):
                    self.settings.setValue(f"optgen_{code}_charge", int(sp.value()))
                sp = self.tbl_opt_gen.cellWidget(r, 9)
                if isinstance(sp, QtWidgets.QSpinBox):
                    self.settings.setValue(f"optgen_{code}_mult", int(sp.value()))

                fc = self.tbl_opt_ext.cellWidget(r, 1)
                self.settings.setValue(f"optext_{code}_out", fc.text() if isinstance(fc, FileCell) else "")
                fc = self.tbl_opt_ext.cellWidget(r, 2)
                self.settings.setValue(f"optext_{code}_tmpl", fc.text() if isinstance(fc, FileCell) else "")
                ed = self.tbl_opt_ext.cellWidget(r, 3)
                if isinstance(ed, QtWidgets.QLineEdit):
                    self.settings.setValue(f"optext_{code}_geoout", ed.text())
        except Exception:
            pass

    def _restore_settings(self):
        self.ed_workdir.setText(self.settings.value("workdir", str(Path.cwd())))

        # Hess
        try:
            self.cb_hess_code.setCurrentIndex(int(self.settings.value("hess_code", 0)))
        except Exception:
            pass
        self.fc_hess_in.setText(self.settings.value("hess_in", ""))
        self.ed_mat_out.setText(self.settings.value("mat_out", "Hessian.out"))
        self.ed_vec_out.setText(self.settings.value("vec_out", "Hessian_flat.out"))

        # BOMD
        try:
            self.cb_bomd_code.setCurrentIndex(int(self.settings.value("bomd_code", 0)))
        except Exception:
            pass
        self.fc_bomd_xyz.setText(self.settings.value("bomd_xyz", ""))
        self.fc_bomd_vel.setText(self.settings.value("bomd_vel", ""))
        self.ed_theory.setText(self.settings.value("theory", "B3LYP"))
        self.ed_bs.setText(self.settings.value("bs", "Def2TZVP"))
        self.ed_conv.setText(self.settings.value("conv", "VeryTight"))
        try:
            self.sp_nproc.setValue(int(self.settings.value("nproc", 48)))
        except Exception:
            pass
        self.ed_mem.setText(self.settings.value("mem", "300Gb"))
        try:
            self.sp_charge.setValue(int(self.settings.value("charge", 0)))
            self.sp_mult.setValue(int(self.settings.value("mult", 1)))
        except Exception:
            pass
        try:
            self.sp_stepsize.setValue(int(self.settings.value("dyn_stepsize", 2000)))
            self.sp_npoints.setValue(int(self.settings.value("dyn_npoints", 2500)))
        except Exception:
            pass
        self.ed_dyn_out.setText(self.settings.value("dyn_out", "dyn.com"))
        self.ed_gau_disp.setText(self.settings.value("gau_disp", ""))

        try:
            self.cb_orca_vel_unit.setCurrentIndex(int(self.settings.value("orca_vel_unit", 0)))
        except Exception:
            pass
        try:
            self.sp_orca_dt.setValue(float(self.settings.value("orca_dt", 0.200)))
            self.sp_orca_run.setValue(int(self.settings.value("orca_run", 2501)))
        except Exception:
            pass
        self.ed_orca_prefix.setText(self.settings.value("orca_prefix", ""))
        self.ed_orca_disp.setText(self.settings.value("orca_disp", ""))

        try:
            self.sp_qchem_dt.setValue(int(self.settings.value("qchem_dt", 8)))
            self.sp_qchem_steps.setValue(int(self.settings.value("qchem_steps", 2500)))
            self.sp_qchem_print.setValue(int(self.settings.value("qchem_print", 1)))
        except Exception:
            pass
        self.ed_qchem_dyn_out.setText(self.settings.value("qchem_dyn_out", "dyn.inp"))
        self.ed_qchem_dft_d.setText(self.settings.value("qchem_dft_d", ""))

        # Parse
        try:
            self.cb_parse_code.setCurrentIndex(int(self.settings.value("parse_code", 0)))
        except Exception:
            pass
        self.fc_gau_out.setText(self.settings.value("gau_out", ""))
        self.fc_gau_xyz.setText(self.settings.value("gau_xyz", ""))
        self.fc_orca_traj.setText(self.settings.value("orca_traj", "trajectory.xyz"))
        self.fc_orca_vel.setText(self.settings.value("orca_vel", "velocity.xyz"))
        self.fc_qchem_out.setText(self.settings.value("qchem_out", ""))
        try:
            self.sp_i.setValue(int(self.settings.value("i0", 0)))
            self.sp_f.setValue(int(self.settings.value("i1", 0)))
        except Exception:
            pass
        self.ed_outbase.setText(self.settings.value("outbase", "parsed_log"))
        self.ed_nimbus_out.setText(self.settings.value("nimbus_out", ""))
        self.ed_epot_out.setText(self.settings.value("epot_out", ""))
        try:
            self.cb_total.setChecked(bool(self.settings.value("total", False)))
        except Exception:
            pass
        self.ed_custom_args.setPlainText(self.settings.value("custom_args", ""))

        # OPT tables
        try:
            codes = ["GAU", "ORCA", "QCHEM"]
            for r, code in enumerate(codes):
                fc = self.tbl_opt_gen.cellWidget(r, 1)
                if isinstance(fc, FileCell):
                    fc.setText(self.settings.value(f"optgen_{code}_xyz", ""))
                cb = self.tbl_opt_gen.cellWidget(r, 2)
                if isinstance(cb, QtWidgets.QComboBox):
                    try:
                        cb.setCurrentIndex(int(self.settings.value(f"optgen_{code}_variant", 0)))
                    except Exception:
                        pass
                for c, key, default in [(3, "theory", "B3LYP"), (4, "bs", "Def2TZVP"), (5, "conv", "VeryTight"), (7, "mem", "300Gb"), (10, "disp", "")]:
                    ed = self.tbl_opt_gen.cellWidget(r, c)
                    if isinstance(ed, QtWidgets.QLineEdit):
                        ed.setText(self.settings.value(f"optgen_{code}_{key}", default))
                sp = self.tbl_opt_gen.cellWidget(r, 6)
                if isinstance(sp, QtWidgets.QSpinBox):
                    try:
                        sp.setValue(int(self.settings.value(f"optgen_{code}_nproc", 48)))
                    except Exception:
                        pass
                sp = self.tbl_opt_gen.cellWidget(r, 8)
                if isinstance(sp, QtWidgets.QSpinBox):
                    try:
                        sp.setValue(int(self.settings.value(f"optgen_{code}_charge", 0)))
                    except Exception:
                        pass
                sp = self.tbl_opt_gen.cellWidget(r, 9)
                if isinstance(sp, QtWidgets.QSpinBox):
                    try:
                        sp.setValue(int(self.settings.value(f"optgen_{code}_mult", 1)))
                    except Exception:
                        pass

                fc = self.tbl_opt_ext.cellWidget(r, 1)
                if isinstance(fc, FileCell):
                    fc.setText(self.settings.value(f"optext_{code}_out", ""))
                fc = self.tbl_opt_ext.cellWidget(r, 2)
                if isinstance(fc, FileCell):
                    fc.setText(self.settings.value(f"optext_{code}_tmpl", ""))
                ed = self.tbl_opt_ext.cellWidget(r, 3)
                if isinstance(ed, QtWidgets.QLineEdit):
                    ed.setText(self.settings.value(f"optext_{code}_geoout", "geo_opt.xyz"))
        except Exception:
            pass

    def closeEvent(self, event: QtGui.QCloseEvent):
        if getattr(self, "_ui_ready", False):
            self._save_settings()
        super().closeEvent(event)

    def _open_workdir(self):
        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        if wd.exists():
            open_in_file_manager(wd)

    # ---------------- theme ----------------
    def _apply_theme(self, dark: bool = True):
        self.act_toggle_dark.blockSignals(True)
        self.act_toggle_dark.setChecked(bool(dark))
        self.act_toggle_dark.blockSignals(False)

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
        QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox, QSpinBox, QDoubleSpinBox, QTableWidget {
            background: #0f172a; border: 1px solid #1f2937; border-radius: 12px; padding: 6px;
        }
        QHeaderView::section { background: #111827; border: 1px solid #1f2937; padding: 6px; }
        QDockWidget::title { background: #111827; padding: 8px; border: 1px solid #1f2937; }
        QScrollArea { border: none; }
        QFrame#AboutCard { background: #0f172a; border: 1px solid #1f2937; border-radius: 18px; }
        """
        self.setStyleSheet(qss_dark if dark else "")


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("BulmaGUI")
    app.setQuitOnLastWindowClosed(False)

    # Startup splash (stays until the user clicks it to close)
    splash_txt = (ASCII_BANNER or "").rstrip("\n")
    splash = None
    if splash_txt.strip():
        splash = AsciiSplash(splash_txt, title="BULMA")
        # Center on the primary screen
        try:
            screen = app.primaryScreen()
            if screen is not None:
                g = screen.availableGeometry()
                splash.move(g.center() - QtCore.QPoint(splash.width() // 2, splash.height() // 2))
        except Exception:
            pass
        splash.show()
    def launch_main():
        # Create/show the main window only once.
        if getattr(app, "_main_window", None) is not None:
            return
        w = BulmaMainWindow()
        app._main_window = w
        w.show()
        app.setQuitOnLastWindowClosed(True)
        try:
            w.raise_()
            w.activateWindow()
        except Exception:
            pass

    if splash is not None:
        splash.splashClosed.connect(launch_main)
    else:
        launch_main()

    app._startup_splash = splash

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
