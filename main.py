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
from renderer import Renderer

from commands import handle_command



DT_CAP = 0.10
FRAME_SLEEP = 0.02



def game_loop(stdscr):

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


        if ch != -1:


            if ch in (
                ord("q"),
                ord("Q")
            ) and not command:

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

                        simulation.handoff(
                            ho
                        )



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

    curses.wrapper(
        game_loop
    )
