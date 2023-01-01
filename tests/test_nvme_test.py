# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Tests the nvme_test.py module."""

import glob
import os
import logging
import time
import platform
import pytest
import sys

import fail_drive_info

from nvmetools.nvme_test import InvalidUserScriptError, StopOnFailError, load_user_drive_test_script, NvmeTestSuite
from nvmetools.features import drive_changes, drive_info
from nvmetools.support.log import  start_logger
from nvmetools.support.process import RunProcess
from nvmetools.support.exit import exit_on_exception

top_directory = os.path.split( os.path.dirname(__file__))[0]
base_directory = os.path.join(top_directory,"__results__","nvme_test")
log_directory = os.path.join(top_directory,"__results__")

drive_path = os.path.join(top_directory,"tests","drives")

if platform.system() == "Windows":
    KILL_EXIT_CODE = 15
else:
    KILL_EXIT_CODE = -9

nvme = 0

log = start_logger(log_directory, logging.DEBUG, "pytest.log")

log.info("Running test_nvme_test.py")

#---------------------------------------------------------------------------
def test_load_user_script():
    log.info("\n *** Testing load user script with model  ***\n")
    directory = os.path.join(base_directory,"test_load_user_script")

    user_script = load_user_drive_test_script("KBG30ZMV256G_TOSHIBA")
    assert user_script is not None
#---------------------------------------------------------------------------
def test_missing_user_script():
    log.info("\n *** Testing missing user script with model  ***\n")
    directory = os.path.join(base_directory,"test_missing_user_script")

    user_script = load_user_drive_test_script("No model")
    assert user_script is None
#---------------------------------------------------------------------------
def test_invalid_user_script():
    log.info("\n *** Testing invalid user script with model  ***\n")
    directory = os.path.join(base_directory,"test_invalid_user_script")

    try:
        user_script = load_user_drive_test_script("INVALID",directory=drive_path)
    except InvalidUserScriptError:
        pass
    else:
        assert True

#---------------------------------------------------------------------------
def test_nvme_tests():
    log.info("\n *** Testing Nvme Tests and TestSuite ***\n")
    directory = os.path.join(base_directory,"test_test_suites")

    nvme = 0
    title = "NVMe Health Check"
    description = "Verifies drive health and wear with diagnostic and SMART"
    details = """NVMe Health Check is a short Test Suite that verifies drive health and wear
            by running the drive diagnostic, reviewing SMART data, and
            checking the Self-Test history."""

    test_suite = NvmeTestSuite(title, description, details, nvme, directory)
    test_suite.run_test(drive_info)
    test_suite.run_test(drive_changes)
    test_suite.end()
    assert test_suite.return_code == 0

#---------------------------------------------------------------------------
def test_nvme_tests():
    log.info("\n *** Testing Nvme Tests and TestSuite with stop ***\n")
    directory = os.path.join(base_directory,"test_test_suites_stop")

    try:
        nvme = 0
        title = "NVMe Health Check"
        description = "Verifies drive health and wear with diagnostic and SMART"
        details = """NVMe Health Check is a short Test Suite that verifies drive health and wear
                by running the drive diagnostic, reviewing SMART data, and
                checking the Self-Test history."""

        test_suite = NvmeTestSuite(title, description, details, nvme, directory)
        test_suite.run_test(fail_drive_info, stop_on_fail=True)
        test_suite.run_test(drive_changes)
        test_suite.end()
    except StopOnFailError as e:
        log.info("Stopping on fail")

    list_of_files = glob.glob(directory)
    assert len(list_of_files) == 1
    assert test_suite.return_code != 0
