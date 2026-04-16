from dataclasses import dataclass
from enum import Enum

from sizing.config import AircraftConfig
from sizing.utils import KG_TO_POUND


@dataclass
class GrowthEntry:
    C: float
    XX: float


# From Nicolai
class AircraftTypeEmptyWeight:
    BOMBER_AND_TRANSPORT = GrowthEntry(0.911, 0.947)


class EmptyWeightFraction:
    approximator: GrowthEntry
    _config: AircraftConfig
    def __init__(self, approximator: GrowthEntry):
        self.approximator = approximator

    def set_config(self, config: AircraftConfig):
        self._config = config

    def empty_weight_fraction(self):
        return self.approximator.C * (self._config.W0 * KG_TO_POUND) ** (self.approximator.XX - 1)