import math
from dataclasses import dataclass
from typing import Optional

from matplotlib import pyplot as plt


@dataclass
class Segment:
    root: float
    sweep: Optional[float] = 0
    length: Optional[float] = 0


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Chord:
    start: Point
    end: Point

    @property
    def c(self):
        return self.end.x - self.start.x

@dataclass
class Wing:
    segments: list[Segment]

    @property
    def area(self):
        area = 0
        for i in range(len(self.segments) - 1):
            segment1 = self.segments[i]
            segment2 = self.segments[i + 1]
            segment_length = segment1.length
            area += (segment1.root + segment2.root) * segment_length / 2
        return area

    @property
    def AR(self):
        return sum([seg.length for seg in self.segments])**2 / self.area


    def get_mac(self):
        mac = 0

        for i in range(len(self.segments) - 1):
            segment1 = self.segments[i]
            segment2 = self.segments[i + 1]
            segment_length = segment1.length

            segment_area = (segment1.root + segment2.root) * segment_length / 2
            lambda_ = segment2.root / segment1.root
            mac += segment_area / 3 * (1 + lambda_ + lambda_**2) / (1 + lambda_) * segment1.root

        return mac / self.area * 2

    def get_mac_location(self) -> Point:
        loc = Point(0, 0)
        mac = self.get_mac()

        for i in range(len(self.segments) - 1):
            segment1 = self.segments[i]
            segment2 = self.segments[i + 1]

            if segment1.root == segment2.root == mac:
                loc.y += segment1.length / 2
                continue

            if segment1.root == segment2.root:
                loc.y += segment1.length
                continue

            y = (segment1.root-mac)/(segment1.root - segment2.root) * segment1.length

            x_segment_2 = math.tan(segment1.sweep) * segment1.length

            if segment1.length > y > 0:
                loc.x += x_segment_2 * (segment1.root-mac)/(segment1.root - segment2.root)
                loc.y += y
                return loc
            else:
                loc.y += segment1.length
                loc.x += x_segment_2

        return None

    def draw_wing(self, ref=Point(0, 0), axis=None):
        import matplotlib.pyplot as plt

        x_le = [ref.x]
        y_le = [ref.y]

        x_te = [ref.x + self.segments[0].root]
        y_te = [ref.y]

        for i, segment in enumerate(self.segments):
            if segment.sweep is not None and segment.length is not None:
                x_le.append(x_le[-1] + math.tan(segment.sweep) * segment.length)
                y_le.append(y_le[-1] + segment.length)
            else:
                x_le.append(x_le[-1])
                y_le.append(y_le[-1])

            if i < len(self.segments) - 1:
                x_te.append(x_le[-1] + self.segments[i+1].root)
                y_te.append(y_le[-1])

        if axis is not None:
            axis.plot([x_le[0], x_te[0]], [y_le[0], y_te[0]], color='black')
            axis.plot([x_le[-1], x_te[-1]], [y_le[-1], y_te[-1]], color='black')
            axis.plot(x_le, y_le)
            axis.plot(x_te, y_te)
            axis.set_xlabel('x')
            axis.set_ylabel('y')
            axis.set_title('Wing Planform')
            axis.axis('equal')
            axis.grid()
        else:
            plt.plot([x_le[0], x_te[0]], [y_le[0], y_te[0]], color='black')
            plt.plot([x_le[-1], x_te[-1]], [y_le[-1], y_te[-1]], color='black')
            plt.plot(x_le, y_le)
            plt.plot(x_te, y_te)
            plt.xlabel('x')
            plt.ylabel('y')
            plt.title('Wing Planform')
            plt.axis('equal')
            plt.grid()
            plt.show()


wing = Wing([
    Segment(root=5, sweep=math.radians(42), length=5.4),
    Segment(root=2, sweep=math.radians(0), length=6.6),
    Segment(root=2)
])
print(wing.area)

ax = plt.subplot(1, 1, 1)
wing.draw_wing(axis=ax)

htail_volume_coeff = 1.0
vtail_volume_coeff = 0.1

FUSELAGE_LENGTH = 26
WINGSPAN = 24

# Rear engines
VTAIL_ARM = 0.5
HTAIL_ARM = 0.5

VTAIL_TAPER = 0.25
HTAIL_TAPER = 0.25

HTAIL_AR = 5
VTAIL_AR = 5

VTAIL_LE_SWEEP = math.radians(30)
HTAIL_LE_SWEEP = math.radians(30)

vtail_area_wet = vtail_volume_coeff * WINGSPAN * wing.area * 2 / (VTAIL_ARM * FUSELAGE_LENGTH)
htail_area = htail_volume_coeff * wing.get_mac() * wing.area * 2 / (HTAIL_ARM * FUSELAGE_LENGTH)

print("VTail Area (wet):", vtail_area_wet)
print("HTail Area:", htail_area)

b_vtail = math.sqrt(VTAIL_AR * vtail_area_wet)
b_htail = math.sqrt(HTAIL_AR * htail_area/2)

r_vtail = 2 * vtail_area_wet / (b_vtail * (1 + VTAIL_TAPER))
r_htail = 2 * htail_area/2 / (b_htail * (1 + HTAIL_TAPER))

vtail = Wing([
    Segment(root=r_vtail, sweep=VTAIL_LE_SWEEP, length=b_vtail),
    Segment(root=r_vtail * VTAIL_TAPER)
])

htail = Wing([
    Segment(root=r_htail, sweep=HTAIL_LE_SWEEP, length=b_htail),
    Segment(root=r_htail * HTAIL_TAPER)
])
htail.draw_wing(ref=Point(FUSELAGE_LENGTH * HTAIL_ARM - htail.get_mac_location().x, 0), axis=ax)

plt.show()
print("Htail area:", htail.area)
print("Htail MAC:", htail.get_mac())
print("Htail AR:", htail.AR)
print("Area:", wing.area)
print("MAC:", wing.get_mac())
print("MAC Location:", wing.get_mac_location())

