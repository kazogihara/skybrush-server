from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


__all__ = ("GPSFix", "GPSFixType")


class GPSFixType(IntEnum):
    """Known GPS fix types."""

    NO_GPS = 0
    NO_FIX = 1
    FIX_2D = 2
    FIX_3D = 3
    DGPS = 4
    RTK_FLOAT = 5
    RTK_FIXED = 6
    STATIC = 7


@dataclass
class GPSFix:
    """Class representing basic GPS fix information of a single UAV."""

    type: GPSFixType = GPSFixType.NO_GPS
    num_satellites: Optional[int] = None

    def update_from(self, other) -> None:
        """Updates this GPS fix object from another one. You may also specify a
        single GPSFixType_ as the input; in this case, the fix type will be
        updated and the number of satellites will be cleared.
        """
        if isinstance(other, int):
            self.type = GPSFixType(other)
            self.num_satellites = None
        elif isinstance(other, GPSFixType):
            self.type = other
            self.num_satellites = None
        else:
            self.type = other.type
            self.num_satellites = other.num_satellites
