"""
Core simulation logic for Headless ATC.
"""

import random
import math
import time

from callsigns import generate_callsign
from aircraft import Aircraft
from config import (
    MAX_AIRCRAFT,
    SPAWN_INTERVAL,
    SPAWN_MIN_DIST_NM,
    SPAWN_MAX_TRIES,
    SPAWN_GRACE_S,

    WARN_DIST_NM,
    LOSS_DIST_NM,
    LOSS_PENALTY,
    LOSS_COOLDOWN_S,

    ALT_WARN_FT,
    ALT_LOSS_FT,

    LOC_CAPTURE_GATE_NM,
    HO_MIN_NM,
    HO_MAX_NM,
    HO_ALT_MAX_FT,

    BEAM_HALF_ANGLE_DEG,
    RWY_HDG,

    NM_PER_COL,
    NM_PER_ROW,
)

from geometry import (
    distance_xy_nm,
    distance_nm,
    bearing_deg,
    wrap_deg,
)


class Simulation:
    """
    Owns the world state.

    The UI should only display this state.
    """

    def __init__(self, airport):

        self.airport = airport

        self.aircraft = []

        self.focus_idx = 0

        self.counter = 0

        self.score = 0
        self.handoffs = 0

        self.last_spawn = time.time() - SPAWN_INTERVAL

        self.last_penalty = -999999

        self.info = (
            "Airspace online."
        )



    # ==================================
    # Spawning
    # ==================================

    def spawn_safe(self, now):

        w = self.airport.width
        h = self.airport.height


        for _ in range(SPAWN_MAX_TRIES):

            edge = random.choice(
                [
                    "N",
                    "S",
                    "W",
                    "E"
                ]
            )


            if edge == "N":

                x = random.randint(2, w - 3)
                y = 1

            elif edge == "S":

                x = random.randint(2, w - 3)
                y = h - 2

            elif edge == "W":

                x = 1
                y = random.randint(2, h - 3)

            else:

                x = w - 2
                y = random.randint(2, h - 3)



            if any(
                distance_xy_nm(
                    a.x,
                    a.y,
                    x,
                    y
                ) < SPAWN_MIN_DIST_NM
                for a in self.aircraft
            ):
                continue



            hdg = bearing_deg(
                x,
                y,
                self.airport.apt_x,
                self.airport.apt_y
            )

            hdg += random.uniform(
                -15,
                15
            )

            self.counter += 1


            callsign = generate_callsign()


            return Aircraft(
                callsign,
                x,
                y,
                wrap_deg(hdg),
                now
            )


        return None



    def try_spawn(self, now):

        if (
            now - self.last_spawn
            >= SPAWN_INTERVAL
            and len(self.aircraft)
            < MAX_AIRCRAFT
        ):

            aircraft = self.spawn_safe(now)

            self.last_spawn = now


            if aircraft:

                self.aircraft.append(
                    aircraft
                )

                self.info = (
                    f"{aircraft.callsign} entered."
                )



    # ==================================
    # Localizer
    # ==================================
    def tower_aim_point(self, distance_nm=0.4):
        """
        Point slightly beyond runway threshold.
        Used by tower autopilot.
        """

        angle = math.radians(
            RWY_HDG
        )

        x = (
            self.airport.threshold_x
            +
            math.sin(angle)
            * distance_nm
            / NM_PER_COL
        )

        y = (
            self.airport.rwy_y
            -
            math.cos(angle)
            * distance_nm
            / NM_PER_ROW
        )

        return x, y

    def beam_coords(self, aircraft):

        thr_x = self.airport.threshold_x
        thr_y = self.airport.rwy_y


        axis = math.radians(
            RWY_HDG + 180
        )


        ux = math.sin(axis)
        uy = -math.cos(axis)

        nx = -uy
        ny = ux


        dx = (
            aircraft.x - thr_x
        ) * NM_PER_COL

        dy = (
            aircraft.y - thr_y
        ) * NM_PER_ROW


        along = (
            dx * ux +
            dy * uy
        )

        cross = (
            dx * nx +
            dy * ny
        )


        return along, cross

    def approach_distance(self, aircraft):

        along, _ = self.beam_coords(
            aircraft
        )

        return along



    def in_loc_beam(self, aircraft):

        along, cross = self.beam_coords(
            aircraft
        )


        if along <= 0:

            return False


        limit = (
            math.tan(
                math.radians(
                    BEAM_HALF_ANGLE_DEG
                )
            )
            * along
        )


        return abs(cross) <= limit



    def dme(self, aircraft):
        """
        True DME/range from the runway threshold in NM.
        Always available regardless of aircraft position.
        """

        return distance_xy_nm(
            aircraft.x,
            aircraft.y,
            self.airport.threshold_x,
            self.airport.rwy_y,
        )

    def update_localizer(self):

        for a in self.aircraft:

            a.loc_captured = self.in_loc_beam(a)


    # ==================================
    # Handoff
    # ==================================

    def eligible_for_handoff(self, a):

        if a.handed_off:
            return False

        dme = self.approach_distance(a)

        return (
            a.loc_captured
            and self.in_loc_beam(a)
            and HO_MIN_NM <= dme <= HO_MAX_NM
            and a.alt_ft < HO_ALT_MAX_FT
        )


    def handoff(self, callsign):

        for a in self.aircraft:

            if a.callsign == callsign:

                if self.eligible_for_handoff(a):

                    a.handed_off = True

                    a.t_spd_kt = random.randint(
                        138,
                        160
                    )

                    self.handoffs += 1
                    self.score += 25

                    self.info = (
                        f"{callsign} handed to TWR"
                    )

                    return True


        self.info = (
            f"{callsign} not eligible."
        )

        return False


    # ==================================
    # Separation
    # ==================================

    def check_separation(self, now):

        for a in self.aircraft:

            a.warn = False


        for i in range(len(self.aircraft)):

            for j in range(i + 1, len(self.aircraft)):

                a = self.aircraft[i]
                b = self.aircraft[j]


                dist = distance_nm(a, b)

                alt = abs(
                    a.alt_ft -
                    b.alt_ft
                )


                if (
                    dist < WARN_DIST_NM
                    and alt < ALT_WARN_FT
                ):

                    a.warn = True
                    b.warn = True



                if (
                    dist < LOSS_DIST_NM
                    and alt < ALT_LOSS_FT
                ):

                    if (
                        now -
                        min(
                            a.spawn_t,
                            b.spawn_t
                        )
                        > SPAWN_GRACE_S
                    ):

                        if (
                            now -
                            self.last_penalty
                            > LOSS_COOLDOWN_S
                        ):

                            self.score = max(
                                0,
                                self.score -
                                LOSS_PENALTY
                            )

                            self.info = (
                                "LOSS OF SEP"
                            )

                            self.last_penalty = now

    # ==================================
    # Focus
    # ==================================

    def focus_next(self):
        """Select the next aircraft."""
        if self.aircraft:
            self.focus_idx = (
                self.focus_idx + 1
            ) % len(self.aircraft)


    def normalize_focus(self):
        """Keep the focus index valid."""
        if self.aircraft:
            self.focus_idx = min(
                self.focus_idx,
                len(self.aircraft) - 1
            )
        else:
            self.focus_idx = 0

    # ==================================
    # Tower
    # ==================================

    def update_tower(self, a, dt):

        aim_x, aim_y = self.tower_aim_point()

        a.t_hdg = bearing_deg(
            a.x,
            a.y,
            aim_x,
            aim_y
        )


        dme = self.dme(a)

        if (
            dme < 0.2
            and a.alt_ft < 100
        ):
            self.aircraft.remove(a)
            return


        a.t_alt_ft = (
            20
            +
            dme * 318
        )


        a.update(
            dt,
            NM_PER_COL,
            NM_PER_ROW
        )

    # ==================================
    # Main update
    # ==================================

    def update(self, dt, now):

        self.try_spawn(now)


        for a in self.aircraft:

            if a.handed_off:

                self.update_tower(a, dt)

            else:

                a.update(
                    dt,
                    NM_PER_COL,
                    NM_PER_ROW
                )


        self.aircraft = [
            a for a in self.aircraft
            if (
                -2 < a.x <
                self.airport.width + 2
                and
                -2 < a.y <
                self.airport.height + 2
            )
        ]


        self.update_localizer()

        self.check_separation(now)

        self.update_handoff_prompt()

    def update_handoff_prompt(self):

        if not self.aircraft:
            return

        self.normalize_focus()

        a = self.aircraft[self.focus_idx]

        eligible = self.eligible_for_handoff(a)


        if eligible and not a.ho_eligible_last:

            self.info = (
                f"{a.callsign} READY FOR H/O — type 'ho' and Enter"
            )


        a.ho_eligible_last = eligible
