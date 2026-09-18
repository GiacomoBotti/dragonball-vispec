# Welcome to DragonBall!

Dragonball is a Python Suite created to guide the user in the simulation of quasi-classical trajectory (QCT) spectra.
You can find a description of the method capabilites [here](https://doi.org/10.1063/5.0297591) and [here](https://doi.org/10.1039/D3CP01216F).

The suite contains three different scripts, both in CLI and GUI version:
- **Flying Nimbus** (aka Flying $\nu_{i}$mbus) to compute the spectra
- **Bulma** to generate the input and parse the outputs of the supported *ab initio* codes (Gaussian, Orca and QChem)
- **Vegeta** to generate the initial conditions for the quasi-classical trajectory

You can find the individual documentation here:
- [Flying Nimbus](docs/source/README_FlyingNimbus.md)
- [Bulma](docs/source/Readme_BULMA.md)
- [Vegeta](docs/source/Readme_VEGETA.md)

You can find the guides on how to use Dragonball with the supported _ab initio_ codes here:
- [Gaussian](docs/source/Gau_tutorial/GAU_tutorial.md)
- [Orca](docs/source/ORCA_tutorial.md)
- [QChem](docs/source/QChem_tutorial.md)

You can find the full documentation [here](https://dragonball-vispec.readthedocs.io/en/latest/)

## Classical Spectra Flowchart

![Dragonball Workflow](docs/source/workflow.png)

## Project ChiChi

Project ChiChi (aka $\langle \chi \vert \chi \rangle$) aims at preparing Dragonball to semiclassical dynamics. It contains three additional scripts:
- [Hessian Database](docs/source/README_hd.md)
- [PrepPY](docs/source/README_preppy.md)
- [CandyBeam](docs/source/README_CandyBeam.md)
and two compatible codes:
- [Frieza](https://github.com/GiacomoBotti/Heller_dynamics)
- [Runner](https://github.com/GiacomoBotti/BOMD_RUNNER)
You can find more information on Project ChiChi in the [archive](link-to-archive).

Have fun!

G.M. & G.B.
