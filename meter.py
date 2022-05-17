#!/usr/bin/env python3
"""

(C) 2022 Wieger Opmeer

MIT License, see the LICENSE file.

Inspired by https://github.com/Mob-Barley/noise_level_protocol/

"""

import csv
from datetime import datetime, time, timedelta, timezone
import os
from pathlib import Path
import subprocess
import sys
from time import sleep

# haven't tested with anything older
MIN_PYTHON = (3, 9)
assert sys.version_info >= MIN_PYTHON, "Python %s.%s or later is required." % MIN_PYTHON

# other constants
AUDIOCARD = "1"
AUDIODEV = "hw:1,0"
BASEDIR = Path.home() / "lawaai"
RECORDING_START = time(22, 0, 0)
RECORDING_END = time(3, 0, 0)
SAVING_PK_DB = -15.0
SAVING_RMS_DB = -45.0
SOX_CMD = "/usr/bin/sox -q -t alsa -d {filename} gain 20 stats trim 0 {runtime}"
# SOX_CMD =  'AUDIODEV={AUDIODEV} sox -q -t alsa -d {filename} gain 20 stats trim 0 {runtime}'

# todo
# change offset here
offset_peak = 45.0
offset_rsm = 40.0
header_csv = ("datetime", "max db", "rms db", "saved")

# do not touch
csv_path = BASEDIR / "csv"
ogg_path = BASEDIR / "ogg"
a_minute = timedelta(minutes=1)
sox_env = os.environ.copy()
sox_env["AUDIODEV"] = AUDIODEV


def time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


try:
    # in case something got stuck
    subprocess.run("pkill -9 sox", shell=True)
    sleep(0.1)
    # max out the volume on our mike
    subprocess.run(f"amixer -c {AUDIOCARD} sset Mic 100%", shell=True)
    sleep(0.1)

    while True:

        # determine filename for current minute
        now = datetime.now(timezone.utc).astimezone()
        # todo better names
        path = ogg_path / now.date().isoformat()
        if not path.exists():
            path.mkdir()
        this_minute = now.replace(tzinfo=None).isoformat(timespec="minutes")
        ogg_file = path.joinpath(f"{this_minute}.ogg")

        # calculcate seconds till top of next minute
        next_minute = (now + a_minute).replace(microsecond=0, second=0)
        runtime = (next_minute - now).total_seconds()

        cmd = SOX_CMD.format(filename=ogg_file, runtime=runtime).split()
        print(cmd)

        res = subprocess.run(
            cmd, check=True, capture_output=True, universal_newlines=True, env=sox_env
        )

        # extract peak and rms dB levels
        for l in res.stderr.splitlines():
            if l.startswith("Pk lev dB"):
                pklvldb = l.split(" ")[-1]
            elif l.startswith("RMS lev dB"):
                rmslvldb = l.split(" ")[-1]

        assert pklvldb
        assert rmslvldb

        pklvldb = float(pklvldb)
        rmslvldb = float(rmslvldb)
        saved = True

        # if minute not within saving window
        # and pk lvl db < saving level
        if (
            not time_in_range(RECORDING_START, RECORDING_END, now.time())
            and pklvldb < SAVING_PK_DB
            and rmslvldb < SAVING_RMS_DB
        ):
            # rm file
            ogg_file.unlink()
            saved = False

        # append stats to csv file
        # ('datetime', 'max db', 'rms db', 'saved')
        data_csv = (this_minute, pklvldb, rmslvldb, saved)
        print(data_csv)
        csv_file = csv_path.joinpath(now.date().isoformat() + ".csv")
        csv_file_already_exists = csv_file.exists()
        with csv_file.open("a", newline="") as f:
            writer = csv.writer(f)
            if not csv_file_already_exists:
                writer.writerow(header_csv)
            writer.writerow(data_csv)

except KeyboardInterrupt:
    subprocess.run("pkill -9 sox", shell=True)
    print("got ctrl-c!")
