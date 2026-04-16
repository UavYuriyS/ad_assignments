import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import fluids


class MissionTypes(str, Enum):
    WARMUP = auto()
    TAXI = auto()
    TAKEOFF = auto()
    CLIMB = auto()
    DESCENT = auto()
    LANDING = auto()

class AircraftTypes(str, Enum):
    SINGLE_ENGINE = auto()
    BIZ_JET = auto()
    REGIONAL_JET = auto()
    TRANSPORT_JET = auto()
    MIL_TRAINER = auto()
    FIGHTER = auto()
    MIL_PATROL = auto()
    AMPHIBIOUS = auto()

class EngineType(str, Enum):
    JET = auto()
    PROP = auto()

@dataclass
class MissionConfig:
    aircraft_type: AircraftTypes

@dataclass
class Aerodynamics:
    AR: float
    E: float
    L_D_max: float

    # transport
    CL_max_to: float = 1.9
    CL_max_l: float = 2.4

    dCD0_to: float = 0.015
    dCD0_l: float = 0.085

    dE_to = - 0.05
    dE_l = -0.1

    def _k(self, e: float):
        return 1 / (math.pi * self.AR * e)

    @property
    def K(self) -> float:
        return self._k(self.E)

    @property
    def K_to(self) -> float:
        return self._k(self.E + self.dE_to)

    @property
    def K_l(self) -> float:
        return self._k(self.E + self.dE_l)

    @property
    def CD0(self):
        return 1 / (4 * self.L_D_max ** 2 * self.K)

    @property
    def CD0_to(self):
        return self.CD0 + self.dCD0_to

    @property
    def CD0_l(self):
        return self.CD0 + self.dCD0_l



@dataclass
class Engine:
    type: EngineType
    sfc: float
    thrust: float

    prop_efficiency: Optional[float] = None

    @staticmethod
    def alpha(mach: float, alt: float) -> float:
        return 1.05 * (1.0 - 0.46*mach) * (fluids.ATMOSPHERE_1976(alt).rho / fluids.ATMOSPHERE_1976(0).rho)**0.7

@dataclass
class AircraftConfig:
    mission: MissionConfig
    aerodynamics: Aerodynamics
    engine: Engine

    souls_onboard: int
    weight_per_person: float
    W0: float
    takeoff_field_length: float
    landing_field_length: float
    takeoff_altitude: float
    landing_altitude: float
    stall_speed: float
    cruise_mach: float = None
    cruise_altitude: float = None
    loiter_mach: float = None
    loiter_altitude: float = None


    @property
    def cruise_airspeed(self) -> float:
        return fluids.ATMOSPHERE_1976(self.cruise_altitude).v_sonic * self.cruise_mach