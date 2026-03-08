from collections import namedtuple
from pathlib import Path
import openvsp as vsp
import numpy as np
from fluids.atmosphere import ATMOSPHERE_1976

vsp.InitGUI()
vsp.StartGUI()

vsp_file = Path('./wing_assignment.vsp3')
aero_path = Path('~/Downloads/OpenVSP-3.46.0-win64').expanduser()

vsp.VSPCheckSetup()  # Verify everything is working as expected
vsp.VSPRenew()  # Clear all global state

vsp.ClearVSPModel()
vsp.Update()

vsp.SetVSPAEROPath(str(aero_path))

# read vsp3 input file
vsp.ReadVSPFile(str(vsp_file))
vsp.Update()

def setup_analysis() -> str:
    vsp.DeleteAllResults()
    analysis_name = "VSPAEROComputeGeometry"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.PrintAnalysisInputs(analysis_name)
    vsp.ExecAnalysis(analysis_name)

    analysis_name = "VSPAEROSweep"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.SetDoubleAnalysisInput(analysis_name, "AlphaEnd", (float(15),), 0)
    vsp.Update()
    vsp.PrintAnalysisInputs(analysis_name)
    return analysis_name

analysis_name = setup_analysis()
vsp.ExecAnalysis(analysis_name)
n_pts = vsp.GetIntAnalysisInput(analysis_name, "AlphaNpts")

def grab_output(result_name, var, alpha_steps):
    return [vsp.GetDoubleResults(vsp.FindResultsID(result_name, x), var, 0)[-1] for x in range(0, alpha_steps[0])]

name = "VSPAERO_History"
history_res = vsp.FindResultsID(name, 2)

alphas = grab_output(name, "Alpha", n_pts)
CL = grab_output(name, "CLtot", n_pts)
CD = grab_output(name, "CDtot", n_pts)

CLs = {"CL": CL}
CDs = {"CL": CD}

SimSettings = namedtuple('Range', ['start', 'end', 'num', 'type'])

settings = {
    "NumWakeNodes": SimSettings(start=4, end=20, num=4, type=int),
    "WakeNumIter": SimSettings(start=2, end=20, num=4, type=int),
}

matcher = {
    'set': {
        int: vsp.SetIntAnalysisInput,
        float: vsp.SetDoubleAnalysisInput,
        str: vsp.SetStringAnalysisInput,
    },
    'get': {
        int: vsp.GetIntAnalysisInput,
        float: vsp.GetDoubleAnalysisInput,
        str: vsp.GetStringAnalysisInput,
    }
}


import matplotlib.pyplot as plt

for setting_name, setting in settings.items():

    # Save the default value of the parameter to reset it after the loop
    get_parameter_function = matcher['get'][setting.type]
    parameter_default = get_parameter_function(analysis_name, setting_name)

    for value in np.linspace(setting.start, setting.end, setting.num, dtype=setting.type):
        setup_analysis()

        set_parameter_function = matcher['set'][setting.type]
        set_parameter_function(analysis_name, setting_name, (setting.type(value),))
        vsp.Update()
        vsp.ExecAnalysis(analysis_name)

        CL_i = grab_output(name, "CLtot", n_pts)
        CD_i = grab_output(name, "CDtot", n_pts)

        plt.plot(alphas, CL_i, label=f"CL_{setting_name}_{str(value)}")
        plt.plot(alphas, CD_i, label=f"CD_{setting_name}_{str(value)}")

    # Reset the parameter to its default value
    set_parameter_function = matcher['set'][setting.type]
    set_parameter_function(analysis_name, setting_name, parameter_default, 0)

    plt.plot(alphas, CL, label="CL")
    plt.plot(alphas, CD, label="CD")
    plt.xlabel("Alpha (deg)")
    plt.ylabel("Coefficient")
    plt.title("CL and CD vs Alpha")
    plt.legend()
    plt.grid()
    plt.show()