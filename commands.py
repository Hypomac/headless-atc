"""
Command handling for Headless ATC.
"""


def parse_int(value):
    """
    Convert string to integer safely.
    """

    try:
        return int(value)
    except Exception:
        return None



def find_aircraft_index(aircraft, callsign_upper):
    """
    Find aircraft by callsign.
    """

    for i, a in enumerate(aircraft):
        if a.callsign.upper() == callsign_upper:
            return i

    return None



def handle_command(line, aircraft, focus_idx):
    """
    Process tower commands.

    Commands:

        ho

        [CS] hdg 090

        [CS] alt 3500

        [CS] spd 180

        list

        help

    Returns:

        ok,
        message,
        focus index,
        handoff callsign (or None)
    """

    parts = line.strip().split()

    if not parts:
        return True, "", focus_idx, None


    cmd = parts[0].lower()


    # -------------------------
    # Help
    # -------------------------

    if cmd in ("help", "?"):

        msg = (
            "Commands: ho | "
            "[CS] hdg 090 | "
            "[CS] alt 3500 | "
            "[CS] spd 160..250 | "
            "list | help"
        )

        return True, msg, focus_idx, None



    # -------------------------
    # List traffic
    # -------------------------

    if cmd == "list":

        if not aircraft:
            return True, "No traffic.", focus_idx, None


        text = " | ".join(
            [
                f"{a.callsign} "
                f"hdg{int(a.hdg):03d} "
                f"spd{int(a.spd_kt)} "
                f"alt{int(a.alt_ft)}"
                for a in aircraft[:12]
            ]
        )

        return True, text, focus_idx, None



    # -------------------------
    # Handoff
    # -------------------------

    if cmd == "ho":

        if not aircraft:
            return (
                False,
                "No aircraft to control.",
                focus_idx,
                None
            )


        return (
            True,
            f"{aircraft[focus_idx].callsign} H/O requested",
            focus_idx,
            aircraft[focus_idx].callsign
        )



    # -------------------------
    # Aircraft target
    # -------------------------

    target_idx = None

    rest = parts


    possible_cs = parts[0].upper()

    found = find_aircraft_index(
        aircraft,
        possible_cs
    )


    if found is not None:

        target_idx = found
        rest = parts[1:]
        focus_idx = found


    else:

        if not aircraft:
            return (
                False,
                "No aircraft to control.",
                focus_idx,
                None
            )

        target_idx = focus_idx



    if not rest:

        return (
            False,
            "Missing command.",
            focus_idx,
            None
        )


    operation = rest[0].lower()

    argument = (
        rest[1]
        if len(rest) > 1
        else None
    )


    a = aircraft[target_idx]



    # -------------------------
    # Heading
    # -------------------------

    if operation in ("hdg", "heading"):

        if a.handed_off:
            return (
                False,
                f"{a.callsign} already handed to TWR",
                focus_idx,
                None
            )

        value = parse_int(argument)

        if value is None or not (0 <= value <= 359):

            return (
                False,
                "Usage: hdg 0..359",
                focus_idx,
                None
            )


        a.t_hdg = float(value)


        return (
            True,
            f"{a.callsign} heading {value:03d}",
            focus_idx,
            None
        )



    # -------------------------
    # Altitude
    # -------------------------

    if operation in ("alt", "climb", "descend"):

        if a.handed_off:
            return (
                False,
                f"{a.callsign} already handed to TWR",
                focus_idx,
                None
            )

        value = parse_int(argument)

        if value is None or not (0 <= value <= 45000):

            return (
                False,
                "Usage: alt 0..45000",
                focus_idx,
                None
            )


        a.t_alt_ft = float(value)


        return (
            True,
            f"{a.callsign} altitude {value} ft",
            focus_idx,
            None
        )



    # -------------------------
    # Speed
    # -------------------------

    if operation in ("spd", "speed"):

        if a.handed_off:
            return (
                False,
                f"{a.callsign} already handed to TWR",
                focus_idx,
                None
            )

        value = parse_int(argument)


        if value is None:

            return (
                False,
                "Usage: spd 160..250",
                focus_idx,
                None
            )


        from config import SPD_MIN_KT, SPD_MAX_KT


        value = int(
            max(
                SPD_MIN_KT,
                min(
                    SPD_MAX_KT,
                    value
                )
            )
        )


        a.t_spd_kt = float(value)


        return (
            True,
            f"{a.callsign} speed {value} kt",
            focus_idx,
            None
        )



    return (
        False,
        "Unknown command (try help).",
        focus_idx,
        None
    )
