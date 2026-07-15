"""
Airport and runway geometry for Headless ATC.
"""

import math


class Airport:
    """
    Represents airport layout and runway data.
    """

    def __init__(self, width, height, runway_heading=90.0):

        self.width = width
        self.height = height

        self.runway_heading = runway_heading

        self._build()


    def _build(self):
        """
        Create runway geometry.

        RWY09 threshold is at the left side.
        """

        rwy_y = self.height // 2

        rwy_len = max(
            4,
            int(self.width * 0.05)
        )

        rwy_start = max(
            2,
            (self.width - rwy_len) // 2
        )

        rwy_end = rwy_start + rwy_len


        self.rwy_y = rwy_y

        self.rwy_start = rwy_start
        self.rwy_end = rwy_end


        # RWY09 threshold
        self.threshold_x = rwy_start


        # Airport reference point
        self.apt_x = (
            rwy_start + rwy_end
        ) / 2.0

        self.apt_y = float(rwy_y)


        self.rwy_len = rwy_len



    def threshold(self):
        """
        Return runway threshold coordinate.
        """

        return (
            self.threshold_x,
            self.rwy_y
        )



    def tower_aim_point(self, distance_nm=0.4):
        """
        Point slightly beyond runway threshold.
        Used by tower autopilot.
        """

        angle = math.radians(
            RWY_HDG
        )

        dx_nm = (
            math.sin(angle)
            * distance_nm
        )

        dy_nm = (
            -math.cos(angle)
            * distance_nm
        )

        x = (
            self.airport.threshold_x
            +
            dx_nm / NM_PER_COL
        )

        y = (
            self.airport.rwy_y
            +
            dy_nm / NM_PER_ROW
        )

        return x, y



    def center(self):
        """
        Return airport center point.
        """

        return (
            self.apt_x,
            self.apt_y
        )



    def data(self):
        """
        Compatibility helper.

        Makes migration easier from the old dictionary format.
        """

        return {
            "rwy_y": self.rwy_y,
            "rwy_start": self.rwy_start,
            "rwy_end": self.rwy_end,
            "thr_x": self.threshold_x,
            "apt_x": self.apt_x,
            "apt_y": self.apt_y,
            "rwy_len": self.rwy_len,
        }
