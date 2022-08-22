# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Test and report for verifying drive health.

This module verifies parameters that indicate if a drive is healthy.  Specifically critical SMART
attributes and previous self-test results.
"""
# Allows type checking for the report function, else circular imports.  TODO: Refactor later.

from __future__ import annotations

from typing import TYPE_CHECKING

from nvmetools.info import Info
from nvmetools.nvme_test import AbortedTestError, NvmeTest, verify_requirement
from nvmetools.settings import RqmtId, THROTTLE_PERCENT_LIMIT, TestId
from nvmetools.support.conversions import as_int

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
            """ This test verifies drive health by looking for failed self-test
            results, critical warnings, media and data integrity errors, and excessive thermal
            throttling.  Self-test results are read from Log Page 6.  All other results are
            SMART attributes from Log Page 2.
            <br/><br/>
            This test defines excessive thermal throttling as a failure but excessive throttling
            could indicate an environment or system issue."""
        )
        report.add_test_result_intro(test_result)

        data = test_result["data"]

        if data["selftest fails"] == 0:
            this_paragraph = f"""A total of {data["number selftests"]} prior self-test results were found
               and none failed.  """
        else:
            this_paragraph = f"""A total of {data["number selftests"]} prior self-test
                results were found and {data["selftest fails"]} of those failed.  """

        if data["critical warnings"] == "No" and data["media errors"] == 0:
            this_paragraph += """There were no critical warnings or media errors. """
        else:
            this_paragraph += f"""There were critical warnings or media errors that indicate
                an unhealthy drive. Media and Data Integrity Errors: {data['media errors']}"""

        if data["throttle percent"] > data["throttle limit"] or data["crit time"] != 0:
            this_paragraph += """Excessive thermal throttling was detected and should be reviewed."""
        else:
            this_paragraph += """No excessive thermal throttling was detected."""

        report.add_paragraph(this_paragraph)

        table_rows = [
            ["PARAMETER", "VALUE", "NOTE"],
            ["Critical Warnings", data["critical warnings"], ""],
            ["Media and Integrity Errors", str(data["media errors"]), ""],
            ["Self-test failures", data["selftest fails"], ""],
            [
                "Percentage Throttled",
                f"{data['throttle percent']:.1f}% ",
                f"Must be less than {data['throttle limit']}%",
            ],
            ["Power On Hours", f"{data['power on hours']:,}", ""],
            [
                "Throttled Hours",
                f"{data['throttle hours']:,.2f}",
                f"{data['throttle percent']:.1f}% of Power On Hours",
            ],
            [
                "Thermal Management Temperature 1 Time",
                f"{data['tmt1']:,} sec",
                f"{(data['tmt1']/3600):,.2f} Hours",
            ],
            [
                "Thermal Management Temperature 2 Time",
                f"{data['tmt2']:,} sec",
                f"{(data['tmt2']/3600):,.2f} Hours",
            ],
            [
                "Warning Composite Temperature Time",
                f"{data['warn time']:,} min",
                f"{(data['warn time']/60):,.2f} Hours",
            ],
            [
                "Critical Composite Temperature Time",
                f"{data['crit time']:,} min",
                f"{(data['crit time']/60):,.2f} Hours",
            ],
        ]
        report.add_table(table_rows, widths=[225, 100, 175])

    except AbortedTestError:
        report.add_aborted_test()

    except Exception as error:
        report.add_exception_report(error)


def test(nvme: int, directory: str, info_file: str = None, *args: any, **kwargs: any) -> None:
    """Verifies drive health.

    The test reads information from the file provided and checked against the health
    of the drive by reading SMART attributes and self-test results

    Args:
       nvme: The nvme drive number (e.g. 0)
       directory: The directory to create the log files
       info_file:  path to file containing information to verify

    Returns:
       returns results in NvmeTest instance.
    """
    try:
        test = NvmeTest(
            test_id=TestId.DRIVE_HEALTH,
            name="Drive Health",
            description="Verifies drive is healthy using SMART and prior self-test results",
            directory=directory,
        )
        info = Info(nvme=nvme, from_file=info_file)
        # ---------------------------------------------------------------------------------------------------
        # Add some parameters to test summary file so can be used for report
        # ---------------------------------------------------------------------------------------------------
        test.data["critical warnings"] = info.parameters["Critical Warnings"]

        test.data["throttle limit"] = THROTTLE_PERCENT_LIMIT
        test.data["selftest fails"] = as_int(info.parameters["Number Of Failed Self-Tests"])
        test.data["number selftests"] = as_int(info.parameters["Current Number Of Self-Tests"])
        test.data["media errors"] = as_int(info.parameters["Media and Data Integrity Errors"])
        test.data["power on hours"] = as_int(info.parameters["Power On Hours"])
        test.data["tmt1"] = as_int(info.parameters["Thermal Management Temperature 1 Time"])
        test.data["tmt2"] = as_int(info.parameters["Thermal Management Temperature 2 Time"])
        test.data["warn time"] = as_int(info.parameters["Warning Composite Temperature Time"])
        test.data["crit time"] = as_int(info.parameters["Critical Composite Temperature Time"])

        test.data["throttle sec"] = (
            test.data["tmt1"] + test.data["tmt2"] + 60 * (test.data["warn time"] + test.data["crit time"])
        )
        test.data["throttle hours"] = test.data["throttle sec"] / 3600
        test.data["throttle percent"] = 100 * (test.data["throttle hours"] / test.data["power on hours"])

        # ---------------------------------------------------------------------------------------------------
        # Verify the drive health requirements
        # ---------------------------------------------------------------------------------------------------
        verify_requirement(
            RqmtId.NO_CRITICAL_WARNINGS,
            name="There shall be no critical warnings",
            limit="No",
            value=test.data["critical warnings"],
            passed=(test.data["critical warnings"] == "No"),
            test=test,
        )
        verify_requirement(
            RqmtId.NO_SELFTEST_FAILS,
            name="Previous Self-Test failures shall be 0",
            limit=0,
            value=test.data["selftest fails"],
            passed=(test.data["selftest fails"] == 0),
            test=test,
        )
        verify_requirement(
            RqmtId.TIME_THROTTLED,
            name=f"Percentage throttled shall be less than {THROTTLE_PERCENT_LIMIT:.1f}%",
            limit=f"{THROTTLE_PERCENT_LIMIT}%",
            value=f"{test.data['throttle percent']:0.2f}%",
            passed=(test.data["throttle percent"] < THROTTLE_PERCENT_LIMIT),
            test=test,
        )
        verify_requirement(
            RqmtId.NO_MEDIA_ERRORS,
            name="SMART media and integrity errors shall be 0",
            limit=0,
            value=test.data["media errors"],
            passed=(test.data["media errors"] == 0),
            test=test,
        )
        verify_requirement(
            RqmtId.CRITICAL_TIME,
            name="Critical composite temperature time shall be 0",
            limit=0,
            value=test.data["crit time"],
            passed=(test.data["crit time"] == 0),
            test=test,
        )
        return test.end()

    except Exception as error:
        return test.abort_on_exception(error)
