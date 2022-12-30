# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that updates test suites.

.. highlight:: none

This function updates the Test Suite after a user has manually updated the test results.
This allows the user to enter manual results and then easily create a new dashboard and
PDF report.

To manually update a test result edit the results.json file in the test directory.  In
the ["steps"] section find the step and verification to change.  Change the "result"
parameter to "PASSED" or "FAILED".  Recommend completing the "reviewer" parameter and
the "note" parameter with the reason for the change.

This function updates the following files in a Test Suite:
        results.json
        dashboard.html
        report.pdf
        <test #>   results.json

Command Line Parameters
    --nvme, -n     Integer NVMe device number, can be found using listnvme.
    --pdf, -p      Flag to display PDF report in a new window when the check completes.
    --run_id, -i   String to use for the results directory name.
    --verbose, -V  Flag for additional logging, verbose logging.
    --debug, -D    Flag for maximum logging for debugging.

**Return Value**

Returns 0 if the health check passes and non-zero if it fails.

**Example**

This example updates the test suite for the current directory.

.. code-block:: python

   updatesuite .

"""
import argparse

from nvmetools.support.console import exit_on_exception
from nvmetools.support.framework import update_suite_files


def main():

    try:
        parser = argparse.ArgumentParser(
            description="Update NVMe Test Suite",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("-d", "--directory", help="Test suite directory", default=".")

        args = parser.parse_args()

        update_suite_files(args.directory)

    except Exception as e:
        exit_on_exception(e)


if __name__ == "__main__":
    main()
