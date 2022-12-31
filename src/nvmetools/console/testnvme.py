# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that runs an NVMe Test Suite.

.. highlight:: none

Verifies the NVMe drive health by running the short self-test diagnostic, checking the SMART attributes for
errors and log page 6 for prior self-test failures.

Logs results to ~/Documents/nvme/<name> where <name> is the date and time the command was run or the run_id
if specified.  This directory contains a PDF test report and other data files.

The debug and verbose parameters enable additional logging and keeps additional files for the purpose of
debugging the script or device failure.  The full debug output is alway saved in the debug.log regardless of
these parameters.

.. note::
   Test Suites with self-test tests must be run as Administrator on Windows OS.

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

   testnvme  --nvme 0  --volume c:  demo

* `Example report (nvme_health_check.pdf) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/nvme_health_check.pdf>`_
* `Example console output (checknvme.log) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/checknvme.log>`_


"""
import argparse

import nvmetools.suites as suites
import nvmetools.support.console as console


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Run NVMe Test Suite",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("suite", help="test suite")

        parser.add_argument(
            "-n", "--nvme", required=True, type=int, default=0, help="NVMe drive number (e.g. 0)", metavar="#"
        )
        parser.add_argument("-v", "--volume", required=True, help="volume to test")
        parser.add_argument("-l", "--loglevel", type=int, default=1, help="volume to test")

        parser.add_argument("-i", "--run_id", help="ID to use for directory name")
        parser.add_argument("-p", "--pdf", dest="pdf", help="Display the pdf report", action="store_true")
        parser.add_argument("-V", "--verbose", help="Verbose log mode", action="store_true")
        parser.add_argument("-D", "--debug", help="Debug mode", action="store_true")

        args = vars(parser.parse_args())

        try:
            getattr(suites, args["suite"])(args)
        except AttributeError as e:
            print(f"FATAL ERROR: {args['suite']} not found")
            print(e)

    except Exception as e:
        console.exit_on_exception(e)


if __name__ == "__main__":
    main()
