# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Test and report for verifying drive specific features for tester environment.

This module runs a test script created by the tester that contains requirements for the specific
model of drive being tested.
"""
# Allows type checking for the report function, else circular imports.  TODO: Refactor later.

from __future__ import annotations

from typing import TYPE_CHECKING

from nvmetools.info import Info
from nvmetools.nvme_test import AbortedTestError, NvmeTest, load_user_drive_test_script
from nvmetools.settings import TestId
from nvmetools.support.log import log

if TYPE_CHECKING:
    from nvmetools.report import HealthReport


def report(report: HealthReport, test_result: dict) -> None:
    """Create pages for pdf test report provided.

    Args:
       test_result (dict): Dictionary with test results.
    """
    try:
        report.add_subheading("DESCRIPTION")
        report.add_paragraph(
            """This test verifies a set of requirements, specific to the drive being tested, that
            are defined by the tester.  This allows the tester to verify features and limits that are
            specific for their environment.  For example, the tester can verify a specific feature,
            such as crypto-erase, is supported.   Another example, the tester can verify the maximum
            power for Power State 0 is less than their system's power target.
            """
        )
        report.add_test_result_intro(test_result)

        data = test_result["data"]

        if data["drive script loaded"]:
            if "report table" in data:
                table_rows = [["PARAMETER", "VALUE", "NOTE"]]
                for row in data["report table"]:
                    table_rows.append([row[0], row[1], row[2]])

                report.add_table(table_rows, widths=[225, 100, 175])
            else:
                report.add_paragraph("No results were found.  Check logs for possible corruption.")
        else:
            report.add_paragraph("No tester requirements for this drive were provided.")

    except AbortedTestError:
        report.add_aborted_test()

    except Exception as error:
        report.add_exception_report(error)


def test(nvme: int, directory: str, info_file: str = None, *args: any, **kwargs: any) -> None:
    """Verifies tester requirements and features.

    This test verifies a set of requirements, specific to the drive being tested, that
    are defined by the tester.  The requirements are defined in a python file called
    <drive model>.py where the drive model is the NVMe model with spaces removed.  This
    allows requirements to be created for each drive model.  The files also contains the
    specification information for warranty, TBW, etc. that optionally can be entered
    by the tester.

    testers can create their own file for each drive model, this allows them to verify a
    specific feature, such as crypto-erase, is supported. The requirements can also verify
    a parameter meets a tester specific limit.  For example, the Power State 0 Max Power must
    be less than 5 Watts.

    Args:
       nvme: The nvme drive number (e.g. 0)
       directory: The directory to create the log files
       info_file:  path to file containing information to verify

    Returns:
       returns results in NvmeTest instance.
    """
    try:
        test = NvmeTest(
            test_id=TestId.DRIVE_FEATURES,
            name="Drive Features",
            description="Verifies drive has tester required features",
            directory=directory,
        )
        # ---------------------------------------------------------------------------------------------------
        # read info from file to get the drive model so can load the drive specific script
        # that was created by the tester.  The drive specific script has a function that
        # verifies the requirements for this test
        # ---------------------------------------------------------------------------------------------------
        info = Info(nvme=nvme, from_file=info_file)
        drive_script = load_user_drive_test_script(info.model)

        if drive_script:
            test.data["drive script loaded"] = True
            drive_script.verify_user_requirements(test, info)
        else:
            log.verbose(f"No drive script found for {info.model} so no features checked")
            test.data["drive script loaded"] = False
            return test.skip()

        return test.end()

    except Exception as error:
        return test.abort_on_exception(error)
