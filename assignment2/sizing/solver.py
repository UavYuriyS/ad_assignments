import math

from config import AircraftConfig, MissionConfig, AircraftTypes, Engine, EngineType, MissionTypes
from sizing.config import Aerodynamics
from sizing.constraint_diagram import ConstraintPlotter, CruiseConstraint, TakeoffConstraint, ClimbConstraint, \
    BalancedTakeoffConstraint, LandingConstraint, StallConstraint
from sizing.empty_weight_fraction import EmptyWeightFraction, AircraftTypeEmptyWeight
from sizing.mission import MissionWeightFraction, ConstantFuelFractionMissionItem, ClimbAndAccelerateMissionItem, \
    CruiseMissionItem, LoiterMissionItem
from sizing.utils import M_TO_FEET, KG_TO_POUND, NMI_TO_M, MIN_TO_S, g
import fluids

CRUISE_MACH = 0.8
CRUISE_ALTITUDE = 36000 / M_TO_FEET

WEIGHT_PER_PERSON = 230 / KG_TO_POUND
PAX_NUMBER = 400
CREW_NUMBER = 10

MISSION_CRUISE_RANGE = 3500 * NMI_TO_M
DIVERSION_RANGE = 200 * NMI_TO_M

LOITER_AT_DIVERSION = 30 * MIN_TO_S

MAX_LIFT_TO_DRAG = 18
ASPECT_RATIO = 9
FACTOR_E = 0.9

TAKEOFF_FIELD_LENGTH = 9000 / M_TO_FEET
LANDING_FIELD_LENGTH = 9000 / M_TO_FEET
TAKEOFF_ALTITUDE = 0
LANDING_ALTITUDE = 0
CLIMBOUT_ALTITUDE = 400 / M_TO_FEET
STALL_SPEED = 88

config = AircraftConfig(
    mission=MissionConfig(AircraftTypes.TRANSPORT_JET),
    aerodynamics=Aerodynamics(
        AR = ASPECT_RATIO,
        E = FACTOR_E,
        L_D_max = MAX_LIFT_TO_DRAG,
    ),
    engine=Engine(
        type=EngineType.JET,
        sfc=15.8e-6,
        thrust=10000
    ),
    W0= 230000,
    pax_onboard=CREW_NUMBER + PAX_NUMBER,
    weight_per_pax=WEIGHT_PER_PERSON,
    cruise_mach=CRUISE_MACH,
    cruise_altitude=CRUISE_ALTITUDE,
    takeoff_field_length=TAKEOFF_FIELD_LENGTH,
    landing_field_length=LANDING_FIELD_LENGTH,
    stall_speed=STALL_SPEED,
    takeoff_altitude=TAKEOFF_ALTITUDE,
    landing_altitude=LANDING_ALTITUDE
)

print(config)

class Solver:
    config: AircraftConfig
    empty_weight_fraction: EmptyWeightFraction
    mission_weight_fraction: MissionWeightFraction
    def __init__(self, conf: AircraftConfig, empty_weight_fraction: EmptyWeightFraction, mission_weight_fraction: MissionWeightFraction):
        self.config = conf
        self.empty_weight_fraction = empty_weight_fraction
        self.mission_weight_fraction = mission_weight_fraction

        self.mission_weight_fraction.set_config(self.config)
        self.empty_weight_fraction.set_config(self.config)

    def estimate_w0(self):
        mission_weight_fraction = self.mission_weight_fraction.total_fuel_weight_fraction()
        empty_weight_fraction = self.empty_weight_fraction.empty_weight_fraction()

        w_fixed = self.config.pax_onboard * self.config.weight_per_pax
        w_fixed += self.config.crew_onboard * self.config.weight_per_crew

        w_0 = w_fixed / (1-(mission_weight_fraction + empty_weight_fraction))
        return w_0


empty_weight_fraction_calc = EmptyWeightFraction(AircraftTypeEmptyWeight.BOMBER_AND_TRANSPORT)

takeoff_fraction_items = [
    ConstantFuelFractionMissionItem(MissionTypes.WARMUP),
    ConstantFuelFractionMissionItem(MissionTypes.TAXI),
]

cruise_fraction_items = takeoff_fraction_items + [
    ConstantFuelFractionMissionItem(MissionTypes.TAKEOFF),
    ConstantFuelFractionMissionItem(MissionTypes.CLIMB),
]

mission_weight_fraction_calc = MissionWeightFraction(cruise_fraction_items + [
    ClimbAndAccelerateMissionItem(0, CRUISE_MACH), # conservative estimate, should be something like V2
    CruiseMissionItem(CRUISE_MACH * fluids.ATMOSPHERE_1976(CRUISE_ALTITUDE).v_sonic, MISSION_CRUISE_RANGE),
    ConstantFuelFractionMissionItem(MissionTypes.DESCENT),
    ConstantFuelFractionMissionItem(MissionTypes.CLIMB),
    ClimbAndAccelerateMissionItem(0, CRUISE_MACH), # conservative estimate, should be something like V2 again
    ConstantFuelFractionMissionItem(MissionTypes.DESCENT),
    LoiterMissionItem(None, LOITER_AT_DIVERSION),
    ConstantFuelFractionMissionItem(MissionTypes.LANDING),
])

solver = Solver(config, empty_weight_fraction_calc, mission_weight_fraction_calc)

while True:
    initial_w_0 = config.W0

    w_0_estimate = solver.estimate_w0()

    error = w_0_estimate - initial_w_0
    print(f"Estimated W0: {w_0_estimate:.2f} kg, Error: {error:.2f} kg")

    config.W0 = w_0_estimate

    if abs(error) < 1:
        print("Converged!")
        break

cruise_mf = MissionWeightFraction(cruise_fraction_items, config).fuel_weight_fraction()
takeoff_mf = MissionWeightFraction(takeoff_fraction_items, config).fuel_weight_fraction()


cp = ConstraintPlotter(
    config=config,
    wing_load_range=(1000, 15000),
    constraints=[
        CruiseConstraint("cruise", config.cruise_altitude, config.cruise_airspeed, cruise_mf),
        TakeoffConstraint("takeoff field length", config.takeoff_altitude, 1.2*config.stall_speed, takeoff_mf, 0.03),
        BalancedTakeoffConstraint("balanced field length", config.takeoff_altitude, 1.2*config.stall_speed, takeoff_mf),
        ClimbConstraint("climb segment 1", config.takeoff_altitude, 1.2*config.stall_speed, takeoff_mf, 0.024),
        ClimbConstraint("climb segment 2", config.takeoff_altitude+CLIMBOUT_ALTITUDE, 1.25*config.stall_speed, takeoff_mf, 0.012),
        LandingConstraint("landing", config.landing_altitude, 1.2*config.stall_speed, 0.85, 0.45),
        StallConstraint("stall", config.landing_altitude, config.stall_speed, 0.85)

    ]
)

import matplotlib.pyplot as plt

fig = plt.figure()
ax = fig.subplots()

cp.draw_diagram(ax)

ax.set_title('Constraint diagram')
ax.legend()
ax.set_xlabel('W/S')
ax.set_ylabel('T/W')

T_to_W = 0.217 * 1.1
W_L = 4306

plt.show()
S = config.W0*g / W_L
Tr = T_to_W * config.W0 * g
print(f"Wing area: {S}")
print(f"Thrust required: {Tr}")

wingspan = math.sqrt(config.aerodynamics.AR*S)





