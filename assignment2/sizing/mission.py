from __future__ import annotations

import math
from dataclasses import dataclass
from enum import auto, Enum
from typing import Optional

from .config import AircraftConfig, MissionTypes, AircraftTypes, EngineType
from .utils import g

# Segment Single Biz Regional Trans- Mil. Fighters Mil. AmphiEngine Jet Turbo- port Trainer Patrol bious
# prop Jet
# Warmup 0.995 0.990 0.990 0.990 0.990 0.990 0.990 0.992
# Taxi 0.997 0.995 0.995 0.990 0.990 0.990 0.990 0.990
# Takeoff 0.998 0.995 0.995 0.995 0.990 0.990 0.995 0.996
# Climb/Acc. 0.992 0.980 0.985 0.980 0.980 0.930 0.980 0.985
# Descent 0.993 0.990 0.985 0.990 0.990 0.990 0.990 0.990
# Landing 0.993 0.992 0.995 0.992 0.995 0.995 0.992 0.990

_values = [
    [0.995, 0.990, 0.990, 0.990, 0.990, 0.990, 0.990, 0.992],
    [0.997, 0.995, 0.995, 0.990, 0.990, 0.990, 0.990, 0.990],
    [0.998, 0.995, 0.995, 0.995, 0.990, 0.990, 0.995, 0.996],
    [0.992, 0.980, 0.985, 0.980, 0.980, 0.930, 0.980, 0.985],
    [0.993, 0.990, 0.985, 0.990, 0.990, 0.990, 0.990, 0.990],
    [0.993, 0.992, 0.995, 0.992, 0.995, 0.995, 0.992, 0.990]
]

RESERVES = 0.05
TRAPPED = 0.01


class MissionWeightFraction:
    mission_items: list[BaseMissionItem]
    _config: AircraftConfig

    def __init__(self, mission_items: list[BaseMissionItem], config: AircraftConfig = None):
        self.mission_items = mission_items
        self._config = config

    def set_config(self, config: AircraftConfig):
        self._config = config
        for mission_item in self.mission_items:
            mission_item._config = config

    def total_fuel_weight_fraction(self) -> float:
        return (1 + RESERVES + TRAPPED) * (1 - self.fuel_weight_fraction())

    def fuel_weight_fraction(self) -> float:
        return math.prod([x.fuel_fraction for x in self.mission_items])

class BaseMissionItem:
    fuel_fraction: float
    _config: AircraftConfig

class ConstantFuelFractionMissionItem(BaseMissionItem):
    _mapper: dict[MissionTypes, dict[AircraftTypes, float]] = {
        mission_type: dict(zip(AircraftTypes, _values[i])) for i, mission_type in enumerate(MissionTypes)
    }
    mission_type: MissionTypes
    def __init__(self, mission_type: MissionTypes):
        self.mission_type = mission_type

    @property
    def fuel_fraction(self) -> float:
        return self._mapper[self.mission_type][self._config.mission.aircraft_type]

class ClimbAndAccelerateMissionItem(BaseMissionItem):
    mach_start: float
    mach_end: float
    def __init__(self, mach_start: float, mach_end: float):
        self.mach_start = mach_start
        self.mach_end = mach_end

    @property
    def fuel_fraction(self) -> float:

        def subsonic(m: float) -> float:
            return 1.0065 - 0.0325*m

        def supersonic(m: float) -> float:
            return 0.991 - 0.007 * m - 0.01 * m**2

        if 0.1 <= self.mach_start <= 1:
            divisor = subsonic(self.mach_start)
        elif self.mach_start < 0.1:
            divisor = 1
        else:
            divisor = subsonic(1) * supersonic(self.mach_start)

        if self.mach_end <= 1:
            fraction = subsonic(self.mach_end)
        else:
            fraction = subsonic(1) * supersonic(self.mach_end)

        return fraction / divisor

class CruiseMissionItem(BaseMissionItem):
    cruise_velocity: Optional[float]
    aircraft_range: float

    def __init__(self, cruise_velocity: Optional[float], aircraft_range: float):
        self.cruise_velocity = cruise_velocity
        self.aircraft_range = aircraft_range


    @property
    def fuel_fraction(self) -> float:
        if self._config.engine.type == EngineType.JET and self.cruise_velocity is None:
            raise ValueError("Cruise velocity must be specified for jet engines")

        if self._config.engine.type == EngineType.JET:
            return math.e ** (-self.aircraft_range * self._config.engine.sfc * g /
                              (self.cruise_velocity * self._config.aerodynamics.L_D_max * 0.866))
        else:
            return math.e ** (-self.aircraft_range * self._config.engine.sfc * g / (
                              self._config.aerodynamics.L_D_max * self._config.engine.prop_efficiency))


class LoiterMissionItem(BaseMissionItem):
    loiter_velocity: Optional[float]
    aircraft_range: float

    def __init__(self, cruise_velocity: Optional[float], aircraft_range: float):
        self.loiter_velocity = cruise_velocity
        self.aircraft_range = aircraft_range

    @property
    def fuel_fraction(self) -> float:
        if self._config.engine.type == EngineType.PROP and self.loiter_velocity is None:
            raise ValueError("Loiter velocity must be specified for prop engines")

        if self._config.engine.type == EngineType.JET:
            return math.e ** (-self.aircraft_range * self._config.engine.sfc * g /
                              self._config.aerodynamics.L_D_max)
        else:
            return math.e ** (-self.aircraft_range * self._config.engine.sfc * self.loiter_velocity * g / (
                              ( self._config.aerodynamics.L_D_max * 0.866 * self._config.engine.prop_efficiency)))
