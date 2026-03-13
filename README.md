## Aircraft Design assignments

This repository contains the assignments for the Aircraft Design course. Each assignment is organized in a separate folder, and includes the necessary files and instructions to execute the code

### Assignment 1: Aerodynamic Analysis in OpenVSP

To replicate the results of Assignment 1, follow these steps:
* Install OpenVSP from the official website: https://openvsp.org/download.php
* Install Anaconda / Miniconda, for example on modern Windows systems with `winget install Anaconda.Anaconda3`
* Add it to path (if not done automatically), activate for PowerShell `conda init powershell`
* From the OpenVSP directory, navigate to `python` folder and execute `./setup.ps`
* This will install all the necessary dependencies, then, with `vsppytools` env activated, go to the `assignment_1` folder and run `pip install -r requirements.txt` to install the required Python packages
* Finally, run the jupyter notebook `assignment_1.ipynb` through `jupyter notebook` command in the terminal from the assignment folder.