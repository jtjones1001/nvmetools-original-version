# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Tests the process.py module."""

import os
import logging
import time
import platform
import pytest
import sys

from nvmetools.support.process import RunProcess, _ZombieProcess
from nvmetools.apps.nvmecmd import NVMECMD_EXEC, NVMECMD_DIR
from nvmetools.support.log import  start_logger


top_directory = os.path.split( os.path.dirname(__file__))[0]
base_directory = os.path.join(top_directory,"__results__","process")
log_directory = os.path.join(top_directory,"__results__")


if platform.system() == "Windows":
    KILL_EXIT_CODE = 15
else:
    KILL_EXIT_CODE = -9

nvme = 0

log = start_logger(log_directory, logging.DEBUG, "pytest.log")

log.info("Running test_process.py")
#---------------------------------------------------------------------------
def test_process_nowait():
    log.info("\n *** Testing process with no wait ***\n")
    directory = os.path.join(base_directory,"test_nowait")
    args = [
        NVMECMD_EXEC,
            os.path.join(NVMECMD_DIR, "read.cmd.json"),
        "--dir",
        f"{directory}",
        "--nvme",
        f"{nvme}",
        "--samples",
        "1",
        "--interval",
        "10",
    ]
    process = RunProcess(args, directory, wait=False)
    process.wait()
    assert process.return_code == 0
    assert process.run_time < 1.5
#---------------------------------------------------------------------------
def test_process_wait():
    log.info("\n *** Testing process with wait ***\n")
    directory = os.path.join(base_directory,"test_wait")
    args = [
        NVMECMD_EXEC,
            os.path.join(NVMECMD_DIR, "read.cmd.json"),
        "--dir",
        f"{directory}",
        "--nvme",
        f"{nvme}",
        "--samples",
        "1",
        "--interval",
        "10",
    ]
    process = RunProcess(args, directory, wait=True)
    process.wait()
    assert process.return_code == 0
    assert process.run_time < 1.5
#---------------------------------------------------------------------------
def test_process_kill_1_sec():
    log.info("\n *** Testing process with kill after 1 second ***\n")
    directory = os.path.join(base_directory,"test_kill_1_sec")
    args = [
        NVMECMD_EXEC,
            os.path.join(NVMECMD_DIR, "read.cmd.json"),
        "--dir",
        f"{directory}",
        "--nvme",
        f"{nvme}",
        "--samples",
        "100000",
        "--interval",
        "10",
    ]
    process = RunProcess(args, directory, wait=False)
    time.sleep(1)
    process.kill()
    assert process.return_code == KILL_EXIT_CODE
    assert process.run_time < 1.6
#---------------------------------------------------------------------------
def test_process_timeout_2_sec():
    log.info("\n *** Testing process with 2 second timeout ***\n")
    directory = os.path.join(base_directory,"test_timeout_2_sec")
    args = [
        NVMECMD_EXEC,
            os.path.join(NVMECMD_DIR, "read.cmd.json"),
        "--dir",
        f"{directory}",
        "--nvme",
        f"{nvme}",
        "--samples",
        "100000",
        "--interval",
        "10",
    ]
    process = RunProcess(args, directory, wait=False)
    process.wait(timeout_sec=2)
    assert process.return_code == 0
    assert process.run_time < 5.0
#---------------------------------------------------------------------------
def test_process_stop_2_sec():
    log.info("\n *** Testing process with stop at 2 seconds ***\n")
    directory = os.path.join(base_directory,"test_stop_2_sec")
    args = [
        NVMECMD_EXEC,
            os.path.join(NVMECMD_DIR, "read.cmd.json"),
        "--dir",
        f"{directory}",
        "--nvme",
        f"{nvme}",
        "--samples",
        "100000",
        "--interval",
        "10",
    ]
    process = RunProcess(args, directory, wait=False)
    time.sleep(2)
    process.stop()
    assert process.return_code == 0
    assert process.run_time < 5.0

    run_time = process.run_time
    return_code = process.return_code
    process.kill()
    process.wait()
    assert return_code == process.return_code
    assert run_time == process.run_time

    process.stop()
    process.wait()
    assert return_code == process.return_code
    assert run_time == process.run_time

    time.sleep(1)
    process.wait()
    assert return_code == process.return_code
    assert run_time == process.run_time
#---------------------------------------------------------------------------
def test_process_nokill_1_sec():
    log.info("\n *** Testing process with 1 second kill that fails ***\n")
    directory = os.path.join(base_directory,"test_nokill_1_sec")
    args = [
        NVMECMD_EXEC,
            os.path.join(NVMECMD_DIR, "read.cmd.json"),
        "--dir",
        f"{directory}",
        "--nvme",
        f"{nvme}",
        "--samples",
        "100000",
        "--interval",
        "10",
    ]
    log.debug("Setting RunProcess._test_suppress_kill = True")
    RunProcess._test_suppress_kill = True

    process = RunProcess(args, directory, wait=False)
    time.sleep(1)
    try:
        process.kill()
        assert True
    except _ZombieProcess as e:
        assert e.code == 59

    log.debug("Setting RunProcess._test_suppress_kill = False")
    RunProcess._test_suppress_kill = False

    process.kill()
    process.wait()
    assert process.return_code == KILL_EXIT_CODE
#---------------------------------------------------------------------------
def test_process_no_stop_so_kill():
    log.info("\n *** Testing process with stop that fails ***\n")
    directory = os.path.join(base_directory,"test_no_stop_so_kill")
    args = [
        NVMECMD_EXEC,
            os.path.join(NVMECMD_DIR, "read.cmd.json"),
        "--dir",
        f"{directory}",
        "--nvme",
        f"{nvme}",
        "--samples",
        "100000",
        "--interval",
        "10",
    ]
    log.debug("Setting RunProcess._test_suppress_ctrlbreak = True")
    RunProcess._test_suppress_ctrlbreak = True

    process = RunProcess(args, directory, wait=False)
    time.sleep(1)
    process.stop()
    process.wait()

    assert process.return_code == KILL_EXIT_CODE
    assert process.run_time > 3

    RunProcess._test_suppress_ctrlbreak = False
