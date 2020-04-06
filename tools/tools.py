import time
import datetime


def _time_format(format_string):
    return datetime.datetime.now().strftime(format_string)


def _sleep(seconds=60):
    print(_time_format("%Y-%d-%m %H:%M:%S") + " | ", end="", flush=True)
    for _ in range(int(seconds)):
        time.sleep(1)
        print(">", end="", flush=True)
    print("")
    time.sleep(1)
