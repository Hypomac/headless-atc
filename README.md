# Headless ATC

A terminal-first air traffic control simulator focused on logic, timing, and operational decision-making.

Named for its deployment model rather than its interface, **Headless ATC** is designed to run happily on a headless Linux server. Players can connect remotely over SSH or run the simulator locally in their terminal.

Inspired by classic radar-style ATC games, the simulator models realistic aircraft performance, continuous separation monitoring, and procedural control. Every clearance, heading, altitude change, and handoff is your responsibility.

## Philosophy

The simulation is authoritative. The client reports the current state—it never invents it.

No hidden automation. No magical shortcuts. Just headings, altitudes, speeds, separation minima, and the constant challenge of keeping traffic flowing safely.

The terminal isn't a compromise. It's a natural environment for a long-running simulation that can run locally or on a remote headless server. Tools like tmux fit naturally into this workflow, allowing the simulation to run independently from the terminal session used to interact with it.

If you enjoy aviation, Unix tools, simulations, and systems thinking where good decisions matter more than flashy graphics, you're in the right place.

## Features

- Configurable climb, descent, and speed limits.
- Continuous lateral and vertical separation monitoring.
- Instrument Landing System (ILS) localizer capture logic.
- Realistic handoff window to tower.
- Dynamic aircraft spawning with fairness checks.
- Multi-aircraft command handling by callsign or selected aircraft.
- Modular architecture with separated simulation, rendering, airport, geometry, and command processing.
- Terminal interface built with Python's built-in curses library.

## Requirements

- Python 3.8 or newer
- Linux or macOS terminal with curses
- Windows users should use WSL or install windows-curses

No external Python packages are required.

## Installation

```bash
git clone https://github.com/hypomac/headless-atc.git
cd headless-atc
python3 main.py
```
## Quick Start

Launch the simulator:
```
python3 main.py
```
- Press any key on the splash screen.
- Aircraft will begin entering your airspace.
- Select aircraft and issue commands.
- Guide arrivals safely toward the runway.
- Hand aircraft to tower when they become eligible.

## Controls
### Keyboard
|Key|Action|
|TAB|Cycle selected aircraft|
|ENTER|Execute command|
|ESC|Clear current command|
|Q|Quit simulator|

## Commands
|Command|Description|
|---|---|
|`hdg <heading>`|Assign heading|
|`<CALLSIGN> hdg <heading>`|Assign heading to a specific aircraft|
|`alt <feet>`|Assign altitude|
|`<CALLSIGN> alt <feet>`|Assign altitude to a specific aircraft|
|`spd <knots>`|Assign speed|
|`<CALLSIGN> spd <knots>`|Assign speed to a specific aircraft|
|`ho`|Request tower handoff for selected aircraft|
|`list`|Show all active aircraft|
|`help`|Display command summary|

## Gameplay

Your objective is to safely sequence aircraft onto the runway while maintaining separation.

Successful controllers must:

Prevent loss of separation.
Intercept aircraft onto the ILS localizer.
Manage speed and altitude.
Hand aircraft to tower during the correct approach window.

Poor timing or incorrect instructions can quickly turn a manageable traffic flow into a developing conflict.

Scoring
Successful tower handoff awards points.
Separation violations reduce your score.
Spawn protection prevents unfair penalties immediately after aircraft enter the airspace.

## Configuration

Gameplay parameters are centralized in `config.py`.

Values such as:

- Spawn interval
- Maximum aircraft
- Turn rate
- Climb and descent rates
- Speed limits
- Separation minima
- Handoff limits

can be adjusted without modifying the simulation logic.

## Deployment

Headless ATC can run locally or on a remote Linux server. The simulation does not require a graphical environment, making it suitable for headless machines and terminal-based workflows.

## Project Structure

```text

main.py            Application entry point
simulation.py      Simulation engine and game state
renderer.py        Terminal rendering
commands.py        Command parsing and execution
airport.py         Airport layout and runway logic
aircraft.py        Aircraft model
geometry.py        Navigation and geometry helpers
callsigns.py       Callsign generation
config.py          Game configuration
```

The project follows a modular design where each component has a clearly defined responsibility.

## Architecture

The application is organized into independent modules:

- `main.py` — Starts and coordinates the application.
- `Simulation` — Updates aircraft movement and game state.
- `Renderer` — Draws the terminal interface.
- `Airport` — Defines airport geometry and runway information.
- `Aircraft` — Represents aircraft state and performance.
- `Geometry` — Navigation mathematics and distance calculations.
- `Commands` — Parses and executes controller input.
- `Configuration` — Centralized gameplay constants.

This separation makes the simulator easier to maintain, extend, and test.

## License

Released under the MIT License.

See the LICENSE file for details.

## Credits

Created by Håkon Furdal

Developed with assistance from GitHub Copilot and ChatGPT.

The design philosophy, architecture, and gameplay decisions remain human-driven, with AI serving as a development assistant.

## Contributing

Bug reports, suggestions, and pull requests are welcome.

## Inspiration

Inspired by classic radar-style ATC simulators while focusing on controller decision-making, timing, and aircraft separation rather than graphical complexity.

Enjoy the quiet stress. ✈️

