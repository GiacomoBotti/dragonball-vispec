# GUI Installation guide

This is the step-by-step installation guide for the DRAGONBALL suite GUIs.

## Prerequisites

The GUIs require specific python packages, so we suggest to create a new environment. To do so, make sure to deactivate any previous environment and to have `venv` installed:
```
sudo apt install python3.8-venv
```
Then, create a new environment:
```
python3 -m venv <environment path>
```
The source it:
```
source <environment path>/bin/activate
```
At this point, install `pip`:
```
python -m pip install -U pip
```
and install the packages listed in `requirements.txt` (that you can find in the repository)
```
python -m pip install -r requirements.txt
```
The file `requirements.txt` holds the list of packages with the best version. In case you get a `No matching` error for a certain package, just remove `==xx.yy.zz` after the package name in `requirements.txt` and try again. This may give compatibility issue, so it's always best to use `requirements.txt` as is. 

With this, all the prerequisites are successfully included in the `<environment name>` environment.

## Installation

To install the GUI, make sure you are in the environment in which you installed the prerequisites:
```
source <environment path>/bin/activate
```
Terminal should appear as
```
(<environment name>) user@machine:
```
Find the GUI source file (`_gui.py`). Make sure that you have the "core" python script in the same folder. Run
```
python <GUI script>_gui.py
```
Enjoy!

## Troubleshooting

We list here some issue we encountered during the installation of the GUIs on our machines. Every machine is different, so you may encounter these same errors, or many others!

### No `libxcb-cursor0`

In this case, just install it:
```
sudo apt install libxcb-cursor0
```

