import os

from nvmetools import Info, InfoSamples, TestStep, rqmts
from nvmetools.apps.fio import FioFiles
from nvmetools.support.conversions import BYTES_IN_GB


def test_start_info(test):
    """blah blah blah."""
    with TestStep(
        test, "Test start info", "Read test start info and verify drive not in error state.", stop_on_fail=True
    ) as step:
        start_info = Info(test.suite.nvme, directory=step.directory)
        rqmts.no_critical_warnings(step, start_info)

    return start_info


def create_fio_big_file(test, disk_size):

    with TestStep(
        test,
        "Create fio file",
        "Create file if does not exist.",
        stop_on_fail=True,
    ) as step:
        fio_files = FioFiles(step.directory, test.suite.volume)
        fio_file = fio_files.create(big=True, verify=False, wait_sec=180, disk_size=disk_size)

        test.data["file size"] = fio_file.file_size
        test.data["file size gb"] = fio_file.file_size / BYTES_IN_GB
        test.data["fio filepath"] = fio_file.os_filepath

    return fio_file


def create_fio_performance_file(test):

    with TestStep(
        test,
        "Create fio file",
        "If does not exist, create a small file without verification data for fio.",
        stop_on_fail=True,
    ) as step:
        fio_files = FioFiles(step.directory, test.suite.volume)
        fio_file = fio_files.create(big=False, verify=False, wait_sec=180)

        test.data["file size"] = fio_file.file_size
        test.data["file size gb"] = fio_file.file_size / BYTES_IN_GB
        test.data["fio filepath"] = fio_file.os_filepath

    return fio_file


def create_fio_small_file(test):

    with TestStep(
        test,
        "Create fio file",
        "Create small file with verification data, if does not exist.",
        stop_on_fail=True,
    ) as step:
        fio_files = FioFiles(step.directory, test.suite.volume)
        fio_file = fio_files.create(big=False, verify=True, wait_sec=180)

        test.data["file size"] = fio_file.file_size
        test.data["file size gb"] = fio_file.file_size / BYTES_IN_GB
        test.data["fio filepath"] = fio_file.os_filepath

    return fio_file


def create_fio_stress_file(test, size):

    with TestStep(test, "Create fio file", "Use big file if exists, else use or create a small file.") as step:

        step.stop_on_fail = True

        fio_files = FioFiles(step.directory, test.suite.volume)
        if os.path.exists(fio_files.bigfile_path):
            fio_file = fio_files.create(big=True, disk_size=float(size))
        else:
            fio_file = fio_files.create(big=False, verify=True)

        test.data["file size"] = fio_file.file_size
        test.data["file size gb"] = fio_file.file_size / BYTES_IN_GB
        test.data["fio filepath"] = fio_file.os_filepath

    return fio_file


def test_end_info(test, start_info):

    with TestStep(
        test,
        "Test end info",
        "Read test end info and verify no errors or unexpected changes occurred during test.",
    ) as step:
        end_info = Info(test.suite.nvme, directory=step.directory, compare_info=start_info)

        rqmts.no_critical_warnings(step, end_info)
        rqmts.no_errorcount_change(step, end_info)
        rqmts.no_static_parameter_changes(step, end_info)
        rqmts.no_counter_parameter_decrements(step, end_info)

    return end_info


def start_state_samples(test, cmd_file="state"):

    with TestStep(test, "Sample info", "Start sampling SMART and power state info every second.") as step:
        info_samples = InfoSamples(
            test.suite.nvme,
            directory=step.directory,
            wait=False,
            samples=100000,
            interval=1000,
            cmd_file=cmd_file,
        )

    return info_samples


def idle_wait(test, wait_sec=180):

    with TestStep(test, "Idle wait", "Wait for idle temperature and garbage collection") as step:

        idle_info_samples = InfoSamples(
            nvme=test.suite.nvme,
            samples=wait_sec,
            interval=1000,
            cmd_file="logpage02",
            directory=step.directory,
        )
        rqmts.admin_commands_pass(step, idle_info_samples)
        rqmts.no_static_parameter_changes(step, idle_info_samples)
        rqmts.no_counter_parameter_decrements(step, idle_info_samples)
        rqmts.admin_command_avg_latency(step, idle_info_samples, test.suite.device["Average Admin Cmd Limit mS"])
        rqmts.admin_command_max_latency(step, idle_info_samples, test.suite.device["Maximum Admin Cmd Limit mS"])
