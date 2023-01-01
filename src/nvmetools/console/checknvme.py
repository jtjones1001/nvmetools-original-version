# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that checks the health of NVMe drive.

.. highlight:: none

Verifies the NVMe drive health by running the short self-test diagnostic, checking the SMART
attributes for errors and log page 6 for prior self-test failures.

Logs results to a directory in ~/Documents/nvmetools/suites/check_nvme.  The directory name is
defined by the run_id command line parameter.  If run_id was not specified the directory name is
based on the date and time the command was run.

.. note::
   This command must be run as Administrator on Windows OS.

Command Line Parameters
    --nvme, -n     Integer NVMe device number, can be found using listnvme.
    --run_id, -i   String to use for the results directory name.
    --loglevel, -l  The amount of information to display, integer, 0 is least and 3 is most.

**Example**

This example checks the health of NVMe 0.

.. code-block:: python

   checknvme  --nvme 0

* `Example report (report.pdf) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/nvme_health_check.pdf>`_
* `Example console output (console.log) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/checknvme/checknvme.log>`_

.. warning::
   The Windows OS driver has a bug where the self-test diagnostic fails if rerun within 10 minutes of a prior
   self-test diagnostic.  The workaround is to wait at least 10 minutes before rerunning a diagnostic.  This
   behavior does not occur in Linux or WinPE.
"""  # noqa: E501
import argparse

import nvmetools.suites as suites
import nvmetools.support.console as console


def main():
    """Checks the health of NVMe drive.

    Verifies the NVMe drive health by running the short self-test diagnostic, checking the SMART
    attributes for errors and log page 6 for prior self-test failures.

    Logs results to a directory in ~/Documents/nvmetools/suites/check_nvme.  The directory name is
    defined by the run_id command line parameter.  If run_id was not specified the directory name is
    based on the date and time the command was run.
    """
    try:
        formatter = lambda prog: argparse.RawDescriptionHelpFormatter(prog,max_help_position=50)
        parser = argparse.ArgumentParser(
            description=main.__doc__,
            formatter_class=formatter,
        )
        parser.add_argument(
            "-n",
            "--nvme",
            required=True,
            type=int,
            default=0,
            help="NVMe drive number (e.g. 0)",
            metavar="#",
        )
        parser.add_argument("-l", "--loglevel", type=int, default=1, help="level of detail in logging")
        parser.add_argument("-i", "--run_id", help="ID to use for directory name")
        args = vars(parser.parse_args())

        suites.health(args)

    except Exception as e:
        console.exit_on_exception(e)


if __name__ == "__main__":
    main()
