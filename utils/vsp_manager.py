import random
import string
from collections import namedtuple
from pathlib import Path

import numpy as np
from openvsp import vsp

AnalysisSettings = namedtuple('AnalysisSettings', ['geom', 'analysis', 'name', 'start', 'end', 'num'])

class VspManager:

    _type_matcher = {
        vsp.INVALID_TYPE: None,
        vsp.BOOL_DATA: bool,
        vsp.INT_DATA: int,
        vsp.DOUBLE_DATA: float,
        vsp.STRING_DATA: str
        # Never met those yet
        # vsp.VEC3D_DATA:
        # vsp.INT_MATRIX_DATA = _vsp.INT_MATRIX_DATA
        # vsp.DOUBLE_MATRIX_DATA = _vsp.DOUBLE_MATRIX_DATA
        # vsp.ATTR_COLLECTION_DATA = _vsp.ATTR_COLLECTION_DATA
        # vsp.PARM_REFERENCE_DATA = _vsp.PARM_REFERENCE_DATA
    }

    _result_getter_matcher = {
        float: vsp.GetDoubleResults,
        int: vsp.GetIntResults,
        str: vsp.GetStringResults,
    }

    _input_getter_matcher = {
        float: vsp.GetDoubleAnalysisInput,
        int: vsp.GetIntAnalysisInput,
        str: vsp.GetStringAnalysisInput,
    }

    _input_setter_matcher = {
        float: vsp.SetDoubleAnalysisInput,
        int: vsp.SetIntAnalysisInput,
        str: vsp.SetStringAnalysisInput,
    }

    file: Path
    path: Path

    def get_result(self, _id, name) -> float | int | str:
        res_type = vsp.GetResultsType(_id, name)
        fun = self._result_getter_matcher[self._type_matcher[res_type]]
        return fun(_id, name)


    def __init__(self, vsp_path: Path, vsp_file: Path):
        vsp.VSPCheckSetup()  # Verify everything is working as expected
        vsp.VSPRenew()  # Clear all global state
        vsp.ClearVSPModel()
        vsp.Update()
        vsp.SetVSP3FileName(str(vsp_file))
        vsp.SetVSPAEROPath(str(vsp_path))
        # read vsp3 input file
        vsp.ReadVSPFile(str(vsp_file))
        vsp.Update()
        self.file = vsp_file
        self.path = vsp_path

    def setup_analysis(self) -> str:
        print("SETUP 1")
        vsp.DeleteAllResults()
        analysis_name = "VSPAEROComputeGeometry"
        vsp.SetAnalysisInputDefaults(analysis_name)
        vsp.PrintAnalysisInputs(analysis_name)
        vsp.ExecAnalysis(analysis_name)
        print("SETUP 2")
        analysis_name = "VSPAEROSweep"
        vsp.SetAnalysisInputDefaults(analysis_name)
        vsp.SetDoubleAnalysisInput(analysis_name, "AlphaEnd", (float(15),), 0)
        vsp.PrintAnalysisInputs(analysis_name)
        #vsp.ComputeCFDMesh(vsp.SET_ALL, vsp.SET_NONE, vsp.CFD_VSPGEOM_TYPE)
        vsp.Update()
        return analysis_name

    def perform_analysis(self, analysis: str, data_to_get: list[str]) -> dict[str, list[float | int | str]]:
        vsp.ExecAnalysis(analysis)
        return {
            data: self.fetch_last_results(analysis, data) for data in data_to_get
        }

    def set_simulation_setting(self, setting: AnalysisSettings, value: float | int | str):
        all_parms = [vsp.GetParmName(x) for x in vsp.GetGeomParmIDs(vsp.FindGeomsWithName(setting.geom)[0])]
        all_inputs = vsp.GetAnalysisInputNames(setting.analysis)

        # Setting parms
        if setting.name in all_parms:
            print("Setting Parm")
            if setting.name == 'SectTess_U':
                xsec_surf = vsp.GetXSecSurf(vsp.FindGeomsWithName(setting.geom)[0], 1)
                # IDK why there are two sections even though there is only one in the GUI
                # The first one is default?
                xsec = vsp.GetXSec(xsec_surf, 1)
                sec_tess_u = vsp.GetXSecParm(xsec, 'SectTess_U')
                vsp.SetParmValUpdate(sec_tess_u, value)
            else:
                res_parm: str
                for parm_id in vsp.GetGeomParmIDs(vsp.FindGeomsWithName(setting.geom)[0]):
                    if vsp.GetParmName(parm_id) == setting.name:
                        vsp.SetParmValUpdate(parm_id, value)
                        break

            vsp.Update()

            vsp.WriteVSPFile(str(self.file))
            vsp.ClearVSPModel()
            vsp.VSPCheckSetup()  # Verify everything is working as expected
            vsp.VSPRenew()  # Clear all global state
            vsp.ClearVSPModel()
            vsp.Update()
            vsp.SetVSPAEROPath(str(self.path))
            # read vsp3 input file
            vsp.ReadVSPFile(str(self.file))
            self.setup_analysis()
            vsp.ExportFile(str(self.file.parent / (self.file.stem + ".vspgeom")), vsp.SET_ALL, vsp.EXPORT_VSPGEOM)
            vsp.Update()

            self.setup_analysis()
        # Setting inputs
        elif setting.name in all_inputs:
            print("Setting Input")
            _type = self._type_matcher[vsp.GetAnalysisInputType(setting.analysis, setting.name)]
            fun = self._input_setter_matcher[_type]
            fun(setting.analysis, setting.name, (_type(value), ), 0)
        vsp.UpdateGeom(setting.geom)
        vsp.Update()

    def get_simulation_setting(self, setting: AnalysisSettings) -> float | int | str:
        all_parms = [vsp.GetParmName(x) for x in vsp.GetGeomParmIDs(vsp.FindGeomsWithName(setting.geom)[0])]
        all_inputs = vsp.GetAnalysisInputNames(setting.analysis)
        res = None
        # Setting parms
        if setting.name in all_parms:
            print("Getting Parm")
            if setting.name == 'SectTess_U':
                xsec_surf = vsp.GetXSecSurf(vsp.FindGeomsWithName(setting.geom)[0], 1)
                # IDK why there are two sections even though there is only one in the GUI
                # The first one is default?
                # Also, all IDs are the same if I use 0 up there and 1 here, but the result is different
                # What the f?
                xsec = vsp.GetXSec(xsec_surf, 1)
                sec_tess_u = vsp.GetXSecParm(xsec, 'SectTess_U')
                res = vsp.GetParmVal(sec_tess_u)
            else:
                res_parm: str
                for parm_id in vsp.GetGeomParmIDs(vsp.FindGeomsWithName(setting.geom)[0]):
                    if vsp.GetParmName(parm_id) == setting.name:
                        res = vsp.GetParmVal(parm_id)
                        break

        # Setting inputs
        elif setting.name in all_inputs:
            print("Getting Input")
            fun = self._input_getter_matcher[
                self._type_matcher[vsp.GetAnalysisInputType(setting.analysis, setting.name)]]
            res = fun(setting.analysis, setting.name)
        return res

    def sweep_analysis(self, settings: AnalysisSettings, data_to_get: list[str]) -> dict[str, dict[str, list[float | int | str]]]:
        self.setup_analysis()

        values = {}

        default_val = self.get_simulation_setting(settings)

        for value in np.linspace(settings.start, settings.end, settings.num):
            self.setup_analysis()
            self.set_simulation_setting(settings, value)
            res = self.perform_analysis(settings.analysis, data_to_get)
            values[f"{settings.name}_{value}"] = res

        self.set_simulation_setting(settings, default_val)
        vsp.DeleteAllResults()
        return values

    def grid_analysis(self, settings: tuple[AnalysisSettings, AnalysisSettings]) -> dict[str, list[list[float | int | str]]]:
        raise NotImplementedError("Can not perform grid analysis yet")

    def fetch_last_results(self, analysis: str, name: str) -> list[float | int | str]:
        n_pts = vsp.GetIntAnalysisInput(analysis, "AlphaNpts")[0]
        return [self.get_result(vsp.FindResultsID("VSPAERO_History", x), name)[-1] for x in range(0, n_pts)]