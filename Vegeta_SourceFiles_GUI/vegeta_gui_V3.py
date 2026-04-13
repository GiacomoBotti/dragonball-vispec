#!/usr/bin/env python3

#SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#Authors: Giacomo Mandelli, Giacomo Botti

"""
Vegeta GUI (PyQt6)

Requirements:
  pip install PyQt6 numpy

Run:
  python vegeta_gui.py

Note:
  Put vegeta_V2.py next to this file.
"""
from __future__ import annotations

import contextlib
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

# ---- Qt (PyQt6) ----
try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except Exception:
    print("PyQt6 not found. Install with: pip install PyQt6", file=sys.stderr)
    raise

# ---- Vegeta core (must be next to this GUI) ----
try:
    import vegeta_V2 as vegeta
except Exception:
    print("Could not import vegeta_V2.py. Put it next to this GUI.", file=sys.stderr)
    raise


# ---------------------------
# Startup splash (click to close)
# ---------------------------
ASCII_BANNER = r"""
                                     ,
                               ,   ,'|
                             ,/|.-'   \\.
                          .-'  '       |.
                    ,  .-'              |
                   /|,'                 |'
                  / '                    |  ,
                 /                       ,'/
              .  |          _              /
               \\`' .-.    ,' `.           |
                \\ /   \\ /      \\          /
                 \\|    V        |        |  ,
                  (           ) /.--.   ''"/
                  "b.`. ,' _.ee'' 6)|   ,-'
                    \\"= --""  )   ' /.-'
                     \\ / `---"   ."|'
                      \\"..-    .'  |.
                       `-__..-','   |
                     __.) ' .-'/    /\\._
               _.--'/----..--------. _.-""-._
            .-'_)   \\.   /     __..-'     _.-'--.
           / -'/      #########         ,'-.   . `.
          | ' /                        /    `   `. \\
          |   |                        |         | |
           \\ .'\\                       |     \\     |
          / '  | ,'               . -  \\`.    |  / /
         / /   | |                      `/"--. -' /\\
        | |     \\ \\                     /     \\     |
        | \\      | \\                  .-|      |    |
     ██╗   ██╗███████╗ ██████╗ ███████╗████████╗ █████╗
     ██║   ██║██╔════╝██╔════╝ ██╔════╝╚══██╔══╝██╔══██╗
     ██║   ██║█████╗  ██║  ███╗█████╗     ██║   ███████║
     ╚██╗ ██╔╝██╔══╝  ██║   ██║██╔══╝     ██║   ██╔══██║
      ╚████╔╝ ███████╗╚██████╔╝███████╗   ██║   ██║  ██║
       ╚═══╝  ╚══════╝ ╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝

            Velocity Generator for Time-Averaged
                   Quasiclassical Spectra
                
                Click anywhere to proceed =)

"""

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
        lay.setSpacing(0)

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
            desktop = screens[0].geometry()
            for sc in screens[1:]:
                desktop = desktop.united(sc.geometry())
        else:
            desktop = QtCore.QRect(0, 0, 1400, 900)

        self.setGeometry(desktop)

        # Center the widget if it fits, otherwise left-align to avoid losing left-side characters
        fm = QtGui.QFontMetrics(fixed)
        lines = (text.splitlines() or [""])
        text_w = max(fm.horizontalAdvance(line) for line in lines)
        text_h = fm.lineSpacing() * len(lines)

        if (text_w <= desktop.width()) and (text_h <= desktop.height()):
            lay.addWidget(self.lbl, 0, QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        else:
            lay.addWidget(self.lbl, 0, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        self.close()

    def closeEvent(self, ev: QtGui.QCloseEvent):
        try:
            self.splashClosed.emit()
        finally:
            super().closeEvent(ev)



# ---------------------------
# Utilities
# ---------------------------
def _parse_tokens(text: str) -> list[str]:
    """Split a text field into tokens (ranges/commas stay inside tokens)."""
    s = (text or "").strip()
    return s.split() if s else []


def safe_read_nat_from_xyz(path_text: str) -> int:
    ptxt = (path_text or "").strip()
    if not ptxt:
        return 0
    p = Path(ptxt).expanduser()
    if not p.is_file():
        return 0
    try:
        return int(p.read_text().splitlines()[0].split()[0])
    except Exception:
        return 0


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


# ---------------------------
# Worker thread
# ---------------------------
class _QtStream:
    def __init__(self, emit_fn):
        self.emit_fn = emit_fn

    def write(self, s: str):
        if s:
            self.emit_fn(s)

    def flush(self):
        pass


@dataclass
class VegetaJob:
    workdir: Path
    xyz: str
    hess: str
    output: str
    nrotrasl: int
    on_text: str
    off_text: str
    freq_thresh: Optional[float]
    clean_cnorm: bool
    cnorm_out: str
    print_modes: bool
    frames: int
    cycles: int
    gau_vel: bool
    zero_vel_atoms: str
    geo_only: bool
    pa_xyz: str


class VegetaWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(int)

    def __init__(self, job: VegetaJob, parent=None):
        super().__init__(parent)
        self.job = job
        self._cancel = False  # best effort

    def request_cancel(self):
        self._cancel = True

    def run(self):
        try:
            stream = _QtStream(self.log.emit)
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                self._run_job()
            self.done.emit(0)
        except Exception:
            self.log.emit("\n" + traceback.format_exc() + "\n")
            self.done.emit(1)

    def _run_job(self):
        job = self.job
        job.workdir.mkdir(parents=True, exist_ok=True)
        os.chdir(job.workdir)

        xyz = Path(job.xyz).expanduser()
        if not xyz.is_file():
            raise FileNotFoundError(f"XYZ not found: {xyz}")

        symb, x_ang = vegeta.read_xyz_geometry(str(xyz))
        nat = len(symb)
        xm = vegeta.build_cart_masses(symb)

        # geometry-only / PA output
        if job.geo_only or job.pa_xyz:
            x_pa = x_ang.copy()
            com = vegeta.shift_coords_to_com(xm, x_pa)
            vegeta.paframe(xm, x_pa)  # rotates in-place to PA
            out_pa = Path(job.pa_xyz).expanduser() if job.pa_xyz else xyz.with_name(xyz.stem + "_pa.xyz")
            vegeta.write_geom_xyz(
                out_pa, symb, x_pa,
                comment=f"COM shifted and rotated to principal axes; COM(Ang)={com[0]:.6f} {com[1]:.6f} {com[2]:.6f}"
            )
            print(f"[geo] wrote: {out_pa}")
            if job.geo_only:
                return

        hess = Path(job.hess).expanduser()
        if not hess.is_file():
            raise FileNotFoundError(f"Hessian not found: {hess}")

        if job.nrotrasl not in (5, 6):
            raise ValueError("--nrotrasl must be 5 or 6")

        ncart = 3 * nat
        nvib = ncart - int(job.nrotrasl)
        if nvib <= 0:
            raise ValueError(f"Invalid nvib={nvib}. Check nrotrasl.")

        nexc = vegeta.np.zeros(nvib, dtype=int)
        nNOener = vegeta.np.zeros(nvib, dtype=int)

        on_modes = vegeta.expand_mode_tokens(_parse_tokens(job.on_text), nvib) if job.on_text.strip() else []
        off_modes = vegeta.expand_mode_tokens(_parse_tokens(job.off_text), nvib) if job.off_text.strip() else []

        for m in on_modes:
            nexc[m - 1] = 1
        for m in off_modes:
            nNOener[m - 1] = 1
            nexc[m - 1] = 0

        x_bohr = x_ang.copy() * vegeta.ANG2BOHR
        hc = vegeta.read_hessian_nwchem(str(hess), ncart)
        ww, cnorm, gamma = vegeta.diagonalize_mass_weighted_hessian(hc, xm, nvib, clean=job.clean_cnorm)

        # threshold switch-off
        if job.freq_thresh is not None:
            freqs_vib_cm1 = gamma * vegeta.TOCM
            low = vegeta.np.where(freqs_vib_cm1 < float(job.freq_thresh))[0]
            if low.size > 0:
                nNOener[low] = 1
                nexc[low] = 0
                print(f"[modes] switched off {low.size} modes with freq < {job.freq_thresh} cm^-1")

        # cnorm output (Nimbus format)
        if job.cnorm_out.strip():
            cnorm_path = Path(job.cnorm_out).expanduser()
            if job.clean_cnorm:
                evals_out = vegeta.np.concatenate([ww[int(job.nrotrasl):], ww[:int(job.nrotrasl)]])
            else:
                evals_out = vegeta.np.concatenate([ww[ncart - nvib:], ww[:ncart - nvib]])
            vegeta.write_cnorm(cnorm_path, evals_out, cnorm)
            print(f"[cnorm] wrote: {cnorm_path}")

        v_au = vegeta.generate_initial_velocities(xm, x_bohr, gamma, cnorm, nexc, nNOener)

        # zero velocities for selected atoms (final output only)
        if job.zero_vel_atoms.strip():
            freeze_atoms = vegeta.expand_atom_tokens(_parse_tokens(job.zero_vel_atoms), nat)
            for a in freeze_atoms:
                i0 = 3 * (a - 1)
                v_au[i0:i0+3] = 0.0
            print(f"[atoms] forced v=0 for atoms: {freeze_atoms}")

        out_vel = Path(job.output).expanduser()
        vegeta.write_vel_xyz(out_vel, symb, v_au)
        print(f"[vel] wrote: {out_vel}")

        if job.gau_vel:
            gau_out = out_vel.with_name(out_vel.stem + "_gau.xyz")
            vegeta.convert_vel_file_to_bohr_s(out_vel, gau_out, precision=16)
            print(f"[vel] wrote (bohr/s): {gau_out}")

        freq_path = out_vel.with_suffix("").with_name("freq.dat")
        vegeta.write_freq_dat(freq_path, ww, out_vel.name, gamma_vib=gamma, nNOener=nNOener)
        print(f"[freq] wrote: {freq_path}")

        # mode movies
        if job.print_modes:
            freqs_cm1_all = vegeta.np.sqrt(vegeta.np.abs(ww)) * vegeta.TOCM
            freqs_cm1_vib = freqs_cm1_all[ncart - nvib:]
            cnorm_vib = cnorm[:, :nvib]
            vegeta.write_mode_xyz_files(
                out_vel, symb, x_ang, cnorm_vib, xm, freqs_cm1_vib,
                nframes=int(job.frames), ncycles=int(job.cycles)
            )
            print(f"[modes] wrote {nvib} mode movies (frames={job.frames}, cycles={job.cycles})")


# ---------------------------
# Main UI
# ---------------------------
class VegetaMainWindow(QtWidgets.QMainWindow):
    HELP: Dict[str, str] = {
        "workdir": "Working directory where output files are written.",
        "xyz": "Equilibrium XYZ geometry file (Å). nat is read from the first line.",
        "hess": "Flat Hessian file (lower triangle; first 2 lines ignored).",
        "nrotrasl": "Roto-translational DOF: 6 (non-linear) or 5 (linear).",
        "on": "Vibrational modes to excite (+1 quantum). Supports ranges: 1-5, 10..12, 20:22 and commas.",
        "off": "Vibrational modes to switch off (P=0). Supports ranges.",
        "freq_thresh": "Switch off all vibrational modes with harmonic freq below this threshold (cm^-1).",
        "clean": "Clean cnorm: force roto-trans eigenvalues to 0 and re-diagonalize vib subspace (Gram-Schmidt).",
        "zero_atoms": "Atom indices (1-based) to force to zero velocity in the final output.",
        "output": "Output velocity XYZ (a.u.).",
        "gau": "Also write velocities converted to bohr/s: <output_stem>_gau.xyz",
        "cnorm": "Write cnorm.dat (Flying Nimbus format) to this path (optional).",
        "print": "Write a multi-frame XYZ movie for each vibrational mode.",
        "frames": "Frames per mode movie (per cycle).",
        "cycles": "Number of oscillation cycles per mode movie.",
        "geo_only": "Geometry-only mode: write Center of Mass COM-shifted + principal-axes geometry and exit.",
        "pa_xyz": "Output filename for COM+PA geometry (optional).",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vegeta GUI")
        self.resize(1180, 840)

        self.worker: Optional[VegetaWorker] = None
        self.settings = QtCore.QSettings("Vegeta", "VegetaGUI")

        self._build_actions()
        self._build_ui()
        self._apply_theme(dark=True)
        self._restore_settings()
        self._refresh_nat_badge()
        self._update_preview()

    # ---- actions ----
    def _build_actions(self):
        self.act_run = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaPlay), "Run", self)
        self.act_stop = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MediaStop), "Stop", self)
        self.act_open_workdir = QtGui.QAction(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon), "Open workdir", self)
        self.act_toggle_dark = QtGui.QAction("Dark theme", self, checkable=True)
        self.act_toggle_dark.setChecked(True)

        self.act_show_log = QtGui.QAction("Show log", self, checkable=True)
        self.act_show_help = QtGui.QAction("Show help", self, checkable=True)
        self.act_show_preview = QtGui.QAction("Show preview", self, checkable=True)

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

    # ---- ui ----
    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()

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
        add_nav("Modes", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView))
        add_nav("Export", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DriveHDIcon))
        add_nav("About", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation))

        self.pages = QtWidgets.QStackedWidget()
        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)

        self.page_files = self._make_scroll_page()
        self.page_modes = self._make_scroll_page()
        self.page_export = self._make_scroll_page()
        self.page_about = self._make_scroll_page()

        for p in (self.page_files, self.page_modes, self.page_export, self.page_about):
            self.pages.addWidget(p)

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        # docks
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

        # pages
        self._build_page_files(self._page_layout(self.page_files))
        self._build_page_modes(self._page_layout(self.page_modes))
        self._build_page_export(self._page_layout(self.page_export))
        self._build_page_about(self._page_layout(self.page_about))

        # status
        self.status = self.statusBar()
        self.lbl_nat = QtWidgets.QLabel("nat: —")
        self.status.addPermanentWidget(self.lbl_nat)

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
        body = self.HELP.get(key, "No help available.")
        self.txt_help.setHtml(f"<h3>{title}</h3><p>{body}</p>")
        if not self.dock_help.isVisible():
            self.dock_help.setVisible(True)

    # ---- Files page ----
    def _build_page_files(self, lay: QtWidgets.QVBoxLayout):
        sec_runner = CollapsibleSection("Runner", expanded=True)
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.ed_workdir = QtWidgets.QLineEdit()
        self.btn_workdir = QtWidgets.QToolButton(text="…")
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
        self.ed_hess = QtWidgets.QLineEdit()
        for ed in (self.ed_xyz, self.ed_hess):
            ed.textChanged.connect(self._on_any_change)

        f2.addRow(*self._file_row(self._hlbl("Equilibrium XYZ", "xyz"), self.ed_xyz, self._browse_xyz))
        f2.addRow(*self._file_row(self._hlbl("Hessian (flat)", "hess"), self.ed_hess, self._browse_hess))
        sec_inputs.content_lay.addLayout(f2)
        lay.addWidget(sec_inputs)

        sec_geo = CollapsibleSection("Geometry (optional)", expanded=False)
        f3 = QtWidgets.QFormLayout()
        f3.setHorizontalSpacing(18)
        f3.setVerticalSpacing(10)

        self.cb_geo_only = QtWidgets.QCheckBox()
        self.cb_geo_only.toggled.connect(self._on_any_change)
        row_geo = QtWidgets.QHBoxLayout()
        row_geo.addWidget(self.cb_geo_only)
        row_geo.addWidget(self._hlbl("Geometry-only (COM+PA)", "geo_only"))
        row_geo.addStretch(1)
        f3.addRow(QtWidgets.QLabel(""), self._wrap(row_geo))

        self.ed_pa_xyz = QtWidgets.QLineEdit("")
        self.ed_pa_xyz.setPlaceholderText("optional output name, e.g. geo_pa.xyz")
        self.ed_pa_xyz.textChanged.connect(self._on_any_change)
        f3.addRow(self._hlbl("PA geometry output", "pa_xyz"), self.ed_pa_xyz)

        sec_geo.content_lay.addLayout(f3)
        lay.addWidget(sec_geo)

        lay.addStretch(1)

    def _file_row(self, label_widget: QtWidgets.QWidget, lineedit: QtWidgets.QLineEdit, browse_fn):
        btn = QtWidgets.QToolButton(text="…")
        btn.clicked.connect(browse_fn)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(lineedit, 1)
        row.addWidget(btn, 0)
        return label_widget, self._wrap(row)

    # ---- Modes page ----
    def _build_page_modes(self, lay: QtWidgets.QVBoxLayout):
        sec = CollapsibleSection("Modes & options", expanded=True)
        f = QtWidgets.QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(10)

        self.cb_nrt = QtWidgets.QComboBox()
        self.cb_nrt.addItems(["6", "5"])
        self.cb_nrt.currentTextChanged.connect(self._on_any_change)

        self.ed_on = QtWidgets.QLineEdit()
        self.ed_on.setPlaceholderText("e.g. 1 2 5-7 10..12")
        self.ed_on.textChanged.connect(self._on_any_change)

        self.ed_off = QtWidgets.QLineEdit()
        self.ed_off.setPlaceholderText("e.g. 1-3,8,20:22")
        self.ed_off.textChanged.connect(self._on_any_change)

        self.sp_thresh = QtWidgets.QDoubleSpinBox()
        self.sp_thresh.setRange(0.0, 1e6)
        self.sp_thresh.setDecimals(3)
        self.sp_thresh.setSpecialValueText("disabled")
        self.sp_thresh.setValue(0.0)
        self.sp_thresh.setKeyboardTracking(False)
        self.sp_thresh.valueChanged.connect(self._on_any_change)

        self.cb_clean = QtWidgets.QCheckBox()
        self.cb_clean.toggled.connect(self._on_any_change)
        row_clean = QtWidgets.QHBoxLayout()
        row_clean.addWidget(self.cb_clean)
        row_clean.addWidget(self._hlbl("Clean cnorm", "clean"))
        row_clean.addStretch(1)

        self.ed_zero_atoms = QtWidgets.QLineEdit()
        self.ed_zero_atoms.setPlaceholderText("e.g. 1 2 10-12")
        self.ed_zero_atoms.textChanged.connect(self._on_any_change)

        f.addRow(self._hlbl("nrotrasl", "nrotrasl"), self.cb_nrt)
        f.addRow(self._hlbl("--on", "on"), self.ed_on)
        f.addRow(self._hlbl("--off", "off"), self.ed_off)
        f.addRow(self._hlbl("freq threshold (cm^-1)", "freq_thresh"), self.sp_thresh)
        f.addRow(QtWidgets.QLabel(""), self._wrap(row_clean))
        f.addRow(self._hlbl("Zero-velocity atoms", "zero_atoms"), self.ed_zero_atoms)

        sec.content_lay.addLayout(f)
        lay.addWidget(sec)

        sec_print = CollapsibleSection("Normal modes movies", expanded=False)
        f2 = QtWidgets.QFormLayout()
        f2.setHorizontalSpacing(18)
        f2.setVerticalSpacing(10)

        self.cb_print = QtWidgets.QCheckBox()
        self.cb_print.toggled.connect(self._on_any_change)
        row_print = QtWidgets.QHBoxLayout()
        row_print.addWidget(self.cb_print)
        row_print.addWidget(self._hlbl("Write mode movies", "print"))
        row_print.addStretch(1)
        f2.addRow(QtWidgets.QLabel(""), self._wrap(row_print))

        self.sp_frames = QtWidgets.QSpinBox()
        self.sp_frames.setRange(1, 9999)
        self.sp_frames.setValue(21)
        self.sp_frames.setKeyboardTracking(False)
        self.sp_frames.valueChanged.connect(self._on_any_change)

        self.sp_cycles = QtWidgets.QSpinBox()
        self.sp_cycles.setRange(1, 999)
        self.sp_cycles.setValue(1)
        self.sp_cycles.setKeyboardTracking(False)
        self.sp_cycles.valueChanged.connect(self._on_any_change)

        f2.addRow(self._hlbl("frames", "frames"), self.sp_frames)
        f2.addRow(self._hlbl("cycles", "cycles"), self.sp_cycles)

        sec_print.content_lay.addLayout(f2)
        lay.addWidget(sec_print)

        lay.addStretch(1)

    # ---- Export page ----
    def _build_page_export(self, lay: QtWidgets.QVBoxLayout):
        sec = CollapsibleSection("Output", expanded=True)
        f = QtWidgets.QFormLayout()
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(10)

        self.ed_output = QtWidgets.QLineEdit("velocity.xyz")
        self.ed_output.textChanged.connect(self._on_any_change)
        f.addRow(self._hlbl("Velocity output", "output"), self.ed_output)

        self.cb_gau = QtWidgets.QCheckBox()
        self.cb_gau.toggled.connect(self._on_any_change)
        row_g = QtWidgets.QHBoxLayout()
        row_g.addWidget(self.cb_gau)
        row_g.addWidget(self._hlbl("Also write bohr/s", "gau"))
        row_g.addStretch(1)
        f.addRow(QtWidgets.QLabel(""), self._wrap(row_g))

        self.ed_cnorm_out = QtWidgets.QLineEdit("")
        self.ed_cnorm_out.setPlaceholderText("optional, e.g. cnorm.dat")
        self.ed_cnorm_out.textChanged.connect(self._on_any_change)
        f.addRow(self._hlbl("cnorm output", "cnorm"), self.ed_cnorm_out)

        sec.content_lay.addLayout(f)
        lay.addWidget(sec)
        lay.addStretch(1)

    # ---- About page ----
    def _build_page_about(self, lay: QtWidgets.QVBoxLayout):
        card = QtWidgets.QFrame()
        card.setObjectName("AboutCard")
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        title = QtWidgets.QLabel("Vegeta GUI")
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

    # ---- Run/Stop ----
    def _set_running(self, running: bool):
        self.act_run.setEnabled(not running)
        self.act_stop.setEnabled(running)
        self.sidebar.setEnabled(not running)

    def _run(self):
        if self.worker is not None and self.worker.isRunning():
            QtWidgets.QMessageBox.information(self, "Already running", "A run is already in progress.")
            return

        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        xyz = (self.ed_xyz.text() or "").strip()
        if not xyz or not Path(xyz).expanduser().is_file():
            self._err("Missing XYZ", "Please select an existing XYZ file.")
            return

        if not self.cb_geo_only.isChecked():
            hess = (self.ed_hess.text() or "").strip()
            if not hess or not Path(hess).expanduser().is_file():
                self._err("Missing Hessian", "Please select an existing Hessian file (required unless geo-only).")
                return

        job = VegetaJob(
            workdir=wd,
            xyz=xyz,
            hess=(self.ed_hess.text() or "").strip(),
            output=(self.ed_output.text() or "velocity.xyz").strip() or "velocity.xyz",
            nrotrasl=int(self.cb_nrt.currentText() or "6"),
            on_text=(self.ed_on.text() or "").strip(),
            off_text=(self.ed_off.text() or "").strip(),
            freq_thresh=(float(self.sp_thresh.value()) if float(self.sp_thresh.value()) > 0 else None),
            clean_cnorm=bool(self.cb_clean.isChecked()),
            cnorm_out=(self.ed_cnorm_out.text() or "").strip(),
            print_modes=bool(self.cb_print.isChecked()),
            frames=int(self.sp_frames.value()),
            cycles=int(self.sp_cycles.value()),
            gau_vel=bool(self.cb_gau.isChecked()),
            zero_vel_atoms=(self.ed_zero_atoms.text() or "").strip(),
            geo_only=bool(self.cb_geo_only.isChecked()),
            pa_xyz=(self.ed_pa_xyz.text() or "").strip(),
        )

        self.txt_log.clear()
        self.txt_log.appendPlainText(self.pseudo_command(job))
        self.txt_log.appendPlainText(f"\n[cwd: {job.workdir}]\n")

        self.worker = VegetaWorker(job, parent=self)
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

    def _err(self, title: str, msg: str):
        QtWidgets.QMessageBox.critical(self, title, msg)

    # ---- Preview ----
    def pseudo_command(self, job: Optional[VegetaJob] = None) -> str:
        if job is None:
            job = VegetaJob(
                workdir=Path((self.ed_workdir.text() or "").strip() or "."),
                xyz=(self.ed_xyz.text() or "").strip(),
                hess=(self.ed_hess.text() or "").strip(),
                output=(self.ed_output.text() or "velocity.xyz").strip(),
                nrotrasl=int(self.cb_nrt.currentText() or "6"),
                on_text=(self.ed_on.text() or "").strip(),
                off_text=(self.ed_off.text() or "").strip(),
                freq_thresh=(float(self.sp_thresh.value()) if float(self.sp_thresh.value()) > 0 else None),
                clean_cnorm=bool(self.cb_clean.isChecked()),
                cnorm_out=(self.ed_cnorm_out.text() or "").strip(),
                print_modes=bool(self.cb_print.isChecked()),
                frames=int(self.sp_frames.value()),
                cycles=int(self.sp_cycles.value()),
                gau_vel=bool(self.cb_gau.isChecked()),
                zero_vel_atoms=(self.ed_zero_atoms.text() or "").strip(),
                geo_only=bool(self.cb_geo_only.isChecked()),
                pa_xyz=(self.ed_pa_xyz.text() or "").strip(),
            )

        parts = ["python", "vegeta_V2.py", "--xyz", job.xyz]
        if job.geo_only:
            parts += ["--geo-only"]
        if job.pa_xyz:
            parts += ["--pa-xyz", job.pa_xyz]
        if (not job.geo_only) and job.hess:
            parts += ["-H", job.hess]
        parts += ["--nrotrasl", str(job.nrotrasl)]
        if job.on_text:
            parts += ["--on"] + job.on_text.split()
        if job.off_text:
            parts += ["--off"] + job.off_text.split()
        if job.freq_thresh is not None:
            parts += ["--freq-thresh", str(job.freq_thresh)]
        if job.clean_cnorm:
            parts += ["--clean-cnorm", "1"]
        if job.cnorm_out:
            parts += ["--cnorm-out", job.cnorm_out]
        if job.zero_vel_atoms:
            parts += ["--zero-vel-atoms"] + job.zero_vel_atoms.split()
        parts += ["-o", job.output]
        if job.gau_vel:
            parts += ["--gau-vel"]
        if job.print_modes:
            parts += ["--print", "1", "--frames", str(job.frames), "--cycles", str(job.cycles)]
        return " ".join(parts)

    def _refresh_nat_badge(self):
        nat = safe_read_nat_from_xyz(self.ed_xyz.text())
        self.lbl_nat.setText(f"nat: {nat}" if nat > 0 else "nat: —")

    def _update_preview(self):
        try:
            self.txt_preview.setPlainText(self.pseudo_command())
        except Exception:
            self.txt_preview.setPlainText("Preview unavailable:\n" + traceback.format_exc())

    def _on_any_change(self, *args):
        self._refresh_nat_badge()
        self._update_preview()
        self._save_settings()

    # ---- Browse ----
    def _browse_workdir(self):
        cur = (self.ed_workdir.text() or "").strip() or str(Path.cwd())
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Select working directory", cur)
        if p:
            self.ed_workdir.setText(p)

    def _browse_xyz(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select equilibrium XYZ", str(Path.cwd()), "XYZ (*.xyz);;All files (*)")
        if p:
            self.ed_xyz.setText(p)

    def _browse_hess(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Hessian file", str(Path.cwd()), "All files (*)")
        if p:
            self.ed_hess.setText(p)

    def _open_workdir(self):
        wd = Path((self.ed_workdir.text() or "").strip() or ".").expanduser()
        if wd.exists():
            open_in_file_manager(wd)

    # ---- Settings ----
    def _restore_settings(self):
        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        state = self.settings.value("windowState")
        if state is not None:
            self.restoreState(state)

        self.ed_workdir.setText(self.settings.value("workdir", str(Path.cwd())))
        self.ed_xyz.setText(self.settings.value("xyz", ""))
        self.ed_hess.setText(self.settings.value("hess", ""))
        self.ed_output.setText(self.settings.value("output", "velocity.xyz"))
        self.ed_on.setText(self.settings.value("on", ""))
        self.ed_off.setText(self.settings.value("off", ""))
        self.ed_zero_atoms.setText(self.settings.value("zero_atoms", ""))
        self.ed_cnorm_out.setText(self.settings.value("cnorm_out", ""))
        self.ed_pa_xyz.setText(self.settings.value("pa_xyz", ""))

        self.cb_nrt.setCurrentText(str(self.settings.value("nrotrasl", "6")))
        self.cb_clean.setChecked(bool(int(self.settings.value("clean", 0))))
        self.cb_gau.setChecked(bool(int(self.settings.value("gau", 0))))
        self.cb_print.setChecked(bool(int(self.settings.value("print", 0))))
        self.cb_geo_only.setChecked(bool(int(self.settings.value("geo_only", 0))))

        try:
            self.sp_thresh.setValue(float(self.settings.value("freq_thresh", 0.0)))
            self.sp_frames.setValue(int(self.settings.value("frames", 21)))
            self.sp_cycles.setValue(int(self.settings.value("cycles", 1)))
        except Exception:
            pass

    def _save_settings(self):
        self.settings.setValue("workdir", (self.ed_workdir.text() or "").strip())
        self.settings.setValue("xyz", (self.ed_xyz.text() or "").strip())
        self.settings.setValue("hess", (self.ed_hess.text() or "").strip())
        self.settings.setValue("output", (self.ed_output.text() or "").strip())
        self.settings.setValue("on", (self.ed_on.text() or "").strip())
        self.settings.setValue("off", (self.ed_off.text() or "").strip())
        self.settings.setValue("zero_atoms", (self.ed_zero_atoms.text() or "").strip())
        self.settings.setValue("cnorm_out", (self.ed_cnorm_out.text() or "").strip())
        self.settings.setValue("pa_xyz", (self.ed_pa_xyz.text() or "").strip())
        self.settings.setValue("nrotrasl", str(self.cb_nrt.currentText()))
        self.settings.setValue("clean", int(self.cb_clean.isChecked()))
        self.settings.setValue("gau", int(self.cb_gau.isChecked()))
        self.settings.setValue("print", int(self.cb_print.isChecked()))
        self.settings.setValue("geo_only", int(self.cb_geo_only.isChecked()))
        self.settings.setValue("freq_thresh", float(self.sp_thresh.value()))
        self.settings.setValue("frames", int(self.sp_frames.value()))
        self.settings.setValue("cycles", int(self.sp_cycles.value()))

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self._save_settings()
        super().closeEvent(event)

    # ---- Theme (Nimbus-style) ----
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
        QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox, QSpinBox, QDoubleSpinBox {
            background: #0f172a; border: 1px solid #1f2937; border-radius: 12px; padding: 8px;
        }
        QComboBox::drop-down { border: none; padding-right: 6px; }
        QDockWidget::title { background: #111827; padding: 8px; border: 1px solid #1f2937; }
        QScrollArea { border: none; }
        QFrame#AboutCard { background: #0f172a; border: 1px solid #1f2937; border-radius: 18px; }
        QToolButton:checked { background: #0f172a; }
        """
        self.setStyleSheet(qss_dark if dark else "")



def main():
    try:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    except Exception:
        pass

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("VegetaGUI")

    # IMPORTANT: prevent app from quitting when splash (the only window) closes
    app.setQuitOnLastWindowClosed(False)

    f = QtGui.QFont()
    f.setPointSize(10)
    app.setFont(f)

    splash_txt = (ASCII_BANNER or "").rstrip("\n")
    splash = AsciiSplash(splash_txt) if splash_txt.strip() else None

    win_holder = {"w": None}

    def launch_main():
        if win_holder["w"] is not None:
            return
        w = VegetaMainWindow()
        win_holder["w"] = w
        w.show()
        try:
            w.raise_()
            w.activateWindow()
        except Exception:
            pass
        # now normal behavior: closing main window quits
        app.setQuitOnLastWindowClosed(True)

    if splash is not None:
        splash.splashClosed.connect(launch_main)
        splash.show()
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

