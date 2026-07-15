"""
Aircraft model for Headless ATC.
"""

from config import (
    SPD_INIT_KT,
    CLIMB_RATE_FTPS,
    SPD_MIN_KT,
    SPD_MAX_KT,
    SPD_SLEW_KT_PER_S,
    TURN_RATE_DPS,
    SPAWN_ALT_FT,
)

from geometry import (
    clamp,
    wrap_deg,
    shortest_turn,
    kt_to_nm_per_sec,
)


class Aircraft:
    """
    Represents one aircraft in the simulation.
    """

    __slots__ = (
        "callsign",
        "x",
        "y",
        "hdg",
        "t_hdg",
        "spd_kt",
        "t_spd_kt",
        "alt_ft",
        "t_alt_ft",
        "spawn_t",
        "warn",
        "gate10_seen",
        "loc_captured",
        "ho_eligible_last",
        "handed_off",
        "landed",
    )

    def __init__(self, cs, x, y, hdg, now):

        self.callsign = cs

        # Position (terminal coordinates)
        self.x = float(x)
        self.y = float(y)

        # Heading
        self.hdg = float(hdg)
        self.t_hdg = float(hdg)

        # Speed
        self.spd_kt = float(SPD_INIT_KT)
        self.t_spd_kt = float(SPD_INIT_KT)

        # Altitude
        self.alt_ft = float(SPAWN_ALT_FT)
        self.t_alt_ft = float(SPAWN_ALT_FT)

        # Timing
        self.spawn_t = float(now)

        # Warnings
        self.warn = False

        # Localizer state
        self.gate10_seen = False
        self.loc_captured = False

        # Handoff prompt memory
        self.ho_eligible_last = False

        # Tower has  accepted the aircraft
        self.handed_off = False

        # Aircraft has landed
        self.landed = False

    def update_heading(self, dt):
        """
        Move current heading toward commanded heading.
        """

        diff = shortest_turn(
            self.hdg,
            self.t_hdg
        )

        self.hdg = wrap_deg(
            self.hdg +
            clamp(
                diff,
                -TURN_RATE_DPS * dt,
                TURN_RATE_DPS * dt
            )
        )


    def update_altitude(self, dt):
        """
        Move altitude toward selected altitude.
        """

        diff = self.t_alt_ft - self.alt_ft

        self.alt_ft += clamp(
            diff,
            -CLIMB_RATE_FTPS * dt,
            CLIMB_RATE_FTPS * dt
        )


    def update_speed(self, dt):
        """
        Move speed toward selected speed.
        """

        diff = self.t_spd_kt - self.spd_kt

        self.spd_kt += clamp(
            diff,
            -SPD_SLEW_KT_PER_S * dt,
            SPD_SLEW_KT_PER_S * dt
        )

        self.spd_kt = clamp(
            self.spd_kt,
            SPD_MIN_KT,
            SPD_MAX_KT
        )


    def update_motion(self, dt, nm_per_col, nm_per_row):
        """
        Move aircraft according to heading and speed.

        Position remains in terminal coordinates.
        """

        speed_nm = kt_to_nm_per_sec(
            self.spd_kt
        )

        import math

        r = math.radians(self.hdg)

        dx_nm = (
            math.sin(r)
            * speed_nm
            * dt
        )

        dy_nm = (
            -math.cos(r)
            * speed_nm
            * dt
        )

        self.x += dx_nm / nm_per_col
        self.y += dy_nm / nm_per_row


    def update(self, dt, nm_per_col, nm_per_row):
        """
        Update complete aircraft state.
        """

        self.update_heading(dt)
        self.update_altitude(dt)
        self.update_speed(dt)
        self.update_motion(
            dt,
            nm_per_col,
            nm_per_row
        )
