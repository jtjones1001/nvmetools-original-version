# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that runs an NVMe Test Suite.

.. highlight:: none

Runs an NVME Test Suite defined in the nvmetools.suite package.

Logs results to a directory in ~/Documents/nvmetools/suites/<suite>.  The directory name is
defined by the run_id command line parameter.  If run_id was not specified the directory name is
based on the date and time the command was run.

The debug and verbose parameters enable additional logging and keeps additional files for the
purpose of debugging the script or device failure.  The full debug output is alway saved in the
debug.log regardless of these parameters.

.. note::
   Test Suites with self-test tests must be run as Administrator on Windows OS.

Command Line Parameters
    --suite         Name of test suite to run
    --nvme, -n      Integer NVMe device number, can be found using listnvme.
    --volume, -v    Volume to test
    --run_id, -i    String to use for the results directory name.
    --loglevel, -l  The amount of information to display, integer, 0 is least and 3 is most.

**Example**

This example runs a Test Suite called short_demo on NVMe 1.

.. code-block:: python

   testnvme  short_demo  --nvme 0  --volume c:

* `Example report (nvme_health_check.pdf) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/nvme_health_check.pdf>`_
* `Example console output (checknvme.log) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/checknvme.log>`_

"""
import argparse
import sys

import nvmetools.suites as suites
import nvmetools.support.console as console


def main():
    """Runs NVMe Test Suite.

    Logs results to a directory in ~/Documents/nvmetools/suites/<suite>.  The directory name is
    defined by the run_id command line parameter.  If run_id was not specified the directory name is
    based on the date and time the command was run.
    """
    try:
        parser = argparse.ArgumentParser(
            description=main.__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("suite", help="test suite")

        parser.add_argument(
            "-n", "--nvme", required=True, type=int, default=0, help="NVMe drive number (e.g. 0)", metavar="#"
        )
        parser.add_argument("-v", "--volume", required=True, help="volume to test")
        parser.add_argument("-l", "--loglevel", type=int, default=1, help="volume to test")
        parser.add_argument("-i", "--run_id", help="ID to use for directory name")

        args = vars(parser.parse_args())

        suite_function = getattr(suites, args["suite"], None)
        if suite_function is None:
            print(f"FATAL ERROR: Test Suite {args['suite']} was not found")
            sys.exit(1)
        else:
            suite_function(args)

        sys.exit(0)

    except Exception as e:
        console.exit_on_exception(e)


if __name__ == "__main__":
    main()
