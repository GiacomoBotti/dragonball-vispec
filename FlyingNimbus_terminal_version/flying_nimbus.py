#!/usr/bin/env python3

#SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#Authors: Giacomo Mandelli, Giacomo Botti

"""
Expected formats:
- Geometry (xyz): standard XYZ (nat, comment, nat atom lines). Optionally a 5th
  column per atom can provide the atomic mass (au). Otherwise masses are taken
  from an internal database.
- Hessian: lower-triangle values after TWO header lines (any text)
- Trajectory: extended XYZ frames with x y z vx vy vz on each atom line.
OUTPUT
- Correlations:  <root>_cpp_mode_X.dat, <root>_cqq_mode_X.dat (if not --ta)
- Spectra:       <root>_FT-cpp_mode_X.dat / <root>_FT-cqq_mode_X.dat
                 <root>_TA-cpp_mode_X.dat / <root>_TA-cqq_mode_X.dat (if --ta)
- Cartesian: <root>_cvv_cartesian.dat / <root>_FT-cvv_cartesian.dat
                  <root>_TA-cvv_cartesian.dat
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np

nimbus_art = f"""
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

"""

nimbus_banner = r"""
                             On the
 
           ███████╗██╗     ██╗   ██╗██╗███╗   ██╗ ██████╗
           ██╔════╝██║     ╚██╗ ██╔╝██║████╗  ██║██╔════╝
           █████╗  ██║      ╚████╔╝ ██║██╔██╗ ██║██║  ███╗
           ██╔══╝  ██║       ╚██╔╝  ██║██║╚██╗██║██║   ██║
           ██║     ███████╗   ██║   ██║██║ ╚████║╚██████╔╝
           ╚═╝     ╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝

           ██╗  ██╗   ███╗   ███╗██████╗ ██╗   ██╗███████╗
           ██║  ██║   ████╗ ████║██╔══██╗██║   ██║██╔════╝
           ██║  ██║   ██╔████╔██║██████╔╝██║   ██║███████╗
           ██║ ██╔╝   ██║╚██╔╝██║██╔══██╗██║   ██║╚════██║
           ████╔═╝▀▀  ██║ ╚═╝ ██║██████╔╝╚██████╔╝███████║
           ╚═══╝  ██╗ ╚═╝     ╚═╝╚═════╝  ╚═════╝ ╚══════╝
                  ██║
                  ╚═╝
"""


# ----------------------------
# Constants 
# ----------------------------

BOHR_RADIUS = 0.52917721067
HA2CMM1 = 219474.625
HA2K = 315775.1293573255
PI = math.pi
HA2EV = 27.2114
TOAUTIME = 4.1341e4
TOAUVEL = 1.0
CNORM = True


# ----------------------------
# Utilities
# ----------------------------

_FLOAT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[dDeE][+-]?\d+)?$")


def _to_float(tok: str) -> float:
    """Parse Fortran-like floats (supports D exponent, commas)."""
    t = tok.strip().strip(",")
    t = t.replace("D", "E").replace("d", "e")
    return float(t)


def _is_numeric_line(line: str) -> bool:
    toks = re.split(r"\s+", line.strip().replace(",", " "))
    for tok in toks:
        if not tok:
            continue
        if _FLOAT_RE.match(tok.replace("D", "E").replace("d", "e")):
            return True
    return False

def read_nat_from_xyz(xyz_path: str | Path) -> int:
    """Read nat (number of atoms) from the first line of an XYZ file."""
    p = Path(xyz_path)
    if not p.exists():
        raise FileNotFoundError(f"XYZ file not found: {p}")
    lines = p.read_text().splitlines()
    if not lines:
        raise ValueError(f"XYZ file is empty: {p}")
    nat = int(lines[0].split()[0])
    if nat <= 0:
        raise ValueError(f"Invalid nat={nat} read from XYZ file {p!s}")
    return nat

# ----------------------------
# Input
# ----------------------------

@dataclass
class Config:
    # system
    nat: int
    nrototrasl: int

    # time/correlation
    nstart: int
    ncorr: int
    nbeads: int
    nbeadsstep: int
    dt: float  # already in atomic units

    # spectrum grid (cm^-1)
    init_wnumb: float
    spec_res: float
    wnumb_span: float

    # switches
    ta: bool
    coord: str  # 'nm' or 'cart'

    # damping
    alpha_pow: float
    alpha_dip: float

    # mode selection (1-based vibrational indices)
    modes: List[int]

    # atom selection (1-based atom indices). Empty = all atoms
    atoms: List[int]

    # files
    zmat_filename: str
    hess_filename: str
    traj_filename: str

    # cnorm control
    readcnorm: int  # 0 -> compute from Hessian (and write cnorm.dat), 1 -> read cnorm.dat
    cnorm_path: str

    # output
    root_out_filename: str

    # plotting
    plot: bool = False              # save spectra plots as PNG
    plot_dir: str = "."             # directory to write PNGs
    plot_dpi: int = 200             # PNG resolution
    plot_logy: bool = False         # log-scale y axis
    plot_show: bool = False         # try to display plots interactively
    # excel-friendly output (CSV)
    excel: bool = False             # also write CSV tables (Excel compatible)
    excel_sep: str = ","            # delimiter (',' ';' or '\t' / 'tab')
    excel_merge: bool = False       # write one merged CSV per spectrum type (columns = selected)
    # spectrum post-processing
    freq_offset: float = 0.0       # shift output wavenumber axis by this offset (cm^-1)
    norm1: bool = False            # normalize each printed spectrum so its max peak is 1
    rm_cnorm: bool = False   # if writing cnorm.dat and it exists, delete it first




# ----------------------------
# Masses + CNORM/Hessian
# ----------------------------

_MASS_DB = {
    "H": 1837.15,
    "D": 3671.48,
    "O": 29156.96,
    "Od": 32810.46,
    "C": 21874.66,
    "N": 25526.06,
    "Ti": 87256.20,
    "F": 34631.97,
    "S": 58281.54,
    "I": 231332.70,
}


def get_masses_from_xyz(zmat_filename: str | Path, nat: int) -> Tuple[List[str], np.ndarray]:
    p = Path(zmat_filename)
    if not p.exists():
        raise FileNotFoundError(f"Geometry/xyz file not found: {p}")
    lines = p.read_text().splitlines()
    if len(lines) < nat + 2:
        raise ValueError(f"XYZ file {p} has too few lines for nat={nat}")

    symbols: List[str] = []
    amass: List[float] = []

    for i in range(nat):
        parts = lines[i + 2].split()
        if not parts:
            raise ValueError(f"Blank atom line at atom {i+1} in {p}")
        sym = parts[0]
        symbols.append(sym)

        m: Optional[float] = None
        if CNORM and len(parts) >= 5:
            try:
                m = _to_float(parts[4])
            except Exception:
                m = None

        if m is None:
            if sym not in _MASS_DB:
                raise KeyError(
                    f"Element '{sym}' not in mass database. "
                    "Add it to _MASS_DB or provide mass as 5th column in your input xyz file."
                )
            amass.append(float(_MASS_DB[sym]))
        else:
            amass.append(float(m))

    xm = np.repeat(np.array(amass, dtype=float), 3)
    return symbols, xm


def read_hessian_nwchem_lower_triangle(hess_filename: str | Path, ncart: int) -> np.ndarray:
    """after two header lines, read lower triangle values."""
    p = Path(hess_filename)
    if not p.exists():
        raise FileNotFoundError(f"Hessian file not found: {p}")

    with p.open("r") as f:
        _ = f.readline()
        _ = f.readline()
        vals: List[float] = []
        for line in f:
            for tok in line.replace(",", " ").split():
                try:
                    vals.append(_to_float(tok))
                except Exception:
                    pass

    expected = ncart * (ncart + 1) // 2
    if len(vals) < expected:
        raise ValueError(f"Not enough Hessian numbers. Expected {expected}, got {len(vals)}")
    vals = vals[:expected]

    h = np.zeros((ncart, ncart), dtype=float)
    k = 0
    for i in range(ncart):
        for j in range(i + 1):
            h[i, j] = vals[k]
            h[j, i] = vals[k]
            k += 1
    return h


def mass_weight_hessian(hess: np.ndarray, xm: np.ndarray) -> np.ndarray:
    m = xm.astype(float)
    denom = np.sqrt(np.outer(m, m))
    return hess / denom


def reorder_modes_rottrans_at_end(evals: np.ndarray, evecs: np.ndarray, nvib: int) -> Tuple[np.ndarray, np.ndarray]:
    ncart = evals.shape[0]
    idx_vib = np.arange(ncart - nvib, ncart)
    idx_rt = np.arange(0, ncart - nvib)
    idx = np.concatenate([idx_vib, idx_rt])
    return evals[idx], evecs[:, idx]


def write_cnorm_file(path: str | Path, evals: np.ndarray, cnorm: np.ndarray) -> None:
    p = Path(path)
    ncart = cnorm.shape[0]
    if CNORM:
        gammaall = np.sqrt(np.abs(evals))
        with p.open("w") as f:
            f.write("#\n")
            f.write("# Scaled Hessian eigenvectors (au) (rot and trasl at end):\n")
            f.write("#\n")
            for i in range(ncart):
                f.write(" ".join(f"{cnorm[j, i]:21.14e}" for j in range(ncart)) + "\n")
            f.write("\n\n")
            f.write("# sqrt(|eigenvalues|) of scaled Hessian (au) (rot and trasl at end):\n")
            f.write(" ".join(f"{gammaall[i]:21.14e}" for i in range(ncart)) + "\n")
            f.write("\n\n")
            f.write("# eigenvalues of scaled Hessian (au) (rot and trasl at end):\n")
            f.write(" ".join(f"{evals[i]:21.14e}" for i in range(ncart)) + "\n")
    else:
        with p.open("w") as f:
            f.write("\n#Hessian eigenvectors (au):\n\n")
            for i in range(ncart):
                f.write(" ".join(f"{cnorm[i, j]:20.10g}" for j in range(ncart)) + "\n")
            f.write("#Hessian eigenvalues (au):\n")
            f.write(" ".join(f"{evals[i]:20.10g}" for i in range(ncart)) + "\n")


def read_cnorm_file(nat: int, nrototrasl: int, cnorm_path: str | Path) -> Tuple[np.ndarray, np.ndarray]:
    p = Path(cnorm_path)
    if not p.exists():
        raise FileNotFoundError(f"cnorm file not found: {p}")

    ncart = 3 * nat

    lines = p.read_text().splitlines()

    if CNORM:
        cnorm = np.zeros((ncart, ncart), dtype=float)
        start = None
        for i, line in enumerate(lines):
            toks = line.split()
            if len(toks) >= ncart and all(_FLOAT_RE.match(t.replace("D", "E").replace("d", "e")) for t in toks[:ncart]):
                start = i
                break
        if start is None:
            raise ValueError("Could not locate cnorm eigenvector block in cnorm.dat")

        for col in range(ncart):
            toks = lines[start + col].split()
            cnorm[:, col] = np.array([_to_float(t) for t in toks[:ncart]], dtype=float)

        ww = None
        for i in range(len(lines) - 1, -1, -1):
            toks = lines[i].split()
            if len(toks) >= ncart and all(_FLOAT_RE.match(t.replace("D", "E").replace("d", "e")) for t in toks[:ncart]):
                ww = np.array([_to_float(t) for t in toks[:ncart]], dtype=float)
                break
        if ww is None:
            raise ValueError("Could not locate eigenvalues line in cnorm.dat")

        deltaq = np.sqrt(np.abs(ww))
        return cnorm, deltaq

    # fallback (skw)
    float_lines = [ln for ln in lines if _is_numeric_line(ln)]
    if len(float_lines) < ncart + 1:
        raise ValueError("cnorm.dat (skw) seems too short")
    cnorm = np.zeros((ncart, ncart), dtype=float)
    for i in range(ncart):
        toks = float_lines[i].split()
        cnorm[i, :] = np.array([_to_float(t) for t in toks[:ncart]], dtype=float)
    ww = np.array([_to_float(t) for t in float_lines[ncart].split()[:ncart]], dtype=float)
    deltaq = np.sqrt(np.abs(ww))
    return cnorm, deltaq


def compute_cnorm_from_hessian(
    nat: int,
    nrototrasl: int,
    hess_filename: str | Path,
    xm: np.ndarray,
    write_cnorm: bool,
    cnorm_path: str | Path,
    rm_existing: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    ncart = 3 * nat
    nvib = ncart - nrototrasl

    hess = read_hessian_nwchem_lower_triangle(hess_filename, ncart=ncart)
    hmw = mass_weight_hessian(hess, xm)

    evals, evecs = np.linalg.eigh(hmw)
    evals2, evecs2 = reorder_modes_rottrans_at_end(evals, evecs, nvib=nvib)

    deltaq = np.sqrt(np.abs(evals2))
    cnorm = evecs2

    if write_cnorm:
        cnorm_p = Path(cnorm_path)
        if cnorm_p.exists():
            if rm_existing and cnorm_p.is_file():
                cnorm_p.unlink()
            else:
                raise FileExistsError(f"{cnorm_p} already exists; will not overwrite")
        write_cnorm_file(cnorm_p, evals2, cnorm)
    return cnorm, deltaq


# ----------------------------
# Trajectory reading
# ----------------------------


def count_md_steps_xyz(traj_filename: str | Path, nat: int) -> int:
    p = Path(traj_filename)
    with p.open("r") as f:
        nstep = 0
        while True:
            line = f.readline()
            if not line:
                break
            line2 = f.readline()
            if not line2:
                break
            for _ in range(nat):
                if not f.readline():
                    return nstep
            nstep += 1
        return nstep


def read_traj_nwchem(traj_filename: str | Path, nat: int) -> Tuple[np.ndarray, np.ndarray]:
    p = Path(traj_filename)
    if not p.exists():
        raise FileNotFoundError(f"Trajectory file not found: {p}")

    NT = count_md_steps_xyz(p, nat=nat)
    if NT <= 0:
        raise ValueError(f"No MD steps detected in {p}")

    x = np.zeros((NT, 3 * nat), dtype=float)
    v = np.zeros((NT, 3 * nat), dtype=float)

    with p.open("r") as f:
        for step in range(NT):
            _ = f.readline()  # nat
            _ = f.readline()  # comment
            for i in range(nat):
                parts = f.readline().split()
                if len(parts) < 7:
                    raise ValueError(f"Malformed atom line at step {step+1}, atom {i+1} (need x y z vx vy vz)")
                xx = np.array([_to_float(parts[1]), _to_float(parts[2]), _to_float(parts[3])], dtype=float)
                vv = np.array([_to_float(parts[4]), _to_float(parts[5]), _to_float(parts[6])], dtype=float)
                x[step, 3 * i : 3 * i + 3] = xx
                v[step, 3 * i : 3 * i + 3] = vv

    # positions are in Angstrom -> convert to bohr
    x /= BOHR_RADIUS
    v *= TOAUVEL
    return x, v


# ---------------------------
# Normal-mode projection
# ----------------------------


def format_atom_selection(atoms_1based: Sequence[int]) -> str:
    """Format a sorted list like [1,2,3,5,8,9] -> '1-3_5_8-9' for filenames."""
    if not atoms_1based:
        return ""
    nums = list(atoms_1based)
    ranges = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
        start = prev = n
    ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
    return "_".join(ranges)


def atom_cart_mask(nat: int, atoms0: Sequence[int]) -> np.ndarray:
    """Return a length-3N 0/1 mask selecting given 0-based atom indices."""
    mask = np.zeros(3 * nat, dtype=float)
    for a in atoms0:
        i = 3 * a
        mask[i:i+3] = 1.0
    return mask


def atom_cart_cols(atoms0: Sequence[int]) -> List[int]:
    """Return column indices [3*a,3*a+1,3*a+2,...] for selected 0-based atoms."""
    cols: List[int] = []
    for a in atoms0:
        cols.extend([3*a, 3*a+1, 3*a+2])
    return cols


def project_to_modes(series: np.ndarray, cnorm: np.ndarray, xm: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Project a (NT x 3N) Cartesian series to normal modes.

    If mask is provided (length 3N, 0/1), only those Cartesian DOFs contribute.
    """
    mw = series * np.sqrt(xm)[None, :]
    if mask is not None:
        mw = mw * mask[None, :]
    return mw @ cnorm


# ----------------------------
# Correlation + FT
# ----------------------------


def simpson_weights(n: int, dt: float) -> np.ndarray:
    w = np.ones(n, dtype=float)
    if n >= 2:
        for j in range(1, n - 1):
            jf = j + 1  # 1-based
            w[j] = 4.0 if (jf % 2 == 0) else 2.0
    return w * (dt / 3.0)


def ft_simpson(
    data: np.ndarray,
    dt: float,
    init_wnumb_cm1: float,
    spec_res_cm1: float,
    nf: int,
    block: int = 256,
) -> np.ndarray:
    ncorr, nseries = data.shape
    df = spec_res_cm1 / HA2CMM1
    w0 = init_wnumb_cm1 / HA2CMM1

    t = np.arange(ncorr, dtype=float) * dt
    w_sim = simpson_weights(ncorr, dt)
    dat_w = data * w_sim[:, None]

    out = np.zeros((nf, nseries), dtype=np.complex128)
    for start in range(0, nf, block):
        end = min(nf, start + block)
        idx = np.arange(start, end, dtype=float)
        omega = w0 + idx * df
        E = np.exp(1j * omega[:, None] * t[None, :])
        out[start:end, :] = (E @ dat_w) / PI
    return out


def corr_nm(
    p: np.ndarray,
    modes: Sequence[int],
    ncorr: int,
    dt: float,
    init_wnumb: float,
    spec_res: float,
    nf: int,
    nbeads: int,
    nbeadsstep: int,
    alpha: float,
) -> Tuple[np.ndarray, np.ndarray]:
    NT, _nvib = p.shape
    modes0 = [m - 1 for m in modes]
    nmode = len(modes0)

    if nbeads <= 0:
        nbeads = NT - (ncorr - 1)
    nbeads = max(1, min(nbeads, NT - (ncorr - 1)))
    origins = np.arange(0, nbeads, nbeadsstep, dtype=int)

    denom = (float(nbeads) / float(nbeadsstep)) - 1.0
    if denom <= 0:
        denom = float(len(origins))

    C = np.zeros((ncorr, nmode), dtype=float)

    for lag in range(ncorr):
        o2 = origins + lag
        valid = o2 < NT
        o = origins[valid]
        o2 = o2[valid]
        if o.size == 0:
            break
        prod = p[o2[:, None], modes0] * p[o[:, None], modes0]
        C[lag, :] = prod.sum(axis=0) / denom
        if alpha != 0.0:
            C[lag, :] *= math.exp(-alpha * ((lag + 1) * dt) ** 2)

    IFF = ft_simpson(C, dt, init_wnumb, spec_res, nf)
    PWS = np.abs(np.real(IFF))
    return C, PWS


def corr_ta_nm(
    p: np.ndarray,
    modes: Sequence[int],
    ncorr: int,
    dt: float,
    init_wnumb: float,
    spec_res: float,
    nf: int,
) -> np.ndarray:
    modes0 = [m - 1 for m in modes]
    if p.shape[0] < ncorr:
        raise ValueError(f"Not enough time points for ncorr={ncorr}")

    Pvec = p[:ncorr, :][:, modes0].copy()
    IFF = ft_simpson(Pvec, dt, init_wnumb, spec_res, nf)
    PWS = (np.abs(IFF) ** 2) / (2.0 * (ncorr - 1) * dt)
    return PWS


def corr_cart(
    v: np.ndarray,
    nat: int,
    ncorr: int,
    dt: float,
    init_wnumb: float,
    spec_res: float,
    nf: int,
    nbeads: int,
    nbeadsstep: int,
    atoms: Sequence[int] | None = None,  # 0-based atom indices
) -> Tuple[np.ndarray, np.ndarray]:
    NT, ncart = v.shape
    if ncart != 3 * nat:
        raise ValueError("v has wrong number of columns")

    if atoms is not None and len(atoms) > 0:
        atoms = sorted(set(int(a) for a in atoms))
        if atoms[0] < 0 or atoms[-1] >= nat:
            raise ValueError("atoms selection out of range for nat")
    else:
        atoms = None

    if nbeads <= 0:
        nbeads = NT - (ncorr - 1)
    nbeads = max(1, min(nbeads, NT - (ncorr - 1)))
    origins = np.arange(0, nbeads, nbeadsstep, dtype=int)

    denom = (float(nbeads) / float(nbeadsstep)) - 1.0
    if denom <= 0:
        denom = float(len(origins))

    C = np.zeros((ncorr, 1), dtype=float)
    vv = v.reshape(NT, nat, 3)
    if atoms is not None:
        vv = vv[:, atoms, :]

    for lag in range(ncorr):
        o2 = origins + lag
        valid = o2 < NT
        o = origins[valid]
        o2 = o2[valid]
        if o.size == 0:
            break
        dots = (vv[o2] * vv[o]).sum(axis=2).mean(axis=1)
        C[lag, 0] = dots.sum() / denom

    IFF = ft_simpson(C, dt, init_wnumb, spec_res, nf)
    PWS = np.abs(np.real(IFF))
    return C[:, 0], PWS[:, 0:1]


def corr_cart_ta(
    v: np.ndarray,
    nat: int,
    ncorr: int,
    dt: float,
    init_wnumb: float,
    spec_res: float,
    nf: int,
    atoms: Sequence[int] | None = None,  # 0-based atom indices
) -> np.ndarray:
    if v.shape[0] < ncorr:
        raise ValueError(f"Not enough time points for ncorr={ncorr}")
    if v.shape[1] != 3 * nat:
        raise ValueError("v has wrong number of columns")

    if atoms is not None and len(atoms) > 0:
        atoms = sorted(set(int(a) for a in atoms))
        if atoms[0] < 0 or atoms[-1] >= nat:
            raise ValueError("atoms selection out of range for nat")
        cols = atom_cart_cols(atoms)
        Vvec = v[:ncorr, cols].copy()
    else:
        Vvec = v[:ncorr, :].copy()

    IFF = ft_simpson(Vvec, dt, init_wnumb, spec_res, nf)
    PWS1 = (np.abs(IFF) ** 2).sum(axis=1) / (2.0 * (ncorr - 1) * dt)
    return PWS1.reshape(-1, 1)


# ----------------------------
# Output writers
# ----------------------------


def write_cvv(out_filename: str | Path, dt: float, cvv: np.ndarray) -> None:
    p = Path(out_filename)
    with p.open("w") as f:
        for i, val in enumerate(cvv):
            f.write(f"{i*dt: .12e} {val: .12e}\n")


def write_ft_nm(
    out_filename: str | Path,
    deltaq: np.ndarray,
    cnorm: np.ndarray,
    init_wnumb: float,
    spec_res: float,
    pws: np.ndarray,
    imode: int,
    nvib: int,
) -> None:
    ncart = cnorm.shape[0]
    nf = pws.shape[0]

    zpe = float(np.sum(0.5 * deltaq[:nvib]))

    p = Path(out_filename)
    with p.open("w") as f:
        f.write("#\n")
        f.write("# Normal mode vectors:          Hartree          eV          cm-1\n")
        for i in range(nvib):
            f.write(
                f"# mode({i+1:2d})                    {deltaq[i]: .9e}   {deltaq[i]*HA2EV:8.6f}   {deltaq[i]*HA2CMM1:7.2f}\n"
            )
            nrt = ncart - nvib
            for j in range(nrt):
                f.write(f"# ({j+1:2d})     {cnorm[j, i]: .9e}\n")
            for j in range(nvib):
                f.write(f"# ({j+1+nrt:2d})     {cnorm[j+nrt, i]: .9e}\n")
            f.write("#\n")
        f.write(f"# zpe=                         {zpe: .9e}   {zpe*HA2EV:8.6f}   {zpe*HA2CMM1:7.2f}\n")
        f.write("#\n")

        for i in range(nf):
            wn = init_wnumb + i * spec_res
            f.write(f"{wn: .6f} {pws[i, imode]: .12e}\n")


def write_ft_cart(
    out_filename: str | Path,
    deltaq: np.ndarray,
    init_wnumb: float,
    spec_res: float,
    pws: np.ndarray,
    nvib: int,
) -> None:
    nf = pws.shape[0]
    zpe = float(np.sum(0.5 * deltaq[:nvib]))

    p = Path(out_filename)
    with p.open("w") as f:
        f.write("#\n")
        f.write(f"# zpe=                         {zpe: .9e}   {zpe*HA2EV:8.6f}   {zpe*HA2CMM1:7.2f}\n")
        f.write("#\n")
        for i in range(nf):
            wn = init_wnumb + i * spec_res
            f.write(f"{wn: .6f} {pws[i, 0]: .12e}\n")



# ----------------------------
# Plotting helpers
# ----------------------------
def _csv_delim(sep: str) -> str:
    """common separators."""
    if sep.lower() in ("\t", "tab", "tsv"):
        return "\t"
    return sep


def write_xy_csv(
    out_filename: str | Path,
    x: "np.ndarray",
    y: "np.ndarray",
    header: tuple[str, str],
    sep: str = ",",
) -> None:
    """Write two numeric columns to a CSV/TSV file (Excel-friendly)."""
    p = Path(out_filename)
    d = _csv_delim(sep)
    with p.open("w", newline="") as f:
        w = csv.writer(f, delimiter=d)
        w.writerow([header[0], header[1]])
        for xi, yi in zip(x, y):
            w.writerow([f"{float(xi):.12g}", f"{float(yi):.12e}"])


def write_matrix_csv(
    out_filename: str | Path,
    x: "np.ndarray",
    Y: "np.ndarray",
    colnames: list[str],
    xname: str,
    sep: str = ",",
) -> None:
    """Write x + multiple columns (nf x ncol) to CSV/TSV."""
    if Y.ndim != 2 or Y.shape[0] != x.shape[0]:
        raise ValueError("Y must be 2D with same first dimension as x")
    p = Path(out_filename)
    d = _csv_delim(sep)
    with p.open("w", newline="") as f:
        w = csv.writer(f, delimiter=d)
        w.writerow([xname] + colnames)
        for ii in range(x.shape[0]):
            row = [f"{float(x[ii]):.6f}"] + [f"{float(v):.12e}" for v in Y[ii, :]]
            w.writerow(row)


def wavenumber_axis(init_wnumb: float, spec_res: float, nf: int) -> np.ndarray:
    return init_wnumb + spec_res * np.arange(nf, dtype=float)

def _normalize_max1(y: np.ndarray) -> np.ndarray:
    """Return y scaled so that max(y)=1 (safe for max<=0)."""
    ymax = float(np.max(y)) if y.size else 0.0
    if ymax > 0.0:
        return y / ymax
    return y

def normalize_columns_max1(Y: np.ndarray) -> np.ndarray:
    """Normalize each column of Y to max=1."""
    if Y.ndim != 2:
        raise ValueError("Y must be 2D")
    Yout = Y.copy()
    for j in range(Yout.shape[1]):
        Yout[:, j] = _normalize_max1(Yout[:, j])
    return Yout

def save_spectrum_png(
    out_png: str | Path,
    wn: np.ndarray,
    intensity: np.ndarray,
    title: str,
    logy: bool = False,
    dpi: int = 200,
    show: bool = False,
) -> None:
    """Save a simple spectrum plot (wavenumber vs intensity) to PNG."""
    # Import so the script works without matplotlib unless plotting is requested.
    import matplotlib
    if not show:
        matplotlib.use("Agg")  # safe default for clusters 
    import matplotlib.pyplot as plt

    p = Path(out_png)
    p.parent.mkdir(parents=True, exist_ok=True)

    plt.figure()
    plt.plot(wn, intensity)
    plt.xlabel(r"Frequency (cm$^{-1}$)")
    plt.ylabel("Intensity (arb. units)")
    plt.title(title)
    if logy:
        plt.yscale("log")
    ax = plt.gca()
    ax.tick_params(axis="y", labelleft=False, left=False)
    plt.tight_layout()
    plt.savefig(p, dpi=dpi)
    if show:
        # This will only work if the environment has a display backend.
        try:
            plt.show()
        except Exception:
            pass
    plt.close()


def maybe_save_spectrum_plot(cfg: "Config", dat_filename: str | Path, wn: np.ndarray, intensity: np.ndarray) -> None:
    """If enabled, save a PNG plot next to the computed spectrum."""
    if not (getattr(cfg, "plot", False) or getattr(cfg, "plot_show", False)):
        return
    datp = Path(dat_filename)
    out_png = Path(getattr(cfg, "plot_dir", ".")) / datp.name
    out_png = out_png.with_suffix(".png")
    save_spectrum_png(
        out_png,
        wn,
        intensity,
        title=datp.stem,
        logy=bool(getattr(cfg, "plot_logy", False)),
        dpi=int(getattr(cfg, "plot_dpi", 200)),
        show=bool(getattr(cfg, "plot_show", False)),
    )
    if getattr(cfg, "plot", False):
        print(f"Saved spectrum plot: {out_png}")


# ----------------------------
# Main
# ----------------------------


def run(cfg: Config) -> None:
    nat = cfg.nat
    ncart = 3 * nat
    nvib = ncart - cfg.nrototrasl
    cnorm_path = (cfg.cnorm_path or "").strip() or "cnorm.dat"

    if cfg.coord not in ("nm", "cart"):
        raise ValueError("--coord must be 'nm' or 'cart'")

    # masses
    _, xm = get_masses_from_xyz(cfg.zmat_filename, nat)

    # cnorm + deltaq
    if cfg.readcnorm == 0:
        cnorm, deltaq = compute_cnorm_from_hessian(
                nat=nat,
                nrototrasl=cfg.nrototrasl,
                hess_filename=cfg.hess_filename,
                xm=xm,
                write_cnorm=True,
                cnorm_path=cnorm_path,
                rm_existing=cfg.rm_cnorm,
                )

    elif cfg.readcnorm == 1:
        cnorm, deltaq = read_cnorm_file(nat=nat, nrototrasl=cfg.nrototrasl, cnorm_path=cnorm_path)
    else:
        raise ValueError("--readcnorm must be 0 (from Hessian) or 1 (from cnorm.dat)")

    # report frequencies (exclude rot/trans)
    print("Frequencies excluding rot and trans (cm^-1):")
    for i in range(nvib):
        print(f"  omega({i+1:3d}) = {deltaq[i]*HA2CMM1:15.6f}")
    print()

    # read trajectory
    x, v = read_traj_nwchem(cfg.traj_filename, nat=nat)
    NT = x.shape[0]

    # apply NSTART
    start0 = cfg.nstart - 1
    if start0 < 0 or start0 >= NT:
        raise ValueError(f"--nstart={cfg.nstart} is out of range for NT={NT}")

    x_copy = x[start0:, :]
    v_copy = v[start0:, :]


    # atom selection (1-based indices)
    atoms_sel = sorted(set(int(a) for a in cfg.atoms)) if cfg.atoms else []
    if atoms_sel:
        for a in atoms_sel:
            if a < 1 or a > nat:
                raise ValueError(f"--atoms contains out-of-range atom index {a} (valid 1..{nat})")
        # treat "all atoms explicitly listed" as no selection
        if len(atoms_sel) == nat:
            atoms_sel = []

    atoms0: Sequence[int] | None = [a - 1 for a in atoms_sel] if atoms_sel else None
    cart_mask = atom_cart_mask(nat, atoms0) if atoms0 is not None else None
    sel_tag = f"_atoms_{format_atom_selection(atoms_sel)}" if atoms_sel else ""

    if x_copy.shape[0] < cfg.ncorr:
        raise ValueError(f"Not enough post-nstart steps for ncorr={cfg.ncorr}")

    nf = int(cfg.wnumb_span / cfg.spec_res)
    if nf <= 0:
        raise ValueError("NF computed <= 0; check --wnumb-span/--spec-res")


    #do_plot = bool(cfg.plot) or bool(cfg.plot_show)
    #wn_axis = wavenumber_axis(cfg.init_wnumb, cfg.spec_res, nf) if do_plot else None
    do_plot = bool(cfg.plot) or bool(cfg.plot_show)
    do_excel = bool(getattr(cfg, "excel", False))
    do_merge = bool(getattr(cfg, "excel_merge", False))
    wn_axis = wavenumber_axis(cfg.init_wnumb + cfg.freq_offset, cfg.spec_res, nf) if (do_plot or do_excel or do_merge) else None

    # mode list sanity
    if cfg.coord == "nm":
        if not cfg.modes:
            raise ValueError("--modes is required when --coord nm")
        for m in cfg.modes:
            if m < 1 or m > nvib:
                raise ValueError(f"Mode {m} is out of range (1..{nvib})")

    # compute
    if cfg.coord == "nm":
        p_all = project_to_modes(v_copy, cnorm, xm, mask=cart_mask)
        q_all = project_to_modes(x_copy, cnorm, xm, mask=cart_mask)
        p = p_all[:, :nvib]
        q = q_all[:, :nvib]

        if not cfg.ta:
            Cpp, PWS_p = corr_nm(
                p,
                modes=cfg.modes,
                ncorr=cfg.ncorr,
                dt=cfg.dt,
                init_wnumb=cfg.init_wnumb,
                spec_res=cfg.spec_res,
                nf=nf,
                nbeads=cfg.nbeads,
                nbeadsstep=cfg.nbeadsstep,
                alpha=cfg.alpha_pow,
            )
            Cqq, PWS_q = corr_nm(
                q,
                modes=cfg.modes,
                ncorr=cfg.ncorr,
                dt=cfg.dt,
                init_wnumb=cfg.init_wnumb,
                spec_res=cfg.spec_res,
                nf=nf,
                nbeads=cfg.nbeads,
                nbeadsstep=cfg.nbeadsstep,
                alpha=cfg.alpha_dip,
            )
            if cfg.norm1:
                PWS_p = normalize_columns_max1(PWS_p)
                PWS_q = normalize_columns_max1(PWS_q)

            for mi, mode in enumerate(cfg.modes):
                write_cvv(f"{cfg.root_out_filename}{sel_tag}_cpp_mode_{mode}.dat", cfg.dt, Cpp[:, mi])
                if do_excel:
                    t = np.arange(Cpp.shape[0], dtype=float) * cfg.dt
                    write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_cpp_mode_{mode}.csv", t, Cpp[:, mi], ("t_au", "cpp"), sep=cfg.excel_sep)
                write_ft_nm(
                    f"{cfg.root_out_filename}{sel_tag}_FT-cpp_mode_{mode}.dat",
                    deltaq,
                    cnorm,
                    cfg.init_wnumb + cfg.freq_offset,
                    cfg.spec_res,
                    PWS_p,
                    mi,
                    nvib,
                )
                  
                if do_excel:
                    write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_FT-cpp_mode_{mode}.csv", wn_axis, PWS_p[:, mi], ("wn_cm-1", "intensity"), sep=cfg.excel_sep)
                if do_plot:
                    maybe_save_spectrum_plot(cfg, f"{cfg.root_out_filename}{sel_tag}_FT-cpp_mode_{mode}.dat", wn_axis, PWS_p[:, mi])

            for mi, mode in enumerate(cfg.modes):
                write_cvv(f"{cfg.root_out_filename}{sel_tag}_cqq_mode_{mode}.dat", cfg.dt, Cqq[:, mi])
                if do_excel:
                    t = np.arange(Cqq.shape[0], dtype=float) * cfg.dt
                    write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_cqq_mode_{mode}.csv", t, Cqq[:, mi], ("t_au", "cqq"), sep=cfg.excel_sep)

                write_ft_nm(
                    f"{cfg.root_out_filename}{sel_tag}_FT-cqq_mode_{mode}.dat",
                    deltaq,
                    cnorm,
                    cfg.init_wnumb + cfg.freq_offset,
                    cfg.spec_res,
                    PWS_q,
                    mi,
                    nvib,
                )
                if do_excel:
                    write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_FT-cqq_mode_{mode}.csv", wn_axis, PWS_q[:, mi], ("wn_cm-1", "intensity"), sep=cfg.excel_sep)
                if do_plot:
                    maybe_save_spectrum_plot(cfg, f"{cfg.root_out_filename}{sel_tag}_FT-cqq_mode_{mode}.dat", wn_axis, PWS_q[:, mi])

        else:
            PWS_p = corr_ta_nm(
                p,
                modes=cfg.modes,
                ncorr=cfg.ncorr,
                dt=cfg.dt,
                init_wnumb=cfg.init_wnumb,
                spec_res=cfg.spec_res,
                nf=nf,
            )
            PWS_q = corr_ta_nm(
                q,
                modes=cfg.modes,
                ncorr=cfg.ncorr,
                dt=cfg.dt,
                init_wnumb=cfg.init_wnumb,
                spec_res=cfg.spec_res,
                nf=nf,
            )
            if cfg.norm1:
                PWS_p = normalize_columns_max1(PWS_p)
                PWS_q = normalize_columns_max1(PWS_q)

            for mi, mode in enumerate(cfg.modes):
                write_ft_nm(
                    f"{cfg.root_out_filename}{sel_tag}_TA-cpp_mode_{mode}.dat",
                    deltaq,
                    cnorm,
                    cfg.init_wnumb + cfg.freq_offset,
                    cfg.spec_res,
                    PWS_p,
                    mi,
                    nvib,
                )
                if do_excel:
                    write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_TA-cpp_mode_{mode}.csv", wn_axis, PWS_p[:, mi], ("wn_cm-1", "intensity"), sep=cfg.excel_sep)
                if do_plot:
                    maybe_save_spectrum_plot(cfg, f"{cfg.root_out_filename}{sel_tag}_TA-cpp_mode_{mode}.dat", wn_axis, PWS_p[:, mi])

            for mi, mode in enumerate(cfg.modes):
                write_ft_nm(
                    f"{cfg.root_out_filename}{sel_tag}_TA-cqq_mode_{mode}.dat",
                    deltaq,
                    cnorm,
                    cfg.init_wnumb + cfg.freq_offset,
                    cfg.spec_res,
                    PWS_q,
                    mi,
                    nvib,
                )
                if do_excel:
                    write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_TA-cqq_mode_{mode}.csv", wn_axis, PWS_q[:, mi], ("wn_cm-1", "intensity"), sep=cfg.excel_sep)
                if do_plot:
                    maybe_save_spectrum_plot(cfg, f"{cfg.root_out_filename}{sel_tag}_TA-cqq_mode_{mode}.dat", wn_axis, PWS_q[:, mi])
                
        # Optional: one merged CSV per spectrum type (columns = selected modes)
        if do_merge and wn_axis is not None:
            modes_tag = "_".join(str(m) for m in cfg.modes)
            if cfg.ta:
                write_matrix_csv(
                        f"{cfg.root_out_filename}{sel_tag}_TA-cpp_modes_{modes_tag}.csv",
                        wn_axis,
                        PWS_p,
                        [f"mode_{m}" for m in cfg.modes],
                        "wn_cm-1",
                        sep=cfg.excel_sep,
                        )
                write_matrix_csv(
                        f"{cfg.root_out_filename}{sel_tag}_TA-cqq_modes_{modes_tag}.csv",
                        wn_axis,
                        PWS_q,
                        [f"mode_{m}" for m in cfg.modes],
                        "wn_cm-1",
                        sep=cfg.excel_sep,
                        )
            else:
                write_matrix_csv(
                        f"{cfg.root_out_filename}{sel_tag}_FT-cpp_modes_{modes_tag}.csv",
                        wn_axis,
                        PWS_p,
                        [f"mode_{m}" for m in cfg.modes],
                        "wn_cm-1",
                        sep=cfg.excel_sep,
                        )
                write_matrix_csv(
                        f"{cfg.root_out_filename}{sel_tag}_FT-cqq_modes_{modes_tag}.csv",
                        wn_axis,
                        PWS_q,
                        [f"mode_{m}" for m in cfg.modes],
                        "wn_cm-1",
                        sep=cfg.excel_sep,
                        )              
    else:
        # cartesian
        if not cfg.ta:
            cvv, pws = corr_cart(
                v_copy,
                nat=nat,
                ncorr=cfg.ncorr,
                dt=cfg.dt,
                init_wnumb=cfg.init_wnumb,
                spec_res=cfg.spec_res,
                nf=nf,
                nbeads=cfg.nbeads,
                nbeadsstep=cfg.nbeadsstep,
                atoms=atoms0,
            )
            if cfg.norm1:
                pws = pws.copy()
                pws[:, 0] = _normalize_max1(pws[:, 0])

            write_cvv(f"{cfg.root_out_filename}{sel_tag}_cvv_cartesian.dat", cfg.dt, cvv)
            if do_excel:
                t = np.arange(cvv.shape[0], dtype=float) * cfg.dt
                write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_cvv_cartesian.csv", t, cvv, ("t_au", "cvv"), sep=cfg.excel_sep)

            write_ft_cart(
                f"{cfg.root_out_filename}{sel_tag}_FT-cvv_cartesian.dat",
                deltaq,
                cfg.init_wnumb + cfg.freq_offset,
                cfg.spec_res,
                pws,
                nvib,
            )
            if do_excel:
                write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_FT-cvv_cartesian.csv", wn_axis, pws[:, 0], ("wn_cm-1", "intensity"), sep=cfg.excel_sep)
            if do_plot:
                maybe_save_spectrum_plot(cfg, f"{cfg.root_out_filename}{sel_tag}_FT-cvv_cartesian.dat", wn_axis, pws[:, 0])
        else:
            pws = corr_cart_ta(
                v_copy,
                nat=nat,
                ncorr=cfg.ncorr,
                dt=cfg.dt,
                init_wnumb=cfg.init_wnumb,
                spec_res=cfg.spec_res,
                nf=nf,
                atoms=atoms0,
            )
            if cfg.norm1:
                pws = pws.copy()
                pws[:, 0] = _normalize_max1(pws[:, 0])

            write_ft_cart(
                f"{cfg.root_out_filename}{sel_tag}_TA-cvv_cartesian.dat",
                deltaq,
                cfg.init_wnumb + cfg.freq_offset,
                cfg.spec_res,
                pws,
                nvib,
            )
            if do_excel:
                write_xy_csv(f"{cfg.root_out_filename}{sel_tag}_TA-cvv_cartesian.csv", wn_axis, pws[:, 0], ("wn_cm-1", "intensity"), sep=cfg.excel_sep)
            if do_plot:
                maybe_save_spectrum_plot(cfg, f"{cfg.root_out_filename}{sel_tag}_TA-cvv_cartesian.dat", wn_axis, pws[:, 0])


# ----------------------------


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
            description="time-averaged (TA) FT / spectra. PLEASE CITE:",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument("-N", "--nat", type=int, default=0, help="Number of atoms (0 = read from --xyz)")
    ap.add_argument("--nrototrasl", type=int, default=6, help="Number of rot+trans modes (usually 6, or 5 for linear)")

    ap.add_argument("--nstart", type=int, default=1, help="""First MD step to use (1-based)""")
    ap.add_argument("--ncorr", type=int, default=2500, help="Length of correlation window")
    ap.add_argument("--nbeads", type=int, default=0, help="Number of time origins (0 = auto)")
    ap.add_argument("--nbeadsstep", type=int, default=1, help="Stride between time origins")

    ap.add_argument("--dt", type=float, default=8.2682749151502, help="Time step in atomic units")

    ap.add_argument("--init-wnumb", type=float, default=0, help="Initial wavenumber (cm^-1)")
    ap.add_argument("--spec-res", type=float, default=1, help="Spectral resolution (cm^-1)")
    ap.add_argument("--wnumb-span", type=float, default=5000, help="Total wavenumber span (cm^-1)")

    # coord default: nm; ta on default =)
    ap.add_argument("--coord", choices=["nm", "cart"], default="nm", help="Work in normal modes (nm) or cartesian (cart)")
    ap.add_argument("--no-ta", dest="ta", action="store_false", help="Disable time-averaged spectrum (use correlation+FT)")
    ap.set_defaults(ta=True)

    ap.add_argument("--alpha-pow", type=float, default=0.0, help="Gaussian damping for cpp correlation")
    ap.add_argument("--alpha-dip", type=float, default=1e-8, help="Gaussian damping for cqq correlation")

    ap.add_argument(
        "--modes",
        nargs="+",
        type=int,
        default=None,
        help="Mode indices to process (1-based vibrational indices). Required with nm option (default)",
    )

    ap.add_argument(
        "--atoms",
        nargs="+",
        type=int,
        default=None,
        help="Subset of atoms (1-based indices) to include in the spectrum. Default: all atoms.",
    )

    ap.add_argument("--plot", action="store_true", help="Save spectra plots as PNG")
    ap.add_argument("--plot-dir", default=".", help="Directory to write PNG plots")
    ap.add_argument("--plot-dpi", type=int, default=200, help="PNG resolution (DPI)")
    #ap.add_argument("--plot-logy", action="store_true", help="Use log scale on y axis in plots")
    #ap.add_argument("--plot-show", action="store_true", help="Try to display plots interactively (may fail on clusters)")
    ap.add_argument("--excel", action="store_true", help="Also write Excel-friendly CSV/TSV tables (no comment lines)")
    ap.add_argument("--excel-sep", default=",", help="Delimiter for CSV output (use ';' or 'tab' if your Excel locale prefers it)")
    ap.add_argument("--excel-merge", action="store_true", help="Also write one merged CSV per spectrum type (columns = selected modes)")


    ap.add_argument("--xyz", dest="zmat_filename", required=True, help="Equilibrium geometry XYZ (also used for masses)")
    ap.add_argument("--hess", dest="hess_filename", required=False, help="Hessian file (lower triangle), required unless --readcnorm 1")
    ap.add_argument("--traj", dest="traj_filename", required=True, help="Trajectory file (extended XYZ with velocities)")

    ap.add_argument("--readcnorm", type=int, choices=[0, 1], default=0, help="0: compute cnorm from Hessian; 1: read cnorm.dat")
    ap.add_argument("--cnorm", dest="cnorm_path", default="cnorm.dat", help="Path to cnorm.dat")

    ap.add_argument("-o", "--output", dest="root_out_filename", default="QCT_", help="Root output prefix")
    ap.add_argument("--freq-offset", type=float, default=0.0, help="Shift output wavenumber axis by this offset (cm^-1)")
    ap.add_argument("--norm1", action="store_true", help="Normalize each printed spectrum so its maximum peak is 1")
    ap.add_argument("--rm-cnorm", dest="rm_cnorm", action="store_true", help="If writing cnorm.dat and it exists, delete it first")


    return ap


def main() -> None:
    ap = build_argparser()
    args = ap.parse_args()
    nat = int(getattr(args, "nat", 0) or 0)
    if nat <= 0:
        nat = read_nat_from_xyz(args.zmat_filename)
    cnorm_path = (getattr(args, "cnorm_path", "") or "").strip() or "cnorm.dat"

    if args.coord == "nm" and not args.modes:
        ap.error("--modes is required when --coord nm")
    if args.readcnorm == 0 and not args.hess_filename:
        ap.error("--hess is required when --readcnorm 0 (Hessian -> cnorm). Use --readcnorm 1 to read cnorm.dat and omit --hess.")

    cfg = Config(
        nat=nat,
        #cnorm_path = (cfg.cnorm_path or "").strip() or "cnorm.dat"
        nrototrasl=args.nrototrasl,
        nstart=args.nstart,
        ncorr=args.ncorr,
        nbeads=args.nbeads,
        nbeadsstep=args.nbeadsstep,
        dt=args.dt,
        init_wnumb=args.init_wnumb,
        spec_res=args.spec_res,
        wnumb_span=args.wnumb_span,
        ta=bool(args.ta),
        coord=args.coord,
        alpha_pow=args.alpha_pow,
        alpha_dip=args.alpha_dip,
        #nmode=(len(args.modes) if args.modes else 0),
        modes=list(args.modes) if args.modes else [],
        atoms=list(args.atoms) if args.atoms else [],
        zmat_filename=args.zmat_filename,
        hess_filename=args.hess_filename,
        traj_filename=args.traj_filename,
        readcnorm=args.readcnorm,
        cnorm_path=cnorm_path,
        root_out_filename=args.root_out_filename,
        plot=bool(args.plot),
        plot_dir=str(args.plot_dir),
        plot_dpi=int(args.plot_dpi),
        #plot_logy=bool(args.plot_logy),
        #plot_show=bool(args.plot_show),
        excel=bool(args.excel),
        excel_sep=str(args.excel_sep),
        excel_merge=bool(args.excel_merge),
        freq_offset=float(args.freq_offset),
        norm1=bool(args.norm1),
        rm_cnorm=bool(args.rm_cnorm),
    )

    print(nimbus_banner)
    print(nimbus_art)
   
    run(cfg)


if __name__ == "__main__":
    main()
