# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that checks the health of NVMe drive.

.. highlight:: none

Verifies the NVMe drive health by running the short self-test diagnostic, checking the SMART attributes for
errors and log page 6 for prior self-test failures.

Logs results to ~/Documents/nvme/<name> where <name> is the date and time the command was run or the run_id
if specified.  This directory contains a PDF test report and other data files.

The debug and verbose parameters enable additional logging and keeps additional files for the purpose of
debugging the script or device failure.  The full debug output is alway saved in the debug.log regardless of
these parameters.

.. note::
   This command must be run as Administrator on Windows OS.

Command Line Parameters
    --nvme, -n     Integer NVMe device number, can be found using listnvme.
    --pdf, -p      Flag to display PDF report in a new window when the check completes.
    --run_id, -i   String to use for the results directory name.
    --verbose, -V  Flag for additional logging, verbose logging.
    --debug, -D    Flag for maximum logging for debugging.

**Return Value**

Returns 0 if the health check passes and non-zero if it fails.

**Example**

This example checks the health of NVMe 0.

.. code-block:: python

   checknvme  --nvme 0

* `Example report (nvme_health_check.pdf) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/nvme_health_check.pdf>`_
* `Example console output (checknvme.log) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/checknvme.log>`_

.. warning::
   The Windows OS driver has a bug where the self-test diagnostic fails if rerun within 10 minutes of a prior
   self-test diagnostic.  The workaround is to wait at least 10 minutes before rerunning a diagnostic.  This
   behavior does not occur in Linux or WinPE.
"""  # noqa: E501

import argparse
import datetime
import logging
import os
import platform
import shutil
import sys

from nvmetools import TESTRUN_DIRECTORY
from nvmetools.apps.nvmecmd import check_nvmecmd_permissions
from nvmetools.features import (
    drive_changes,
    drive_diagnostic,
    drive_features,
    drive_health,
    drive_info,
    drive_wear,
)
from nvmetools.nvme_test import NvmeTestSuite
from nvmetools.report import HealthReport
from nvmetools.support.conversions import is_admin
from nvmetools.support.exit import USAGE_EXIT_CODE, exit_on_exception
from nvmetools.support.log import start_logger


def _parse_arguments() -> None:
    """Parse input arguments from command line."""
    parser = argparse.ArgumentParser(
        description=checknvme.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-n", "--nvme", type=int, default=0, help="NVMe drive number (e.g. 0)", metavar="#")
    parser.add_argument("-i", "--run_id", help="ID to use for directory name")
    parser.add_argument("-p", "--pdf", dest="pdf", help="Display the pdf report", action="store_true")
    parser.add_argument("-V", "--verbose", help="Verbose log mode", action="store_true")
    parser.add_argument("-D", "--debug", help="Debug mode", action="store_true")
    return vars(parser.parse_args())


def checknvme(
    nvme: int = 0, run_id: str = None, pdf: bool = False, verbose: bool = False, debug: bool = False
) -> None:
    """Run short check of the NVMe drive health and wear.

    Args:
        nvme: NVMe device number.  Can be found with listnvme.
        run_id: Optional string to use for log directory name.
        pdf: Displays the pdf report at end if True.
        verbose:  Displays additional logging if True.
        debug: Displays all possible logging if True.

    Returns:
       returns 0 if all tests pass, else returns non-zero error code
    """
    try:

        if debug:
            log_level = logging.DEBUG
        elif verbose:
            log_level = logging.VERBOSE
        else:
            log_level = logging.INFO

        if run_id is None:
            directory = os.path.join(
                os.path.abspath(TESTRUN_DIRECTORY),
                datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            )
        else:
            directory = os.path.join(
                os.path.abspath(TESTRUN_DIRECTORY),
                run_id,
            )
        if os.path.exists(directory):
            shutil.rmtree(directory)

        log = start_logger(directory, log_level, "checknvme.log", debug_log=True)
        check_nvmecmd_permissions()

        if platform.system() == "Windows" and not is_admin():
            log.error(" This script requires running with admin (root) privileges")
            sys.exit(USAGE_EXIT_CODE)

        # Now create an test_suite instance and run the tests belowe

        title = "NVMe Health Check"
        description = """Verifies drive health and wear with diagnostic and SMART"""
        details = """NVMe Health Check is a short Test Suite that verifies drive health and wear
                  by running the drive diagnostic, reviewing SMART data, and
                  checking the Self-Test history."""

        test_suite = NvmeTestSuite(title, description, details, nvme, directory)

        test_suite.run_test(drive_info)
        test_suite.run_test(drive_wear)
        test_suite.run_test(drive_health)
        test_suite.run_test(drive_features)
        test_suite.run_test(drive_diagnostic)
        test_suite.run_test(drive_changes)

        test_suite.end()

        report = HealthReport(results_directory=test_suite.directory, description=details)
        report.save()
        if pdf:
            report.show()

        sys.exit(test_suite.return_code)

    except Exception as e:
        exit_on_exception(e)


def main() -> None:
    """Allow command line operation with unique arguments or running from test script."""
    args = _parse_arguments()
    checknvme(**args)


if __name__ == "__main__":
    main()
