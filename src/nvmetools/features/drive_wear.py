# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Test and report for verifying drive wear.

This module verifies the drive is not worn out by checking the relevant SMART attributes from Log Page 2.
The acceptable amount of wear is defined in the user settings file.
"""
# Allows type checking for the report function, else circular imports.  TODO: Refactor later.

from __future__ import annotations

from typing import TYPE_CHECKING

from nvmetools.info import Info
from nvmetools.nvme_test import AbortedTestError, NvmeTest, load_user_drive_test_script, verify_requirement
from nvmetools.settings import RqmtId, TestId, WEAR_PERCENT_LIMIT
from nvmetools.support.conversions import GB_IN_TB, as_float, as_int

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
            """This test verifies the drive is not “worn out” prior to beginning a test run.
            Drive wear is determined by reading SMART attributes from log page 2. The Percentage
            Used SMART attribute is the primary reference of drive wear.
            <br/><br/>

            If the user provided information on the warranty and TBW then the Percentage Data Written
            and Percentage Warranty Used are verified.  Percentage Data Written is defined as
            as 100 * (Data Written / TBW) where TBW (Terabytes Written) is the total amount of
            data that can be written to the drive during the warranty period.  Data Written is
            the SMART attribute that reports the data written to the drive.
            <br/><br/>

            Percentage Warranty Used is defined as 100 * (Power On Hours / Warranty Hours)
            where warranty hours is the number of days in the warranty multiplied by 8 hours for
            client drives or 24 hours for enterprise drives.
            """
        )
        report.add_test_result_intro(test_result)

        data = test_result["data"]

        table_rows = [
            ["PARAMETER", "VALUE", "NOTE"],
            ["Percentage Used", f"{data['percentage used']}%", "SMART attribute"],
        ]

        if "specification" in data:
            warranty_comment = (
                f"{data['specification']['warranty']}" + f" * 365 * {data['specification']['hours per day']}hr"
            )
            table_rows.extend(
                [
                    ["Percentage Data Written", f"{data['data used']:.1f}%", "Calculated"],
                    ["Percentage Warranty Used", f"{data['warranty used']:.1f}%", "Calculated"],
                    ["Data Written", f"{data['data written tb']:.3f} TB", "SMART attribute"],
                    ["Terabytes Written (TBW)", f"{data['specification']['tbw']} TB", "User Input"],
                    ["Warranty", f"{data['specification']['warranty']} years", "User input"],
                    ["Power On Hours", f"{data['power on hours']:,}", "SMART attribute"],
                    [
                        "Warranty Hours",
                        f"{data['specification']['warranty hours']:,}",
                        warranty_comment,
                    ],
                ]
            )
        report.add_table(rows=table_rows, widths=[225, 100, 175])

    except AbortedTestError:
        report.add_aborted_test()

    except Exception as error:
        report.add_exception_report(error)


def test(nvme: int, directory: str, info_file: str = None, *args: any, **kwargs: any) -> None:
    """Verifies drive wear within limits.

    The test reads information from the file provided and checks drive wear against the
    limit.  The default wear limit is 80%.  If the input file contains
    specification data the test also verifies data written and power on hours.

    Args:
       nvme: The nvme drive number (e.g. 0)
       directory: The directory to create the log files
       info_file:  path to file containing information to verify

    Returns:
       returns results in NvmeTest instance.
    """
    try:
        test = NvmeTest(
            test_id=TestId.DRIVE_WEAR,
            name="Drive Wear",
            description="Verifies drive wear is within limit using SMART attributes",
            directory=directory,
        )
        # ---------------------------------------------------------------------------------------------------
        # Read in NVMe information from file specified and verify the wear requirements.
        # Save some parameters in the results file so they can be used for the report
        # ---------------------------------------------------------------------------------------------------
        info = Info(nvme=nvme, from_file=info_file)

        test.data["wear limit"] = WEAR_PERCENT_LIMIT
        test.data["available spare"] = as_int(info.parameters["Available Spare"])
        test.data["percentage used"] = as_int(info.parameters["Percentage Used"])

        verify_requirement(
            RqmtId.PERCENTAGE_USED,
            name=f"Percentage Used shall be less than {WEAR_PERCENT_LIMIT}%",
            limit=f"{WEAR_PERCENT_LIMIT}%",
            value=f"{test.data['percentage used']}%",
            passed=(test.data["percentage used"] < WEAR_PERCENT_LIMIT),
            test=test,
        )
        verify_requirement(
            RqmtId.AVAILABLE_SPARE,
            name="Available Spare shall be 100%",
            limit="100%",
            value=f"{test.data['available spare']}%",
            passed=(test.data["available spare"] == 100),
            test=test,
        )
        # ---------------------------------------------------------------------------------------------------
        # Load the drive specific script created by user to get warranty, TBW, and other
        # info that must be entered manually by the user.  This file is optional
        # ---------------------------------------------------------------------------------------------------
        drive_script = load_user_drive_test_script(info.model)

        if drive_script:
            test.data["specification"] = drive_script.DRIVE_SPECIFICATION
            test.data["data written tb"] = as_float(info.parameters["Data Written"]) / GB_IN_TB
            test.data["power on hours"] = as_int(info.parameters["Power On Hours"])
            test.data["data used"] = 100.0 * test.data["data written tb"] / test.data["specification"]["tbw"]
            test.data["warranty used"] = (
                100.0 * test.data["power on hours"] / test.data["specification"]["warranty hours"]
            )
            verify_requirement(
                RqmtId.DATA_WRITTEN,
                name=f"Percentage Written shall be less than {WEAR_PERCENT_LIMIT}%",
                limit=f"{WEAR_PERCENT_LIMIT}%",
                value=f"{test.data['data used']:0.1f}%",
                passed=(test.data["data used"] < WEAR_PERCENT_LIMIT),
                test=test,
            )
            verify_requirement(
                RqmtId.POWERON_HOURS,
                name=f"Percentage Warranty Used shall be less than {WEAR_PERCENT_LIMIT}%",
                limit=f"{WEAR_PERCENT_LIMIT}%",
                value=f"{test.data['warranty used']:0.1f}%",
                passed=(test.data["warranty used"] < WEAR_PERCENT_LIMIT),
                test=test,
            )

        return test.end()

    except Exception as error:
        return test.abort_on_exception(error)
