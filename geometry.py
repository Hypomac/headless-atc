"""
Geometry helpers for Headless ATC.

All calculations are done in nautical miles.
The terminal coordinate system is only a display layer.
"""

import math

from config import NM_PER_COL, NM_PER_ROW


# =========================
# Basic helpers
# =========================

def clamp(v, lo, hi):
    """Keep value inside range."""
    return lo if v < lo else hi if v > hi else v


def wrap_deg(d):
    """Normalize heading to 0-359.999 degrees."""
    return d % 360.0


def shortest_turn(a, b):
    """
    Smallest signed turn from heading a to heading b.

    Returns:
        -180 ... +180 degrees
    """
    return (b - a + 180.0) % 360.0 - 180.0


# =========================
# Coordinate conversion
# =========================

def xy_to_nm_delta(x1, y1, x2, y2):
    """
    Convert terminal coordinates to nautical mile coordinates.

    Terminal:
        x = columns
        y = rows

    Real world:
        columns and rows have different scales.
    """

    dx_nm = (x2 - x1) * NM_PER_COL
    dy_nm = (y2 - y1) * NM_PER_ROW

    return dx_nm, dy_nm


def distance_xy_nm(x1, y1, x2, y2):
    """
    Distance between two screen coordinates in NM.
    """

    dx_nm, dy_nm = xy_to_nm_delta(
        x1, y1,
        x2, y2
    )

    return math.hypot(dx_nm, dy_nm)


def distance_nm(a, b):
    """
    Distance between two aircraft objects.
    """

    return distance_xy_nm(
        a.x,
        a.y,
        b.x,
        b.y
    )


# =========================
# Heading calculations
# =========================

def bearing_deg(x1, y1, x2, y2):
    """
    Calculate bearing.

    Convention:
        0   = up/north
        90  = right/east
        180 = down/south
        270 = left/west
    """

    dx_nm, dy_nm = xy_to_nm_delta(
        x1, y1,
        x2, y2
    )

    angle = math.degrees(
        math.atan2(
            dx_nm,
            -dy_nm
        )
    )

    return wrap_deg(angle)


def kt_to_nm_per_sec(knots):
    """
    Convert knots (NM/hour) to NM/second.
    """

    return knots / 3600.0


def heading_glyph(heading):
    """
    Convert heading to readable terminal arrow.
    """

    candidates = [
        (0, "^"),
        (90, ">"),
        (180, "v"),
        (270, "<"),
    ]

    heading = wrap_deg(heading)

    return min(
        candidates,
        key=lambda item:
            abs(shortest_turn(heading, item[0]))
    )[1]
