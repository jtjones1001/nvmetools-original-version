# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that updates test suite results.

Test Suite results can be updated after completion by editing the results.json files.
This command creates a new dashboard, PDF report, and updates the summaries in results.json to
reflect any changes in the results.json files.

To update a test result edit the results.json file in the test directory.  In the ["steps"]
section find the step and verification to change.  Change the verification's "result"
to "PASSED" or "FAILED".  Recommend completing the "reviewer" and "note" parameters with the
reason for the change.  After all results.json files have been updated run this command.

Command Line Parameters
    --directory, -d     Directory of the test suite results to update

**Example**

    This example updates the test suite for the current directory.

    .. code-block:: python

        updatenvme .

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
