"""
Headless ATC API client.

The game must remain fully playable if the API is unavailable.
All network errors are handled silently.
"""

import json
import urllib.request
import urllib.error

from config import (
    API_ENABLED,
    API_URL,
    API_TIMEOUT_S,
)


class APIClient:

    def __init__(self):

        self.online = False

        self.session_id = None
        self.token = None

        if API_ENABLED:
            self.start_session()


    def start_session(self):

        url = f"{API_URL}/api/session/start"

        request = urllib.request.Request(
            url,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "HeadlessATC/0.1.0"
            },
            data=b"{}"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=API_TIMEOUT_S
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

                self.session_id = data["session_id"]
                self.token = data["token"]

                self.online = True

                return True

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
            ValueError,
            KeyError,
        ):

            self.online = False
            self.session_id = None
            self.token = None

            return False

    def submit_score(
        self,
        controller_name,
        score,
        aircraft_handled,
        game_version,
    ):

        if not self.online:
            return False


        url = f"{API_URL}/api/score"


        payload = {
            "session_id": self.session_id,
            "token": self.token,
            "controller_name": controller_name,
            "score": score,
            "aircraft_handled": aircraft_handled,
            "game_version": game_version,
        }


        request = urllib.request.Request(
            url,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "HeadlessATC/0.1.0"
            },
            data=json.dumps(payload).encode("utf-8")
        )


        try:

            with urllib.request.urlopen(
                request,
                timeout=API_TIMEOUT_S
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

                return data.get("accepted", False)


        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
            ValueError,
        ):

            return False

    def get_leaderboard(self):

        url = f"{API_URL}/api/leaderboard"

        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": "HeadlessATC/0.1.0"
            }
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=API_TIMEOUT_S
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

                return data


        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            OSError,
            ValueError,
        ):

            return []
