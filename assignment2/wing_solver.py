import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class Segment:
    root: float
    sweep: Optional[float] = None
    length: Optional[float] = None


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


Wing = Wing([
    Segment(root=15, sweep=math.radians(2), length=25),
    Segment(root=15, sweep=math.radians(20), length=80),
    Segment(root=9)
])

vtail_volume_coeff = 1.0
htail_volume_coeff = 0.01

fuselage_length = 28

print("Area:", Wing.area)
print("MAC:", Wing.get_mac())
print("MAC Location:", Wing.get_mac_location())

