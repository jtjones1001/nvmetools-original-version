# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Test and report for reading drive information.

This module verifies the reading of NVMe information using the Get Log Page, Get Feature, Identify Controller,
and Identify Namespace Admin Commands.  If any Admin Command returns an error code the test fails.
"""

# Allows type checking for the report function, else circular imports.  TODO: Refactor later.

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nvmetools.report import HealthReport

import os

from nvmetools.settings import TestId
from nvmetools.info import Info
from nvmetools.nvme_test import AbortedTestError, NvmeTest


def report(report: HealthReport, test_result: dict) -> None:
    """Create pages for this this test in the pdf test report.

    Args:
       report: The health check NVMe test report.
       test_result: Dictionary with test results.
    """
    try:
        report.add_subheading("DESCRIPTION")
        report.add_paragraph(
            """This test verifies the drive information can be read without errors.  The NVMe information
            is read using the Get Log Page, Get Feature, Identify Controller, and Identify Namespace Admin
            Commands.  If any Admin Command returns an error code the test fails.
            """
        )
        report.add_test_result_intro(test_result)

    except AbortedTestError:
        report.add_aborted_test()

    except Exception as error:
        report.add_exception_report(error)


def test(nvme: int, directory: str, *args: any, **kwargs: any) -> dict:
    r"""Verifies drive information has no errors.

    The test reads the NVMe drive information and verifies no errors occurred during the reads and the
    SMART attributes do not report any critical warnings.

    Args:
       nvme: The nvme drive number (e.g. 0)
       directory: The directory to create the log files

    Returns:
       returns a dictionary containing the test results.
    """
    try:
        test = NvmeTest(
            test_id=TestId.DRIVE_INFO,
            name="Drive Info",
            description="Verifies drive information has no critical errors",
            directory=directory,
        )
        Info(nvme=nvme, directory=test.directory)

        return test.end(1)

    except Exception as error:
        return test.abort_on_exception(error)
