import random

AIRLINES = [
    "SAS",
    "NOZ",
    "KLM",
    "DHL",
    "BAW",
    "AFR",
]

#SUFFIXES = [
#    "A",
#    "B",
#    "K",
#    "L",
#    "M",
#]

def generate_callsign():
    airline = random.choice(AIRLINES)
    number = random.randint(10, 999)

    return f"{airline}{number}"
