"""
Terminal renderer for Headless ATC.

Renderer only displays simulation state.
No simulation logic belongs here.
"""

import curses

from config import (
    ACTIVE_RUNWAY,
    NM_PER_COL,
    NM_PER_ROW,
)

from geometry import heading_glyph



ASCII_SPLASH = r"""
 _   _               _ _
| | | |             | | |
| |_| | ___  __ _ __| | | ___  ___ ___
|  _  |/ _ \/ _` / _` | |/ _ \/ __/ __|
| | | |  __/ (_| | (_| | |  __/\__ \__ \
\_| |_/\___|\__,_|\__,_|_|\___||___/___/

          H E A D L E S S   A T C
"""



class Renderer:

    def __init__(self):

        self.C_SCOPE = 1
        self.C_PLANE = 2
        self.C_FOCUS = 3
        self.C_WARN = 4
        self.C_TEXT = 5
        self.C_RWY = 6
        self.C_HO = 7
        self.C_HANDOFF = 4


    def setup(self, stdscr):

        curses.curs_set(0)

        stdscr.nodelay(True)
        stdscr.keypad(True)

        curses.start_color()
        curses.use_default_colors()

        curses.init_pair(
            self.C_SCOPE,
            curses.COLOR_CYAN,
            -1
        )

        curses.init_pair(
            self.C_PLANE,
            curses.COLOR_WHITE,
            -1
        )

        curses.init_pair(
            self.C_FOCUS,
            curses.COLOR_YELLOW,
            -1
        )

        curses.init_pair(
            self.C_WARN,
            curses.COLOR_RED,
            -1
        )

        curses.init_pair(
            self.C_TEXT,
            curses.COLOR_GREEN,
            -1
        )

        curses.init_pair(
            self.C_RWY,
            curses.COLOR_BLUE,
            -1
        )

        curses.init_pair(
            self.C_HO,
            curses.COLOR_GREEN,
            -1
        )



    def splash(self, stdscr):

        stdscr.erase()

        rows, cols = stdscr.getmaxyx()

        lines = ASCII_SPLASH.strip("\n").splitlines()

        start_y = max(
            0,
            (rows - len(lines)) // 2
        )

        for i, line in enumerate(lines):

            try:

                x = max(
                    0,
                    (cols - len(line)) // 2
                )

                stdscr.addstr(
                    start_y + i,
                    x,
                    line,
                    curses.A_BOLD
                )

            except curses.error:
                pass


        msg = (
            "Airspace online. Press any key."
        )

        try:

            stdscr.addstr(
                start_y + len(lines) + 2,
                max(
                    0,
                    (cols - len(msg)) // 2
                ),
                msg
            )

        except curses.error:
            pass


        stdscr.refresh()

        stdscr.nodelay(False)

        stdscr.getch()

        stdscr.nodelay(True)



    def draw_box(
        self,
        stdscr,
        top,
        left,
        bottom,
        right
    ):

        attr = (
            curses.A_BOLD |
            curses.color_pair(
                self.C_SCOPE
            )
        )

        try:

            for x in range(left, right + 1):

                stdscr.addch(
                    top,
                    x,
                    "-",
                    attr
                )

                stdscr.addch(
                    bottom,
                    x,
                    "-",
                    attr
                )


            for y in range(top, bottom + 1):

                stdscr.addch(
                    y,
                    left,
                    "|",
                    attr
                )

                stdscr.addch(
                    y,
                    right,
                    "|",
                    attr
                )


        except curses.error:

            pass



    def draw_runway(
        self,
        stdscr,
        airport
    ):

        attr = (
            curses.color_pair(
                self.C_RWY
            )
        )

        try:

            for x in range(
                airport.rwy_start,
                airport.rwy_end + 1
            ):

                stdscr.addch(
                    airport.rwy_y,
                    x,
                    "=",
                    attr
                )


            stdscr.addstr(
                airport.rwy_y - 1,
                airport.threshold_x,
                "09",
                attr
            )

        except curses.error:

            pass



    def draw_dme_markers(
        self,
        stdscr,
        airport
    ):

        attr = curses.color_pair(
            self.C_TEXT
        )


        for nm in (10, 5):

            x = (
                airport.threshold_x
                - int(round(nm / NM_PER_COL))
            )

            y = airport.rwy_y


            try:

                if x > 1:

                    stdscr.addch(
                        y,
                        x,
                        ".",
                        attr
                    )

                    stdscr.addstr(
                        y - 1,
                        x,
                        f"{nm}nm",
                        attr
                    )

            except curses.error:

                pass



    def draw_aircraft(
        self,
        stdscr,
        simulation,
        aircraft,
        focus,
        cols
    ):

        for i, a in enumerate(aircraft):

            x = int(round(a.x))
            y = int(round(a.y))


            if x < 1 or y < 1:

                continue


            if a.warn:

                color = self.C_WARN

            elif a.handed_off:

                color = self.C_HO

            elif i == focus:

                color = self.C_FOCUS

            else:

                color = self.C_PLANE


            attr = curses.color_pair(color)


            try:

                stdscr.addch(
                    y,
                    x,
                    heading_glyph(a.hdg),
                    attr
                )

                dme = simulation.dme(a)

                line1 = (
                    f"{a.callsign} "
                    f"hdg{int(a.hdg):03d} "
                    f"spd{int(a.spd_kt):3d}kt"
                )

                line2 = (
                    f"alt{int(a.alt_ft):5d}ft "
                    f"dme{dme:4.1f}nm"
                )

                max_len = max(
                    0,
                    cols - (x + 2) - 1
                )

                stdscr.addstr(
                    y,
                    x + 2,
                    line1[:max_len],
                    attr
                )

                stdscr.addstr(
                    y + 1,
                    x + 2,
                    line2[:max_len],
                    attr
                )


            except curses.error:

                pass



    def draw(
        self,
        stdscr,
        simulation,
        focus
    ):

        stdscr.erase()


        rows, cols = stdscr.getmaxyx()

        scope_h = rows - 4
        scope_w = cols - 1


        self.draw_box(
            stdscr,
            0,
            0,
            scope_h - 1,
            scope_w - 1
        )


        title = (
            f" HEADLESS ATC "
            f"| RWY {ACTIVE_RUNWAY} "
            f"| Score {simulation.score} "
            f"| H/O {simulation.handoffs}"
        )


        try:

            stdscr.addstr(
                0,
                2,
                title,
                curses.color_pair(
                    self.C_SCOPE
                )
            )

        except curses.error:

            pass

        commands = (
            "COMMANDS: hdg ### | alt #### | spd ### | "
            "TAB next | ho | q quit"
        )

        try:

            stdscr.addstr(
                1,
                2,
                commands[:cols - 3],
                curses.color_pair(
                    self.C_TEXT
                )
            )

        except curses.error:

            pass


        self.draw_runway(
            stdscr,
            simulation.airport
        )


        self.draw_dme_markers(
            stdscr,
            simulation.airport
        )


        self.draw_aircraft(
            stdscr,
            simulation,
            simulation.aircraft,
            focus,
            cols
        )


        try:

            stdscr.addstr(
                rows - 2,
                0,
                simulation.info[:cols - 1],
                curses.color_pair(
                    self.C_TEXT
                )
            )

        except curses.error:

            pass


        stdscr.refresh()
