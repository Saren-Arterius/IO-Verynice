#!/usr/bin/python3
from threading import Thread, RLock, enumerate as all_threads
from subprocess import check_output, call, CalledProcessError
from time import sleep
from os.path import realpath, dirname, join
from os import geteuid
from json import loads, dumps
import re
import signal

from jsbeautifier import beautify

from pwd import getpwnam

RUN = True


class IOVeryNice(Thread):
    default_settings = {
        "processes": [
            {
                "process_name": "dropbox",
                "grep_string": None,
                "owner": "saren",
                "class": "idle"
            },
            {
                "process_name": "tar",
                "grep_string": None,
                "owner": "root",
                "class": "idle"
            },
        ],
        "classes": {
            "low": {
                "prio_class": 2,
                "prio_data": 7
            },
            "idle": {
                "prio_class": 3,
                "prio_data": 0
            },
            "high": {
                "prio_class": 2,
                "prio_data": 0
            },
            "very_high": {
                "prio_class": 1,
                "prio_data": 4
            },
            "extreme_high": {
                "prio_class": 1,
                "prio_data": 0
            },
            "default": {
                "prio_class": 0,
                "prio_data": 0
            }
        },
        "other": {
            "check_interval": 10
        }
    }

    def __init__(self, process_name, grep_string, owner, prio_class, prio_data):
        Thread.__init__(self)
        valid = 0
        if process_name is not None and len(process_name):
            valid += 1
        self.process_name = process_name
        if grep_string is not None and len(grep_string):
            valid += 1
        self.grep_string = grep_string
        if owner is not None and getpwnam(owner):
            valid += 1
        assert valid >= 2
        self.owner = owner
        assert prio_class in range(0, 4)
        self.prio_class = prio_class
        assert prio_data in range(0, 8)
        self.prio_data = prio_data
        self.pids = None
        self.EXIT_FLAG = False

    def run(self):
        global settings
        while True:
            if self.EXIT_FLAG:
                return
            new_pids = self.get_pids()
            if new_pids != self.pids and isinstance(new_pids, list):
                for pid in new_pids:
                    call_args = ["ionice", "-c", str(self.prio_class)]
                    if self.prio_class == 1 or self.prio_class == 2:
                        call_args += ["-n", str(self.prio_data)]
                    call_args += ["-p", str(pid)]
                    call(call_args)
            self.pids = new_pids
            sleep(settings["other"]["check_interval"])

    def exit(self):
        print("Exiting thread {0}...".format(self))
        lock = RLock()
        lock.acquire()
        self.EXIT_FLAG = True
        if isinstance(self.pids, list):
            for pid in self.pids:
                call_args = ["ionice", "-c", "0", "-p", str(pid)]
                call(call_args)
        lock.release()

    def get_pids(self):
        pids = []
        try:
            if self.owner is not None:
                for line in check_output(["ps", "-Lf", "-U", self.owner]).decode().splitlines():
                    result = re.split("\s+", line)
                    if result[0] == "UID":
                        continue
                    if self.process_name in result[9]:
                        if self.grep_string is not None and self.grep_string not in "".join(result[9:]):
                            continue
                        pids.append(int(result[3]))
            else:
                for line in check_output(["ps", "aux", "-L"]).decode().splitlines():
                    result = re.split("\s+", line)
                    if self.process_name in result[12]:
                        if self.grep_string is not None and self.grep_string not in "".join(result[12:]):
                            continue
                        pids.append(int(result[2]))
            return pids
        except CalledProcessError:
            return


def handle(a, b):
    global RUN
    print("Received SIGTERM, terminating all IOVeryNice threads...")
    for thread in all_threads():
        if isinstance(thread, IOVeryNice):
            thread.exit()
    RUN = False


def load_settings():
    settings_path = join(dirname(realpath(__file__)), "settings.json")
    try:
        settings = loads(open(settings_path).read())
        has_change = False
        for i, item in enumerate(settings["processes"]):
            for key, val in {"process_name": "input_process_name_here", "grep_string": "grep_string", "owner": None,
                             "class": "default"}.items():
                if key not in item:
                    settings["processes"][i][key] = val
                    has_change = True
        for item in settings["processes"]:
            if item["class"] not in settings["classes"]:
                settings[item["class"]] = settings["classes"]["default"].copy()
                has_change = True
        for prio_class, config in settings["classes"].items():
            if "prio_class" not in config or "prio_data" not in config or len(config) != 2:
                settings["classes"][prio_class].clear()
                settings["classes"][prio_class]["prio_class"] = settings["classes"]["default"]["prio_class"]
                settings["classes"][prio_class]["prio_data"] = settings["classes"]["default"]["prio_data"]
                has_change = True
        if has_change:
            open(settings_path, "w+").write(beautify(dumps(settings)))
    except FileNotFoundError or ValueError:
        settings = IOVeryNice.default_settings.copy()
        open(settings_path, "w+").write(beautify(dumps(settings)))
    return settings


if __name__ == "__main__":
    if geteuid() != 0:
        raise EnvironmentError("This program must be run as root.")
    settings = load_settings()
    for limiter in settings["processes"]:
        print("Started setting class {3} on {2}'s {0}({1})'s all pids...".format(limiter["process_name"],
                                                                                 limiter["grep_string"],
                                                                                 limiter["owner"], limiter["class"]))
        IOVeryNice(limiter["process_name"], limiter["grep_string"], limiter["owner"],
                   settings["classes"][limiter["class"]]["prio_class"],
                   settings["classes"][limiter["class"]]["prio_data"]).start()
    signal.signal(signal.SIGTERM, handle)
    while RUN:
        try:
            signal.pause()
        except KeyboardInterrupt:
            handle("", "")
    print("Stopping...")