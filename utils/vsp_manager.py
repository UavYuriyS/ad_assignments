import os
import random
import string
from collections import namedtuple
from pathlib import Path
from typing import Optional

import numpy as np
from openvsp import vsp

AnalysisSettings = namedtuple('AnalysisSettings', ['geom', 'analysis', 'name', 'start', 'end', 'num'], defaults=[None, None, None])

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

    thin_value = vsp.SET_ALL
    thick_value = vsp.SET_NONE

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
        self.setup_analysis()



    def setup_analysis(self) -> str:
        vsp.DeleteAllResults()
        analysis_name = "VSPAEROComputeGeometry"
        vsp.SetAnalysisInputDefaults(analysis_name)
        #vsp.PrintAnalysisInputs(analysis_name)
        vsp.ExecAnalysis(analysis_name)
        analysis_name = "VSPAEROSweep"
        vsp.SetAnalysisInputDefaults(analysis_name)
        vsp.PrintAnalysisInputs(analysis_name)
        #vsp.ComputeCFDMesh(vsp.SET_ALL, vsp.SET_NONE, vsp.CFD_VSPGEOM_TYPE)
        vsp.Update()
        return analysis_name

    def perform_analysis(self, analysis: str, data_to_get: list[str]) -> dict[str, list[float | int | str]]:
        vsp.DeleteAllResults()

        vsp.ExecAnalysis(analysis)
        return {
            data: self.fetch_last_results(analysis, data) for data in data_to_get
        }

    def set_simulation_setting(self, setting: AnalysisSettings, value: float | int | str):
        self._get_set_simulation_setting(setting, value)

    def get_simulation_setting(self, setting: AnalysisSettings) -> float | int | str:
        return self._get_set_simulation_setting(setting, None)

    def write_out_mesh(self):
        geom: str
        for geom in vsp.FindGeoms():
            if 'mesh' in vsp.GetGeomName(geom).lower():
                vsp.DeleteGeom(geom)

        # Now export as a vspgeom file for VSPAERO
        # After this you are good to go
        vsp.ExportFile(
            str(self.file.parent / (self.file.stem + ".vspgeom")),
            self.thick_value, vsp.EXPORT_VSPGEOM, 1, self.thin_value)

    def _get_set_simulation_setting(self, setting: AnalysisSettings, value: Optional[float | int | str]) -> Optional[float | int | str]:
        all_parms = [vsp.GetParmName(x) for x in vsp.GetGeomParmIDs(vsp.FindGeomsWithName(setting.geom)[0])]
        all_inputs = vsp.GetAnalysisInputNames(setting.analysis)
        res = None
        if setting.name in all_parms:
            # Setting the params (when value is not none) is a bit tricky
            # First we set it with SetParmValUpdate
            if setting.name in ['SectTess_U', 'ProjectedSpan', 'Span']:
                xsec_surf = vsp.GetXSecSurf(vsp.FindGeomsWithName(setting.geom)[0], 1)
                # IDK why there are two sections even though there is only one in the GUI
                # The first one is default?
                xsec = vsp.GetXSec(xsec_surf, 1)
                sec_tess_u = vsp.GetXSecParm(xsec, setting.name)

                if value is not None:
                    vsp.SetParmValUpdate(sec_tess_u, value)
                else:
                    res = vsp.GetParmVal(sec_tess_u)
            else:
                res_parm: str
                for parm_id in vsp.GetGeomParmIDs(vsp.FindGeomsWithName(setting.geom)[0]):
                    if vsp.GetParmName(parm_id) == setting.name:
                        if value is not None:
                            vsp.SetParmValUpdate(parm_id, value)
                        else:
                            res = vsp.GetParmVal(parm_id)
                        break

            if value is not None:
                vsp.Update()
                # Then, clear all old meshes. It creates more after a simulation for some reason
                # and then the ExportFile will happily export this outdated mesh. Don't ask why, I have no clue
                self.write_out_mesh()

        elif setting.name in all_inputs:
            if value is None:
                fun = self._input_getter_matcher[
                    self._type_matcher[vsp.GetAnalysisInputType(setting.analysis, setting.name)]]
                res = fun(setting.analysis, setting.name)
            else:
                _type = self._type_matcher[vsp.GetAnalysisInputType(setting.analysis, setting.name)]
                fun = self._input_setter_matcher[_type]
                fun(setting.analysis, setting.name, (_type(value),), 0)

                if setting.name == "ThinGeomSet":
                    self.thin_value = value
                    self.write_out_mesh()

                if setting.name == "GeomSet":
                    self.thick_value = value
                    self.write_out_mesh()

                vsp.Update()

        return res

    def sweep_analysis(self, settings: AnalysisSettings, data_to_get: list[str]) -> dict[str, dict[str, list[float | int | str]]]:
        return self.parallel_sweep_analysis([settings], data_to_get)

    def parallel_sweep_analysis(self, settings: list[AnalysisSettings], data_to_get: list[str]) -> dict[
        str, dict[str, list[float | int | str]]]:

        results = {}

        if not all([setting.num == settings[0].num for setting in settings]):
            raise ValueError("Number of settings does not match")

        if not all([setting.analysis == settings[0].analysis for setting in settings]):
            raise ValueError("Analyses do not match")

        default_vals = [[setting, self.get_simulation_setting(setting)] for setting in settings]

        for values in zip(*[np.linspace(setting.start, setting.end, setting.num) for setting in settings]):
            for value, setting in zip(values, settings):
                self.set_simulation_setting(setting, value)
            res = self.perform_analysis(settings[0].analysis, data_to_get)
            results[f"{' '.join([setting.name for setting in settings])}_{' '.join([f"{value:.2f}" for value in values])}"] = res

        for setting, default_val in default_vals:
            self.set_simulation_setting(setting, default_val)
        vsp.DeleteAllResults()
        return results

    def grid_analysis(self, settings: tuple[AnalysisSettings, AnalysisSettings]) -> dict[str, list[list[float | int | str]]]:
        raise NotImplementedError("Can not perform grid analysis yet")

    def fetch_last_results(self, analysis: str, name: str) -> list[float | int | str]:
        n_pts = vsp.GetIntAnalysisInput(analysis, "AlphaNpts")[0]
        return [self.get_result(vsp.FindResultsID("VSPAERO_History", x), name)[-1] for x in range(0, n_pts)]