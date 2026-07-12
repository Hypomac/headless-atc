# Headless ATC
"""
**Headless ATC** is a terminal-based air traffic control simulator focused on logic, timing, and separation — not graphics.

There is no radar screen.
There is no mouse.
There is only the airspace, the rules, and your decisions.

This project is inspired by radar-style ATC games, but deliberately implemented as a **headless, CLI-first simulation**.
Aircraft follow deterministic flight paths, real constraints apply, and every mistake is yours alone.
The terminal is not a limitation — it’s the point.

Headless ATC is built around a simple principle:

> **Python owns the truth.**
> **The interface only reports what already happened.**

No hidden automation. No visual crutches. Just altitude, heading, speed, separation, and handover at the right moment.

If you enjoy systems thinking, classic simulations, and the quiet stress of managing multiple aircraft with minimal feedback,
you’re in the right place.
"""

import curses
import time
import math
import random


# =========================
# UI / Presentation
# =========================

ASCII_SPLASH = r"""
 _   _               _ _
| | | |             | | |
| |_| | ___  __ _ __| | | ___  ___ ___
|  _  |/ _ \/ _` / _` | |/ _ \/ __/ __|
| | | |  __/ (_| | (_| | |  __/\__ \__ \
\_| |_/\___|\__,_|\__,_|_|\___||___/___/

          H E A D L E S S   A T C
"""


def show_splash_curses(stdscr):
    """Curses-safe splash so it is actually visible."""
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()
    lines = ASCII_SPLASH.strip("\n").splitlines()

    start_y = max(0, (rows - len(lines) - 3) // 2)
    for i, line in enumerate(lines):
        x = max(0, (cols - len(line)) // 2)
        try:
            stdscr.addstr(start_y + i, x, line, curses.A_BOLD)
        except curses.error:
            pass

    msg = "Airspace online. Maintain separation. (Press any key to start)"
    try:
        stdscr.addstr(start_y + len(lines) + 2, max(0, (cols - len(msg)) // 2), msg)
    except curses.error:
        pass

    stdscr.nodelay(False)
    stdscr.refresh()
    try:
        stdscr.getch()
    except curses.error:
        pass
    stdscr.nodelay(True)


# =======================
# Configuration
# =======================

# Runway and heading convention
ACTIVE_RUNWAY = "09"
RWY_HDG = 90.0  # 0 up, 90 right, 180 down, 270 left

# -----------------------------------------------------------------------------
# World/display scale
# -----------------------------------------------------------------------------
# IMPORTANT:
# The simulation is now handled in real nautical-mile geometry, while the terminal
# is only a display surface. Terminal cells are not square: one text row is
# visually much taller than one text column is wide. If we treat one row and one
# column as the same distance, aircraft appear to move too fast north/south, and
# distance/separation logic becomes distorted.
#
# NM_PER_ROW says how many nautical miles one terminal row represents.
# CELL_ASPECT says how many columns visually equal the height of one row.
# A typical terminal font is roughly 2:1, so one row ~= two columns visually.
# Therefore one column represents fewer NM than one row.
#
# Tune CELL_ASPECT if your terminal/font looks different:
#   1.6 = less correction
#   2.0 = good default
#   2.2 = stronger correction
# -----------------------------------------------------------------------------
NM_PER_ROW = 0.5
CELL_ASPECT = 2.0
NM_PER_COL = NM_PER_ROW / CELL_ASPECT

# ILS / localizer-like beam
BEAM_HALF_ANGLE_DEG = 10.0

# Handoff/localizer gates in NM
# Previously the comments said 10->5 NM, while constants effectively allowed
# 15->2 NM. This is now made explicit and internally consistent.
LOC_CAPTURE_GATE_NM = 10.0
HO_MIN_NM = 5.0
HO_MAX_NM = 10.0
HO_ALT_MAX_FT = 4000

# Geometry tolerances (currently not used directly, kept for future gameplay tuning)
CENTERLINE_TOL_CELLS = 1.5
REQUIRE_WEST_OF_THR = True  # for RWY09 approach side

# Rates
TURN_RATE_DPS = 180.0 / 60.0        # 3 deg/sec = 180 deg/min
CLIMB_RATE_FTPS = 1200.0 / 60.0     # 20 ft/sec = 1200 ft/min

# Speed in knots (still controllable)
SPD_INIT_KT = 250
SPD_MIN_KT = 160
SPD_MAX_KT = 250
SPD_SLEW_KT_PER_S = 10.0

# Traffic
SPAWN_INTERVAL = 40.0
MAX_AIRCRAFT = 3

# Spawn fairness
SPAWN_MIN_DIST_NM = 10.0
SPAWN_MAX_TRIES = 40
SPAWN_GRACE_S = 8.0

# Separation penalty only, in nautical miles
WARN_DIST_NM = 5.0
LOSS_DIST_NM = 2.5
LOSS_PENALTY = 5
LOSS_COOLDOWN_S = 5.0

# Vertical separation thresholds
ALT_WARN_FT = 1000   # warn if < 5 NM and < 1000 ft vertical separation
ALT_LOSS_FT = 300    # loss if < 2.5 NM and < 300 ft vertical separation

# Timing
DT_CAP = 0.10
FRAME_SLEEP = 0.02

# Colors
C_SCOPE = 1
C_PLANE = 2
C_FOCUS = 3
C_WARN  = 4
C_TEXT  = 5
C_RWY   = 6
C_HO    = 7


# =======================
# Helpers
# =======================

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def wrap_deg(d):
    return d % 360.0


def shortest_turn(a, b):
    """Signed smallest angular difference [-180, 180]."""
    return (b - a + 180.0) % 360.0 - 180.0


def xy_to_nm_delta(x1, y1, x2, y2):
    """
    Convert a terminal-cell delta into real NM delta.

    x/y are still stored as terminal coordinates because curses draws in rows and
    columns, but all geometry calculations should go through this scaling.
    """
    dx_nm = (x2 - x1) * NM_PER_COL
    dy_nm = (y2 - y1) * NM_PER_ROW
    return dx_nm, dy_nm


def distance_xy_nm(x1, y1, x2, y2):
    """Real distance in NM between two terminal-coordinate points."""
    dx_nm, dy_nm = xy_to_nm_delta(x1, y1, x2, y2)
    return math.hypot(dx_nm, dy_nm)


def distance_nm(a, b):
    """Real distance in NM between two Aircraft objects."""
    return distance_xy_nm(a.x, a.y, b.x, b.y)


def bearing_deg(x1, y1, x2, y2):
    """
    Bearing with convention:
      0 up, 90 right, 180 down, 270 left

    Uses NM-scaled terminal coordinates so headings are not distorted by the
    non-square terminal cell aspect ratio.
    """
    dx_nm, dy_nm = xy_to_nm_delta(x1, y1, x2, y2)
    ang = math.degrees(math.atan2(dx_nm, -dy_nm))
    return wrap_deg(ang)


def kt_to_nm_per_sec(kt):
    """Knots = NM/hour, so NM/sec = kt / 3600."""
    return kt / 3600.0


def heading_glyph(h):
    """4-way-ish glyph; cardinal arrows are most readable."""
    candidates = [(0, "^"), (90, ">"), (180, "v"), (270, "<")]
    h = wrap_deg(h)
    return min(candidates, key=lambda t: abs(shortest_turn(h, t[0])))[1]


def draw_box(stdscr, top, left, bottom, right, attr):
    # Safer drawing: ignore curses errors near edges / resizing
    try:
        for x in range(left, right + 1):
            stdscr.addch(top, x, "-", attr)
            stdscr.addch(bottom, x, "-", attr)
        for y in range(top, bottom + 1):
            stdscr.addch(y, left, "|", attr)
            stdscr.addch(y, right, "|", attr)
        stdscr.addch(top, left, "+", attr)
        stdscr.addch(top, right, "+", attr)
        stdscr.addch(bottom, left, "+", attr)
        stdscr.addch(bottom, right, "+", attr)
    except curses.error:
        pass


# =======================
# Aircraft model
# =======================

class Aircraft:
    __slots__ = (
        "callsign",
        "x", "y",
        "hdg", "t_hdg",
        "spd_kt", "t_spd_kt",
        "alt_ft", "t_alt_ft",
        "spawn_t",
        "warn",
        # ILS-beam state:
        "gate10_seen",
        "loc_captured",
        # prompt memory:
        "ho_eligible_last"
    )

    def __init__(self, cs, x, y, hdg, now):
        self.callsign = cs
        self.x = float(x)
        self.y = float(y)

        self.hdg = float(hdg)
        self.t_hdg = float(hdg)

        self.spd_kt = float(SPD_INIT_KT)
        self.t_spd_kt = float(SPD_INIT_KT)

        self.alt_ft = float(7000)
        self.t_alt_ft = float(7000)

        self.spawn_t = float(now)
        self.warn = False

        # 10 NM gate logic: capture localizer when crossing into <=10 NM
        self.gate10_seen = False
        self.loc_captured = False

        # prompt transition memory
        self.ho_eligible_last = False


# =======================
# Airport geometry
# =======================

def build_airport(w, h):
    """
    Centered runway, small footprint (~5% width).
    RWY09 threshold at left end.
    """
    rwy_y = h // 2
    rwy_len = max(4, int(w * 0.05))
    rwy_start = clamp((w - rwy_len) // 2, 2, w - 3 - rwy_len)
    rwy_end = rwy_start + rwy_len
    thr_x = rwy_start

    # Airfield centerpoint (runway midpoint) used for initial headings only.
    apt_x = (rwy_start + rwy_end) / 2.0
    apt_y = float(rwy_y)

    return {
        "rwy_y": rwy_y,
        "rwy_start": rwy_start,
        "rwy_end": rwy_end,
        "thr_x": thr_x,
        "apt_x": apt_x,
        "apt_y": apt_y,
        "rwy_len": rwy_len,
    }


# =======================
# ILS beam (localizer-like)
# =======================

def approach_axis_deg():
    """
    The beam extends outward from the threshold into the approach region.
    For RWY09 (inbound heading 090), the approach region is to the west.
    We model the beam axis pointing FROM threshold outward into approach,
    i.e. along the reciprocal heading (RWY_HDG + 180).
    """
    return wrap_deg(RWY_HDG + 180.0)


def loc_frame():
    """
    Build unit vectors in real coordinate orientation:
    - x positive right/east
    - y positive down/south, matching screen coordinates
    - heading convention: 0 up/north, 90 right/east
    """
    axis = math.radians(approach_axis_deg())
    ux = math.sin(axis)
    uy = -math.cos(axis)

    # normal / cross-track axis
    nx = -uy
    ny = ux
    return ux, uy, nx, ny


def beam_coords(a, ap):
    """
    Return along-track and cross-track distance in NM relative to the threshold
    and approach axis.

    along_nm > 0 means the aircraft is in the approach half-plane in front of
    the threshold.
    """
    ox = ap["thr_x"]
    oy = ap["rwy_y"]
    ux, uy, nx, ny = loc_frame()

    dx_nm, dy_nm = xy_to_nm_delta(ox, oy, a.x, a.y)

    along_nm = dx_nm * ux + dy_nm * uy
    cross_nm = dx_nm * nx + dy_nm * ny
    return along_nm, cross_nm


def in_loc_beam(a, ap):
    """
    Beam as a wedge: abs(cross) <= tan(half_angle) * along, with along > 0.
    This is a pure ±10° wedge from the threshold outward.
    """
    along_nm, cross_nm = beam_coords(a, ap)
    if along_nm <= 0:
        return False
    limit_nm = math.tan(math.radians(BEAM_HALF_ANGLE_DEG)) * along_nm
    return abs(cross_nm) <= limit_nm


def dme_nm_from_threshold(a, ap):
    """
    Use along-track distance along the approach axis as DME for gating and markers.
    This matches the 5 NM / 10 NM dots on centerline outward from threshold.
    """
    along_nm, _ = beam_coords(a, ap)
    if along_nm <= 0:
        return float("inf")
    return along_nm


# =======================
# H/O eligibility based on real-ish logic
# =======================

def eligible_for_handoff(a, ap):
    """
    H/O is allowed if:
    - localizer was captured at the 10 NM gate
    - still inside the beam
    - DME window 10 -> 5 NM
    - altitude < 4000 ft
    - speed irrelevant
    """
    dme = dme_nm_from_threshold(a, ap)
    return (
        a.loc_captured
        and in_loc_beam(a, ap)
        and HO_MIN_NM <= dme <= HO_MAX_NM
        and a.alt_ft < HO_ALT_MAX_FT
    )


# =======================
# Spawn logic (safe)
# =======================

def spawn_safe(counter, w, h, ap, aircraft, now):
    for _ in range(SPAWN_MAX_TRIES):
        edge = random.choice(["N", "S", "W", "E"])
        if edge == "N":
            x, y = random.randint(2, w - 3), 1
        elif edge == "S":
            x, y = random.randint(2, w - 3), h - 2
        elif edge == "W":
            x, y = 1, random.randint(2, h - 3)
        else:
            x, y = w - 2, random.randint(2, h - 3)

        # Real NM distance, not cell distance.
        if any(distance_xy_nm(a.x, a.y, x, y) < SPAWN_MIN_DIST_NM for a in aircraft):
            continue

        hdg = bearing_deg(x, y, ap["apt_x"], ap["apt_y"]) + random.uniform(-15, 15)
        hdg = wrap_deg(hdg)

        cs = f"SE{100 + counter:03d}"
        return Aircraft(cs, x, y, hdg, now)

    return None


# =======================
# Command parsing
# =======================

def parse_int(s):
    try:
        return int(s)
    except Exception:
        return None


def find_aircraft_index(aircraft, callsign_upper):
    for i, a in enumerate(aircraft):
        if a.callsign.upper() == callsign_upper:
            return i
    return None


def handle_command(line, aircraft, focus_idx):
    """
    Commands:
      ho                         (handoff focused aircraft if eligible)
      <CS> hdg <0-359>           (or without CS uses focus)
      <CS> alt <feet>
      <CS> spd <knots 160..250>
      help | list
    """
    parts = line.strip().split()
    if not parts:
        return True, "", focus_idx, None

    c0 = parts[0].lower()

    if c0 in ("help", "?"):
        msg = (
            "Commands: ho | [CS] hdg 090 | [CS] alt 3500 | [CS] spd 160..250 | list | help. "
            "TAB cycles focus. H/O prompts when eligible (10->5 NM in beam)."
        )
        return True, msg, focus_idx, None

    if c0 == "list":
        if not aircraft:
            return True, "No traffic.", focus_idx, None
        s = " | ".join([f"{a.callsign} hdg{int(a.hdg):03d} spd{int(a.spd_kt)} alt{int(a.alt_ft)}"
                        for a in aircraft[:12]])
        return True, s, focus_idx, None

    # 'ho' alone = focused
    if c0 == "ho":
        if not aircraft:
            return False, "No aircraft to hand over.", focus_idx, None
        return True, f"{aircraft[focus_idx].callsign} H/O requested", focus_idx, aircraft[focus_idx].callsign

    # callsign optional: if first token matches callsign
    target_idx = None
    rest = parts

    maybe_cs = parts[0].upper()
    i = find_aircraft_index(aircraft, maybe_cs)
    if i is not None:
        target_idx = i
        rest = parts[1:]
        focus_idx = i
    else:
        if not aircraft:
            return False, "No aircraft to control.", focus_idx, None
        target_idx = focus_idx
        rest = parts

    if not rest:
        return False, "Missing command (try help).", focus_idx, None

    op = rest[0].lower()
    arg = rest[1] if len(rest) > 1 else None

    a = aircraft[target_idx]

    if op in ("hdg", "heading"):
        v = parse_int(arg) if arg else None
        if v is None or not (0 <= v <= 359):
            return False, "Usage: hdg 0..359", focus_idx, None
        a.t_hdg = float(v)
        return True, f"{a.callsign} heading {v:03d}", focus_idx, None

    if op in ("alt", "climb", "descend"):
        v = parse_int(arg) if arg else None
        if v is None or not (0 <= v <= 45000):
            return False, "Usage: alt 0..45000", focus_idx, None
        a.t_alt_ft = float(v)
        return True, f"{a.callsign} altitude {v} ft", focus_idx, None

    if op in ("spd", "speed"):
        v = parse_int(arg) if arg else None
        if v is None:
            return False, "Usage: spd 160..250", focus_idx, None
        v = int(clamp(v, SPD_MIN_KT, SPD_MAX_KT))
        a.t_spd_kt = float(v)
        return True, f"{a.callsign} speed {v} kt", focus_idx, None

    return False, "Unknown command (try help).", focus_idx, None


# =======================
# Main loop
# =======================

def main(stdscr):
    # --- curses setup ---
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(C_SCOPE, curses.COLOR_CYAN,   -1)
    curses.init_pair(C_PLANE, curses.COLOR_WHITE,  -1)
    curses.init_pair(C_FOCUS, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_WARN,  curses.COLOR_RED,    -1)
    curses.init_pair(C_TEXT,  curses.COLOR_GREEN,  -1)
    curses.init_pair(C_RWY,   curses.COLOR_BLUE,   -1)
    curses.init_pair(C_HO,    curses.COLOR_YELLOW, -1)

    show_splash_curses(stdscr)

    aircraft = []
    focus_idx = 0
    counter = 0

    score = 0
    tower_handoffs = 0

    cmd = ""
    info = "Scaled NM geometry enabled. First aircraft spawns immediately."
    last_info_t = time.time()

    now = time.time()
    last_spawn = now - SPAWN_INTERVAL  # immediate first spawn
    last_t = now
    last_penalty_t = -1e9

    while True:
        now = time.time()
        dt = min(now - last_t, DT_CAP)
        last_t = now

        rows, cols = stdscr.getmaxyx()
        scope_h = rows - 4
        scope_w = cols - 1

        if scope_h < 12 or scope_w < 60:
            stdscr.erase()
            try:
                stdscr.addstr(0, 0, "Terminal too small. Resize larger.")
            except curses.error:
                pass
            stdscr.refresh()
            time.sleep(0.2)
            continue

        ap = build_airport(scope_w, scope_h)

        # -------- input --------
        ch = stdscr.getch()
        if ch != -1:
            if ch in (ord('q'), ord('Q')) and not cmd:
                break
            elif ch == 9 and aircraft:  # TAB
                focus_idx = (focus_idx + 1) % len(aircraft)
            elif ch in (10, 13):  # ENTER
                line = cmd.strip()
                cmd = ""
                if line:
                    ok, msg, focus_idx, ho_cs = handle_command(line, aircraft, focus_idx)
                    if msg:
                        info = msg
                        last_info_t = time.time()

                    if ho_cs:
                        a = next((x for x in aircraft if x.callsign == ho_cs), None)
                        if a and eligible_for_handoff(a, ap):
                            aircraft = [x for x in aircraft if x.callsign != ho_cs]
                            tower_handoffs += 1
                            score += 25
                            info = f"{ho_cs} handed to TWR ✅"
                            last_info_t = time.time()
                            focus_idx = 0
                        else:
                            info = f"{ho_cs} not eligible (must be beam-captured at 10 NM and in 10->5 NM window, alt<4000)."
                            last_info_t = time.time()

            elif ch == 27:  # ESC clears line
                cmd = ""
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                cmd = cmd[:-1]
            else:
                if 32 <= ch <= 126:
                    cmd += chr(ch)

        # -------- spawn --------
        if (now - last_spawn) >= SPAWN_INTERVAL and len(aircraft) < MAX_AIRCRAFT:
            counter += 1
            a = spawn_safe(counter, scope_w, scope_h, ap, aircraft, now)
            if a:
                aircraft.append(a)
                info = f"{a.callsign} entered."
            else:
                info = "Spawn skipped (no safe position)."
            last_info_t = time.time()
            last_spawn = now

        # -------- update motion --------
        for a in aircraft:
            # turn shortest-way
            diff = shortest_turn(a.hdg, a.t_hdg)
            a.hdg = wrap_deg(a.hdg + clamp(diff, -TURN_RATE_DPS * dt, TURN_RATE_DPS * dt))

            # altitude
            diff_alt = a.t_alt_ft - a.alt_ft
            a.alt_ft += clamp(diff_alt, -CLIMB_RATE_FTPS * dt, CLIMB_RATE_FTPS * dt)

            # speed
            diff_spd = a.t_spd_kt - a.spd_kt
            a.spd_kt += clamp(diff_spd, -SPD_SLEW_KT_PER_S * dt, SPD_SLEW_KT_PER_S * dt)
            a.spd_kt = clamp(a.spd_kt, SPD_MIN_KT, SPD_MAX_KT)

            # Move in real NM space, then convert to terminal-display cells.
            spd_nm = kt_to_nm_per_sec(a.spd_kt)
            r = math.radians(a.hdg)
            dx_nm = math.sin(r) * spd_nm * dt
            dy_nm = -math.cos(r) * spd_nm * dt

            a.x += dx_nm / NM_PER_COL
            a.y += dy_nm / NM_PER_ROW

        # remove aircraft leaving sector (no penalty)
        aircraft = [a for a in aircraft if -2 < a.x < scope_w + 2 and -2 < a.y < scope_h + 2]
        if aircraft:
            focus_idx = int(clamp(focus_idx, 0, len(aircraft) - 1))
        else:
            focus_idx = 0

        # -------- ILS capture at 10 NM gate --------
        for a in aircraft:
            dme = dme_nm_from_threshold(a, ap)

            if not a.gate10_seen and dme <= LOC_CAPTURE_GATE_NM:
                # first time entering <=10 NM region => capture or fail
                a.gate10_seen = True
                a.loc_captured = in_loc_beam(a, ap)

            # If it goes far back outside gate, reset (optional realism)
            if dme > LOC_CAPTURE_GATE_NM + 0.5:
                a.gate10_seen = False
                a.loc_captured = False

        # -------- separation (penalty only) --------
        for a in aircraft:
            a.warn = False

        loss_pairs = []
        for i in range(len(aircraft)):
            for j in range(i + 1, len(aircraft)):
                a, b = aircraft[i], aircraft[j]
                dist_nm = distance_nm(a, b)
                alt_diff = abs(a.alt_ft - b.alt_ft)

                if dist_nm < WARN_DIST_NM and alt_diff < ALT_WARN_FT:
                    a.warn = True
                    b.warn = True

                if dist_nm < LOSS_DIST_NM and alt_diff < ALT_LOSS_FT:
                    loss_pairs.append((a, b))

        if loss_pairs:
            youngest = min(min(now - p[0].spawn_t, now - p[1].spawn_t) for p in loss_pairs)
            if youngest < SPAWN_GRACE_S:
                info = f"Loss-of-sep (spawn grace {SPAWN_GRACE_S:.0f}s): no penalty."
                last_info_t = time.time()
            else:
                if (now - last_penalty_t) >= LOSS_COOLDOWN_S:
                    score = max(0, score - LOSS_PENALTY)
                    info = f"LOSS OF SEP: -{LOSS_PENALTY} score"
                    last_info_t = time.time()
                    last_penalty_t = now

        # -------- H/O PROMPT --------
        if aircraft:
            foc = aircraft[focus_idx]
            eligible = eligible_for_handoff(foc, ap)
            if eligible and not foc.ho_eligible_last:
                info = f"{foc.callsign} READY FOR H/O — type 'ho' and Enter"
                last_info_t = time.time()
            foc.ho_eligible_last = eligible

        # -------- draw --------
        stdscr.erase()
        draw_box(stdscr, 0, 0, scope_h - 1, scope_w - 1, curses.A_BOLD | curses.color_pair(C_SCOPE))

        # title
        title = (f" HEADLESS ATC — RWY {ACTIVE_RUNWAY} | Score {score} | Tower H/O {tower_handoffs} "
                 f"| Spawn {SPAWN_INTERVAL:.0f}s | Max {MAX_AIRCRAFT} | ILS beam ±{int(BEAM_HALF_ANGLE_DEG)}° "
                 f"| Scale col/row {NM_PER_COL:.2f}/{NM_PER_ROW:.2f} NM ")
        try:
            stdscr.addstr(0, max(1, (scope_w - len(title)) // 2), title,
                          curses.A_BOLD | curses.color_pair(C_SCOPE))
        except curses.error:
            pass

        # runway
        rwy_attr = curses.A_BOLD | curses.color_pair(C_RWY)
        ry = ap["rwy_y"]
        xs = ap["rwy_start"]
        xe = ap["rwy_end"]
        thr = ap["thr_x"]

        try:
            for x in range(xs, xe + 1):
                stdscr.addch(ry, x, "=", rwy_attr)
            stdscr.addch(ry, thr, "[", rwy_attr)
            stdscr.addch(ry, xe, "]", rwy_attr)

            label_y = ry - 1 if ry - 1 > 0 else ry + 1
            stdscr.addstr(label_y, clamp(thr, 1, scope_w - 4), "09", rwy_attr)
            stdscr.addstr(label_y, clamp(xe - 1, 1, scope_w - 4), "27", rwy_attr)
        except curses.error:
            pass

        # 5 NM / 10 NM markers from threshold on centerline outward into approach.
        # For RWY09 this is west/left, so use NM_PER_COL for horizontal drawing.
        marker_attr = curses.color_pair(C_TEXT)
        for nm in (10, 5):
            xm = thr - int(round(nm / NM_PER_COL))
            if 1 < xm < scope_w - 2:
                try:
                    stdscr.addch(ry, xm, ".", marker_attr)
                    txt = f"{nm}nm"
                    ly = ry - 1 if ry - 1 > 0 else ry + 1
                    lx = clamp(xm + 2, 1, scope_w - 1 - len(txt))
                    stdscr.addstr(ly, lx, txt, marker_attr)
                except curses.error:
                    pass

        # aircraft with two-line labels
        for i, a in enumerate(aircraft):
            x = int(round(a.x))
            y = int(round(a.y))
            if not (1 <= x < scope_w - 1 and 1 <= y < scope_h - 1):
                continue

            is_eligible = eligible_for_handoff(a, ap)
            col = curses.color_pair(C_FOCUS if i == focus_idx else C_PLANE)
            if a.warn:
                col = curses.color_pair(C_WARN)
            if is_eligible:
                col = curses.color_pair(C_HO)

            attr = col | (curses.A_BOLD if (i == focus_idx or is_eligible) else 0)

            try:
                stdscr.addch(y, x, heading_glyph(a.hdg), attr)
            except curses.error:
                pass

            dme = dme_nm_from_threshold(a, ap)
            tag = " HO!" if is_eligible else ""
            cap = " CAP" if a.loc_captured else ""
            line1 = f"{a.callsign} hdg{int(a.hdg):03d} spd{int(a.spd_kt):3d}kt"
            line2 = f"alt{int(a.alt_ft):5d}ft dme{dme:4.1f}nm{cap}{tag}"

            # label placement: try right side, else left
            maxlen = max(len(line1), len(line2))
            if x < scope_w // 2:
                lx = int(clamp(x + 2, 1, scope_w - 2 - maxlen))
            else:
                lx = int(clamp(x - 2 - maxlen, 1, scope_w - 2 - maxlen))

            ly1 = y
            ly2 = y + 1
            if ly2 > scope_h - 2:
                ly2 = y - 1
                ly1 = y - 2
            if ly1 < 1:
                ly1 = 1
                ly2 = 2

            try:
                stdscr.addstr(ly1, lx, line1, attr)
                stdscr.addstr(ly2, lx, line2, attr)
            except curses.error:
                pass

        # bottom UI
        try:
            focus_cs = aircraft[focus_idx].callsign if aircraft else "-"
            status = (
                f"Keys: TAB focus | ENTER submit | ESC clear | q quit  ||  "
                f"Focus:{focus_cs} | 0°=UP 90°=RIGHT 180°=DOWN 270°=LEFT | "
                f"Turn:180°/min | V/S:1200ft/min | SPD:160..250kt | "
                f"H/O: captured @10nm, window 10->5nm, alt<4000"
            )
            stdscr.addstr(rows - 3, 0, status[:cols - 1], curses.color_pair(C_TEXT))
            stdscr.addstr(rows - 2, 0, f"CMD> {cmd}"[:cols - 1], curses.A_BOLD)
            stdscr.addstr(
                rows - 1, 0,
                (info if (now - last_info_t) < 7 else "Type 'help' for commands.")[:cols - 1],
                curses.color_pair(C_TEXT)
            )
        except curses.error:
            pass

        stdscr.noutrefresh()
        curses.doupdate()
        time.sleep(FRAME_SLEEP)


# =========================
# Entrypoint
# =========================

if __name__ == "__main__":
    curses.wrapper(main)
