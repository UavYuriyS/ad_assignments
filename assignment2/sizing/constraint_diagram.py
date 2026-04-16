from __future__ import annotations
import math
from dataclasses import dataclass, field

import fluids
import numpy as np
from matplotlib.axes import Axes
from numpy import ndarray

from sizing.config import AircraftConfig
from sizing.utils import g, SLUG_TO_N

class ConstraintPlotter:
    _config: AircraftConfig
    _n_points=200
    wing_load_range: tuple[float, float]
    constraints: list[Constraint]

    def __init__(self, config: AircraftConfig, wing_load_range: tuple[float, float], constraints: list[Constraint]):
        self._config = config
        self.wing_load_range = wing_load_range
        self.constraints = constraints

        for constraint in constraints:
            constraint._config = config

    def draw_diagram(self, ax: Axes) -> None:

        wing_loadings = np.linspace(*self.wing_load_range, self._n_points)
        for constraint in self.constraints:
            constraint.draw(ax, wing_loadings)

@dataclass
class Constraint:
    _config: AircraftConfig = field(init=False)
    name: str
    altitude: float
    airspeed: float
    mass_fraction: float

    def _get_engine_alpha(self) -> float:
        mach = self.airspeed / fluids.ATMOSPHERE_1976(self.altitude).v_sonic
        alpha = self._config.engine.alpha(mach, self.altitude)
        return alpha

    def _thrust_to_weight_master(self, wing_loading: ndarray, load_factor: float, climb_grad: float, accel: float) -> ndarray:
        CD_0 = self._config.aerodynamics.CD0
        K = self._config.aerodynamics.K

        q = fluids.ATMOSPHERE_1976(self.altitude).rho * self.airspeed**2 / 2
        alpha = self._get_engine_alpha()

        return self.mass_fraction / alpha * (
            q / (self.mass_fraction * wing_loading)*(
                CD_0 + K * (load_factor * self.mass_fraction * wing_loading / q)**2) +
                climb_grad + 1/g * accel
        )

    def get_thrust_to_weight(self, wing_loading: ndarray) -> ndarray:
        pass

    def draw(self, ax: Axes, wing_loading: ndarray):
        ax.plot(wing_loading, self.get_thrust_to_weight(wing_loading), label=self.name)

class ConstantWingLoadingConstraint(Constraint):
    def get_thrust_to_weight(self, *args, **kwargs) -> float:
        pass

    def draw(self, ax: Axes, wing_loading: ndarray):
        color = next(ax._get_lines.prop_cycler)['color']
        ax.axvline(self.get_thrust_to_weight(wing_loading), label=self.name, color=color)

@dataclass
class ClimbConstraint(Constraint):
    climb_grad: float
    engine_count: int = 2
    inop_count: int = 1
    def get_thrust_to_weight(self, wing_loading: ndarray) -> ndarray:
        return (self._thrust_to_weight_master(
            wing_loading, load_factor=1, climb_grad=self.climb_grad, accel=0)
                / ((self.engine_count - self.inop_count) / self.engine_count))

@dataclass
class CruiseConstraint(Constraint):
    def get_thrust_to_weight(self, wing_loading: ndarray) -> ndarray:
        return self._thrust_to_weight_master(wing_loading, load_factor=1, climb_grad=0, accel=0)


@dataclass
class TakeoffConstraint(Constraint):
    mu: float
    f_obs: float = 1.13
    f_ms: float = 1.15
    f_v: float = 1.44
    def get_thrust_to_weight(self, wing_loading: ndarray) -> ndarray:
        alpha = self._get_engine_alpha()
        rho = fluids.ATMOSPHERE_1976(self.altitude).rho
        CL_max_to = self._config.aerodynamics.CL_max_to
        CD0_to = self._config.aerodynamics.CD0_to

        to_length = self._config.takeoff_field_length

        return self.f_obs * self.f_ms * (self.f_v * self.mass_fraction ** 2)/(
                alpha * rho * g * CL_max_to * to_length) * wing_loading + \
            (0.7 * CD0_to)/(self.mass_fraction * CL_max_to) + self.mu

@dataclass
class BalancedTakeoffConstraint(Constraint):
    def get_thrust_to_weight(self, wing_loading: ndarray):

        CL_max_to = self._config.aerodynamics.CL_max_to
        sigma = fluids.ATMOSPHERE_1976(self.altitude).rho / fluids.ATMOSPHERE_1976(0).rho
        to_length = self._config.takeoff_field_length

        return 37.5 / SLUG_TO_N * wing_loading / (sigma * CL_max_to * to_length)

@dataclass
class LandingConstraint(ConstantWingLoadingConstraint):
    mu: float
    h_obs: float = 15.24
    f_MS: float = 0.66
    f_V: float = 1.3
    gamma: float = 3
    def get_thrust_to_weight(self, wing_loading: ndarray) -> float:
        rho = fluids.ATMOSPHERE_1976(self.altitude).rho
        CL_max_l = self._config.aerodynamics.CL_max_l

        return self.f_MS * (self._config.landing_field_length -
            self.h_obs / (self.f_MS * math.tan(math.radians(self.gamma)))) * \
            rho * g * self.mu * CL_max_l / (self.f_V ** 2 * self.mass_fraction)

@dataclass
class StallConstraint(ConstantWingLoadingConstraint):
    def get_thrust_to_weight(self, wing_loading: ndarray) -> float:
        rho = fluids.ATMOSPHERE_1976(self.altitude).rho
        return 0.5 * rho / self.mass_fraction * self._config.stall_speed**2 * self._config.aerodynamics.CL_max_l