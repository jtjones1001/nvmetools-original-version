# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Functions and constants for converting values."""

import ctypes
import datetime
import logging
import os

import numpy

from nvmetools.support.log import log

BYTES_IN_KB = 1e3
BYTES_IN_MB = 1e6
BYTES_IN_GB = 1e9
BYTES_IN_TB = 1e12

BYTES_IN_KIB = 1024
BYTES_IN_MIB = 1024 * 1024
BYTES_IN_GIB = 1024 * 1024 * 1024
BYTES_IN_TIB = 1024 * 1024 * 1024 * 1024

KIB_TO_GB = 1024 / 1000 * 1000 * 1000

GB_IN_TB = 1e3

NS_IN_SEC = 1e9
NS_IN_MS = 1e6
NS_IN_US = 1e3

US_IN_MS = 1e3

MS_IN_SEC = 1e3
MS_IN_MIN = 60000
MS_IN_HR = 3600 * MS_IN_SEC

SEC_IN_MIN = 60


class IllegalIoStringError(Exception):
    """Custom exception to flag illegal IO string."""

    def __init__(self) -> None:
        """Add error code and indicate custom exception then propagate."""
        self.code = 58
        self.nvmetools = True
        super().__init__("Illegal IO string")


def as_datetime(timestamp: str) -> datetime:
    """Convert timestamp into a date time string."""
    stamp = timestamp
    stamp = stamp.rstrip(" DST")
    return datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S.%f")


def as_io(description: str) -> dict:
    """Convert string into a dictionar of IO payload parameters."""
    try:
        io = {}

        fields = description.split(",")
        if len(fields) != 3:
            raise IllegalIoStringError

        io["pattern"] = fields[0].strip().lower()

        if fields[1].strip().find("QD") != 0:
            raise IllegalIoStringError
        io["depth"] = fields[1].strip()[2:]

        if fields[2].find("KiB") == -1:
            raise IllegalIoStringError
        io["size"] = str(int(fields[2].strip().replace("KiB", "")) * BYTES_IN_KIB)
        return io

    except Exception:
        raise IllegalIoStringError


def as_int(string_value: str) -> int:
    """Convert string to int, removes commas and units."""
    tmp_string = string_value.replace(",", "")
    if tmp_string.rfind(" ") != -1:
        tmp_string = tmp_string[: tmp_string.rfind(" ")]
    return int(tmp_string)


def as_float(string_value: str) -> float:
    """Convert string to float, removes commas and units."""
    tmp_string = string_value.replace(",", "")
    if tmp_string.rfind(" ") != -1:
        tmp_string = tmp_string[: tmp_string.rfind(" ")]
    return float(tmp_string)


def as_linear(elapsed_time: list[float], elapsed_progress: list[float]) -> float:
    """Convert time and progress series to linear coefficient."""
    # Pearson coefficient undefined for constant series so return 0 if
    # the progress doesn't change
    if elapsed_progress.count(elapsed_progress[0]) == len(elapsed_progress):
        return 0
    else:
        return numpy.corrcoef(elapsed_time, elapsed_progress)[0, 1]


def as_monotonic(elapsed_time: list[float]) -> str:
    """Convert time series to string indicating monotonicity."""
    diff_time = numpy.diff(elapsed_time)
    if numpy.all(diff_time <= 0) or numpy.all(diff_time >= 0):
        return "Monotonic"
    else:
        return "NOT Monotonic"


def as_nicedate(timedate: datetime) -> str:
    """Convert time to string with nice formatting."""
    return timedate.strftime("%B %d, %Y at %H:%M:%S")


def is_admin() -> bool:
    """Return boolean to indicate running with admin privilege."""
    try:
        return os.getuid() == 0
    except Exception:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0


def is_debug() -> bool:
    """Return boolean to indicate running in debug mode."""
    return log.handlers[0].level == logging.DEBUG
