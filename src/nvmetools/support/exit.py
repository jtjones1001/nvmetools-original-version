# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Exception and constants for standardizing script exit."""

import sys

from nvmetools.support.log import log

USAGE_EXIT_CODE = 1
FAILURE_EXIT_CODE = 2
EXCEPTION_EXIT_CODE = 50


def exit_on_exception(e: Exception) -> None:
    """Log exceptions in a standard way and exit with an exception error code.

    The StopOnFailError exception occurs when a test fails with the stop on fail property
    set.  This exits the script with the standard failure code.

    Exceptions with the nvmetools attribute are specific to this package and have a
    unique error code that is returned.

    All other exceptions return the generic exception error code.

    Args:
      e (exception): The fatal exception that was raised
    """
    if e.__class__.__name__ == "StopOnFailError":
        e.code = FAILURE_EXIT_CODE
        log.error(f" STOP ON FAIL : {e.msg}")
        log.error("")
    elif not hasattr(e, "nvmetools"):
        e.code = EXCEPTION_EXIT_CODE
        log.header(f" FATAL ERROR : {e.code}", indent=False)
        log.exception("Unknown error.  Send developer details below and debug.log\n\n")
    else:
        log.header(f"FATAL ERROR : {e.code}", indent=False)
        log.error(e)

    sys.exit(e.code)
