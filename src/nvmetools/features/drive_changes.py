# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Test and report for verifying drive parameter changes over time."""

# Allows type checking for the report function, else circular imports.  TODO: Refactor later.

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from nvmetools.info import Info
from nvmetools.nvme_test import AbortedTestError, NvmeTest
from nvmetools.settings import RqmtId, TestId
from nvmetools.support.conversions import as_datetime, as_nicedate


if TYPE_CHECKING:
    from nvmetools.report import HealthReport


def report(report: HealthReport, test_result: dict) -> None:
    """Create pages for this this test in the pdf test report.

    Args:
       report: Check NVMe PDF test report
       test_result: Dictionary with test results.
    """
    try:
        report.add_subheading("DESCRIPTION")
        report.add_paragraph(
            """This test verifies drive parameters change as expected across two readings.  Static parameters,
            such as Model and Serial Number, are verified not to change. SMART counter parameters, such as
            Power-On Hours, are verified not to decrease or reset.
            <br/><br/>
            For the complete list of parameters, refer to the file nvme.info.json. In this file, static
            parameters have the compare type 'exact' and counter parameters 'counter'."""
        )
        report.add_test_result_intro(test_result)

        data = test_result["data"]

        start_date = as_datetime(data["date start read"])
        end_date = as_datetime(data["date end read"])
        delta_time = end_date - start_date

        report.add_paragraph(
            f"""The start information was read at the beginning of this test run on
            {as_nicedate(start_date)}.  The end information was read on
            {as_nicedate(end_date)}.  The time difference between the two
            reads is {str(delta_time).split('.')[0]}.  The reported difference in Power
            On Hours is {data["power on delta"]}."""
        )
        if len(data["static mismatches"]) == 0:
            this_paragraph = f"""A total of {data['static parameters']} static parameters
            were verified not to change.  """
        else:
            this_paragraph = f"""A total of {data['static parameters']} static parameters
            were verified with {len(data['static mismatches'])} failures.  """

        if len(data["counter decrements"]) == 0:
            this_paragraph += f"""A total of {data['counter parameters']} counter parameters
            were verified not to decrement or reset."""
        else:
            this_paragraph += f"""A total of {data['counter parameters']} counter parameters
            were verified with {len(data['counter decrements'])} failures."""
        report.add_paragraph(this_paragraph)

        table_rows = [["PARAMETER", "START", "END"]]
        for parameter in data["static mismatches"]:
            table_rows.append([parameter["name"], parameter["start"], parameter["end"]])
        for parameter in data["counter decrements"]:
            table_rows.append([parameter["name"], parameter["start"], parameter["end"]])

        if test_result["requirements"]["condensed"][RqmtId.NO_CRITICAL_WARNINGS]["fail"] == 0:
            smart_paragraph = "No Critical Warnings were asserted."
        else:
            smart_paragraph = "Critical Warnings were asserted."

        if test_result["requirements"]["condensed"][RqmtId.NO_ERROR_INCREASE]["fail"] == 0:
            smart_paragraph += " Media and Data Integrity Errors did not increase."
        else:
            smart_paragraph += " Media and Data Integrity Errors increased by"
            smart_paragraph += f" {test.data['media error increase']}"

        report.add_paragraph(smart_paragraph)

    except AbortedTestError:
        report.add_aborted_test()

    except Exception as error:
        report.add_exception_report(error)


def test(nvme: int, directory: str, info_file: str = None, *args: any, **kwargs: any) -> None:
    r"""Verifies parameters change as expected.

    The test reads information and compares against the information in the file provided.  It verifies static
    parameters do not change and counter parameters do not decrement.

    When info_file is not provided the default is:

       <directory>\10_drive_info\nvme.info.json.

    Args:
       nvme: The nvme drive number (e.g. 0)
       directory: The directory to create the log files
       info_file:  path to file containing information to verify

    Returns:
       returns results in NvmeTest instance.
    """
    try:
        test = NvmeTest(
            test_id=TestId.DRIVE_CHANGE,
            name="Drive Parameter Change",
            description="Compares drive parameters against earlier reading",
            directory=directory,
        )

        if info_file is None:
            info_file = os.path.join(directory, "10_drive_info", "nvme.info.json")

        start_info = Info(nvme=nvme, from_file=info_file)

        end_info = Info(nvme, directory=test.directory)
        end_info.verify(test, start_info, verify_poh=True)

        return test.end()

    except Exception as error:
        return test.abort_on_exception(error)
