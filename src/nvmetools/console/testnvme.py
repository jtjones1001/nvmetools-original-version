# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that runs an NVMe Test Suite.

.. highlight:: none

Runs an NVME Test Suite defined in the nvmetools.suite package.

Logs results to a directory in ~/Documents/nvmetools/suites/<suite>.  The directory name is
defined by the uid command line parameter.  If uid was not specified the directory name is
based on the date and time the command was run.

.. note::
   Test Suites with self-test tests must be run as Administrator on Windows OS.

Command Line Parameters
    --suite         Name of test suite to run
    --nvme, -n      Integer NVMe device number, can be found using listnvme.
    --volume, -v    Volume to test
    --uid, -i    String to use for the results directory name.
    --loglevel, -l  The amount of information to display, integer, 0 is least and 3 is most.

**Example**

    This example runs a Test Suite called short_demo on NVMe 1.

    .. code-block:: python

        testnvme  short_demo  --nvme 1  --volume /mnt/nvme1a

    - `Example report (report.pdf) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/nvme_health_check.pdf>`_
    - `Example dashboard (dashboard.html) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/checknvme.log>`_

**Example**

    This example runs a Test Suite called big_demo on NVMe 1.

    .. code-block:: python

        testnvme  big_demo  --nvme 1 --volume g:

    - `Example report (report.pdf) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/nvme_health_check.pdf>`_
    - `Example dashboard (dashboard.html) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/checknvme.log>`_

"""
import argparse
import sys

import nvmetools.suites as suites
import nvmetools.support.console as console


def main():
    """Runs NVMe Test Suite.

    Runs an NVME Test Suite defined in the nvmetools.suite python package.

    The test suite and the NVMe and logical volume to test must be specified.  The listnvme command
    displays the NVMe numbers to use.   The logical volume must reside on the physical NVMe drive
    specified.

    Logs results to a directory in ~/Documents/nvmetools/suites/<suite>.  TThe directory name is
    defined by the uid argument.  If uid was not specified the directory name is defined by the date
    and time the command was run.
    """
    try:

        formatter = lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=50)
        parser = argparse.ArgumentParser(
            description=main.__doc__,
            formatter_class=formatter,
        )
        parser.add_argument("-s", "--suite", required=True, help="test suite to run")

        parser.add_argument(
            "-n",
            "--nvme",
            required=True,
            type=int,
            help="NVMe drive to test",
            metavar="#",
        )
        parser.add_argument(
            "-v",
            "--volume",
            required=True,
            help="logical volume to test",
        )
        parser.add_argument(
            "-l",
            "--loglevel",
            type=int,
            default=1,
            metavar="#",
            help="level of detail in logging, 0 is least, 3 is most",
        )
        parser.add_argument("-i", "--uid", help="unique id for directory name")

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
