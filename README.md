# Headless ATC

A terminal-based air traffic control simulator focused on logic, timing, and separation — not graphics.

**There is no radar screen. There is no mouse. There is only the airspace, the rules, and your decisions.**

Headless ATC is a CLI-first simulation inspired by classic radar-style ATC games, but deliberately implemented as a headless, deterministic system. Aircraft follow real constraints, separation rules apply unforgivingly, and every mistake is yours alone.

---

## Philosophy

> **Python owns the truth. The interface only reports what already happened.**

No hidden automation. No visual crutches. Just altitude, heading, speed, separation, and handoff at the right moment. The terminal is not a limitation — it's the point.

If you enjoy systems thinking, classic simulations, and the quiet stress of managing multiple aircraft with minimal feedback, you're in the right place.

---

## Features

- **Real-world physics**: Aircraft move in nautical-mile geometry with accurate turn rates (3°/sec), climb/descent rates (1,200 ft/min), and speed constraints (160–250 knots).
- **Separation rules**: Maintain minimum lateral (5 NM warning, 2.5 NM loss) and vertical (1,000 ft warning, 300 ft loss) separation. Violations cost points.
- **ILS localizer**: Aircraft must be captured in a realistic ±10° approach beam at the 10 NM gate (DME) to become handoff-eligible.
- **Handoff logic**: Hand aircraft to tower when they meet strict criteria (beam-captured, 10→5 NM window, altitude < 4,000 ft). Successful handoffs award points.
- **Dynamic spawning**: Aircraft spawn at the screen edges every 40 seconds (tunable), with fairness checks to avoid unsafe starting positions.
- **Terminal UI**: Real-time display of aircraft position, heading, speed, altitude, and DME distance. No external dependencies beyond Python's `curses`.

---

## Getting Started

### Requirements

- Python 3.7+
- `curses` (included on Linux/macOS; on Windows, use WSL or install `windows-curses`)

### Installation

```bash
git clone https://github.com/hypomac/headless-atc.git
cd headless-atc
python3 headless_atc.py
```

### Quick Start

1. **Run the simulator**: `python3 headless_atc.py`
2. **Read the splash screen**: Press any key to begin.
3. **Watch aircraft spawn**: They'll enter from the edges of your terminal.
4. **Issue commands** (see below).
5. **Goal**: Hand off approaching aircraft to tower before they leave your airspace. Score points for successful handoffs; lose points for separation violations.

---

## Controls & Commands

### Navigation

- **TAB**: Cycle focus between aircraft.
- **Type commands** and press **ENTER** to submit.
- **ESC**: Clear the input line.
- **q**: Quit the simulator.

### Command Reference

| Command | Example | Effect |
|---------|---------|--------|
| `hdg <0-359>` | `hdg 090` | Set heading of focused aircraft to 090°. |
| `<CS> hdg <0-359>` | `SE101 hdg 180` | Set heading of specific aircraft (by callsign). |
| `alt <feet>` | `alt 3500` | Set altitude target. |
| `<CS> alt <feet>` | `SE101 alt 2000` | Set altitude of specific aircraft. |
| `spd <knots>` | `spd 180` | Set speed (clamped to 160–250 kt). |
| `<CS> spd <knots>` | `SE101 spd 200` | Set speed of specific aircraft. |
| `ho` | `ho` | Request handoff of focused aircraft (if eligible). |
| `list` | `list` | Show all active aircraft. |
| `help` | `help` | Show command summary. |

### Heading Convention

- **0°** = North (up)
- **90°** = East (right)
- **180°** = South (down)
- **270°** = West (left)

---

## Gameplay

### The Goal

Guide approaching aircraft to the runway via the ILS localizer. Hand them off to tower when they meet strict criteria.

### Handoff Eligibility

An aircraft is ready for handoff when **all** of these are true:

1. **Localizer captured**: Aircraft was detected inside the ±10° approach beam at the 10 NM gate (DME).
2. **Still in beam**: Aircraft remains inside the beam cone.
3. **Correct altitude window**: Altitude < 4,000 ft.
4. **Correct distance window**: Distance from threshold is between 10 NM and 5 NM (the approach corridor).

When eligible, the aircraft tag will show **`HO!`** and the status bar will prompt you. Type `ho` to request the handoff.

### Scoring

- **+25 points** per successful handoff to tower.
- **−5 points** per loss of separation (triggered if two aircraft are closer than 2.5 NM AND less than 300 ft apart).
- **Spawn grace period**: No penalty for separation losses within 8 seconds of spawn (prevents unfair conflicts on entry).

### Display Legend

- **Aircraft symbol**: Heading glyph (^, >, v, <) matching the aircraft's direction.
- **Yellow highlight**: Focused aircraft.
- **Red**: Warning or loss of separation.
- **Yellow with `HO!`**: Ready for handoff.
- **`CAP`**: Localizer captured.
- **DME**: Distance in nautical miles from runway threshold.

---

## Configuration

Key parameters in the code (at the top of `headless_atc.py`):

```python
SPAWN_INTERVAL = 40.0        # Seconds between spawns
MAX_AIRCRAFT = 3             # Maximum active aircraft
BEAM_HALF_ANGLE_DEG = 10.0   # ILS beam half-width
HO_MIN_NM = 5.0              # Handoff distance window (min)
HO_MAX_NM = 10.0             # Handoff distance window (max)
HO_ALT_MAX_FT = 4000         # Handoff altitude limit
TURN_RATE_DPS = 3.0          # Degrees per second
CLIMB_RATE_FTPS = 20.0       # Feet per second
```

Adjust these to tune difficulty and gameplay feel.

---

## Architecture

- **Aircraft model** (`class Aircraft`): State representation — position, heading, altitude, speed, ILS capture flags.
- **Airport geometry** (`build_airport()`): Runway placement and centerline logic.
- **ILS beam** (`loc_frame()`, `beam_coords()`, `in_loc_beam()`): Localizer geometry and capture logic.
- **Physics** (`heading_glyph()`, `kt_to_nm_per_sec()`, `distance_xy_nm()`): Motion and distance calculations.
- **Separation logic**: Continuous checks for loss-of-separation; penalties applied with cooldown.
- **Terminal UI** (via `curses`): Real-time rendering of airspace, aircraft, runway, and status.

---

## Credits

**Created by**: Håkon Furdal  
**With assistance from**: GitHub Copilot  
**License**: MIT (see `LICENSE`)

The philosophy and design were crafted collaboratively: human vision and decision-making paired with AI-assisted implementation.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.

---

## Contributing

Found a bug? Have an idea for a feature? Feel free to open an issue or submit a pull request.

---

## Inspiration

Inspired by classic radar-style ATC simulators like *Radar Contact* and *Approach*, but stripped to the essentials: logic, timing, and the pure challenge of separation.

Enjoy the quiet stress. ✈️
