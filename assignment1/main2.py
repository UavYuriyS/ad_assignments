from pathlib import Path

from matplotlib import pyplot as plt

from assignment1.utils.vsp_manager import VspManager, AnalysisSettings

to_get = ['Alpha', 'CLtot', 'CDtot', 'CLwtot', 'CDwtot']

vsp_file = Path('wing_assignment.vsp3')
aero_path = Path('~/Downloads/OpenVSP-3.48.1-win64').expanduser()
manager = VspManager(aero_path, vsp_file)

analysis_name = "VSPAEROSweep"

manager.setup_analysis()

#_as = AnalysisSettings(geom="WingGeom", analysis=analysis_name, name="WakeNumIter", start=2, end=10, num=3)
_as = AnalysisSettings(geom="WingGeom", analysis=analysis_name, name="SectTess_U", start=10, end=100, num=3)


data = manager.sweep_analysis(_as, to_get)

for k,v in data.items():
    alphas = v.pop('Alpha')
    for label, data in v.items():
        plt.plot(alphas, data, label=f"{k}_{label}")
plt.xlabel("Alpha (deg)")
plt.ylabel("Coefficient")
plt.title("CL and CD vs Alpha")
plt.legend()
plt.grid()
plt.show()

data = manager.perform_analysis(analysis_name, to_get)

alphas = data.pop('Alpha')

for label, data in data.items():
    plt.plot(alphas, data, label=label)

plt.xlabel("Alpha (deg)")
plt.ylabel("Coefficient")
plt.title("CL and CD vs Alpha")
plt.legend()
plt.grid()
plt.show()

print(data)