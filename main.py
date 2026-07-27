
"""
Headless ATC

Main application entry point.

The main loop only connects:
- input
- simulation
- rendering
"""

import curses
import time

from airport import Airport
from simulation import Simulation
from api_client import APIClient
from renderer import Renderer
from user_config import get_controller_name, set_controller_name
from commands import handle_command
from config import GAME_VERSION



DT_CAP = 0.10
FRAME_SLEEP = 0.02



def game_loop(stdscr, controller_name):

    renderer = Renderer()

    renderer.setup(stdscr)

    renderer.splash(stdscr)


    rows, cols = stdscr.getmaxyx()


    airport = Airport(
        cols - 1,
        rows - 4
    )


    simulation = Simulation(
        airport
    )

    api = APIClient()

    if api.online:
        simulation.info = "API: online"
    else:
        simulation.info = "API: offline"


    command = ""


    last_time = time.time()



    while True:

        now = time.time()


        dt = min(
            now - last_time,
            DT_CAP
        )

        last_time = now



        # -------------------------
        # Keyboard
        # -------------------------

        ch = stdscr.getch()


        if ch in (
            ord("q"),
            ord("Q")
        ) and not command:

            result = api.submit_score(
                controller_name,
                simulation.score,
                simulation.handoffs,
                GAME_VERSION,
            )

            if result:
                simulation.info = "Score submitted."

            else:
                simulation.info = "Score not submitted."

            break



        elif ch == 9:

            simulation.focus_next()



        elif ch in (
            10,
            13
        ):

            if command:

                ok, msg, focus_idx, ho = (
                    handle_command(
                        command,
                        simulation.aircraft,
                        simulation.focus_idx
                    )
                )


                command = ""


                if msg:

                    simulation.info = msg



                if ho:

                    simulation.handoff(ho)



        elif ch == 27:

            command = ""



        elif ch in (
            curses.KEY_BACKSPACE,
            127,
            8
        ):

            command = command[:-1]



        else:

            if 32 <= ch <= 126:

                command += chr(ch)



        # -------------------------
        # Simulation
        # -------------------------

        simulation.update(
            dt,
            now
        )
        
        simulation.normalize_focus()



        # -------------------------
        # Render
        # -------------------------

        renderer.draw(
            stdscr,
            simulation,
            simulation.focus_idx
        )


        # Command line

        try:

            stdscr.addstr(
                rows-1,
                0,
                f"CMD> {command}"[:cols-1]
            )

            stdscr.refresh()


        except curses.error:

            pass



        time.sleep(
            FRAME_SLEEP
        )




if __name__ == "__main__":

    controller_name = get_controller_name()

    if not controller_name:
        controller_name = input("controller name: ").strip()

        if controller_name:
            set_controller_name(controller_name)

    curses.wrapper(
        lambda stdscr: game_loop(stdscr, controller_name)
    )
