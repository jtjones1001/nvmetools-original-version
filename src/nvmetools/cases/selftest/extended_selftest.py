# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
import os
import platform
import time

from nvmetools import Info, TestCase, TestStep, fio, log, rqmts, steps
from nvmetools.apps.nvmecmd import Selftest
from nvmetools.support.conversions import as_int


def extended_selftest(suite):
    """Verify extended self-test functionality.

    The test verifies verifies the extended self-test passes and functions as expected.
    """
    with TestCase(suite, "Extended selftest", extended_selftest.__doc__) as test:

        test.data["linearity limit"] = suite.device["Linearity Limit"]
        test.data["idle wait sec"] = IDLE_WAIT_SEC = 180
        test.data["windows wa sec"] = WINDOWS_WA_SEC = 600

        # -----------------------------------------------------------------------------------------
        # Step : Read NVMe info at start of test
        # -----------------------------------------------------------------------------------------
        with TestStep(test, "Test start info", "Read NVMe information using nvmecmd") as step:
            step.stop_on_fail = True

            start_info = Info(nvme=suite.nvme, directory=step.directory)

            if start_info.parameters["Device Self-test Command"] != "Supported":
                test.skip("Device Self-test Command not supported.")

            # Note: EDSTT is nominal time and not the maximum time
            EDSTT = as_int(start_info.parameters["Extended Device Self-test Time (EDSTT)"])
            test.data["runtime limit"] = EDSTT

            rqmts.no_critical_warnings(step, start_info)
        # -----------------------------------------------------------------------------------------
        # Step: Create the file for fio to read and write
        # -----------------------------------------------------------------------------------------
        fio_file = steps.create_fio_small_file(test)

        # -----------------------------------------------------------------------------------------
        # Step : Run self-test standalone using nvmecmd
        # -----------------------------------------------------------------------------------------
        with TestStep(test, "Selftest standalone", "Run selftest without IO") as step:

            selftest = Selftest(
                nvme=suite.nvme,
                directory=step.directory,
                extended=True,
                limit_min=EDSTT,
            )
            rqmts.selftest_pass(step, selftest)
            rqmts.selftest_runtime(step, selftest)
            rqmts.selftest_monotonicity(step, selftest)
            rqmts.selftest_linearity(step, selftest)
            rqmts.selftest_poweron_hours(step, selftest)

            test.data["standalone"] = selftest.data

        # -----------------------------------------------------------------------------------------
        # Step : Run fio baseline for as long as self-test is expected to take
        # -----------------------------------------------------------------------------------------
        with TestStep(test, "IO standalone", "Run IO workload without selftest") as step:

            log.debug(f"Sleeping for {IDLE_WAIT_SEC} seconds before fio.")
            time.sleep(IDLE_WAIT_SEC)

            max_fio_runtime_sec = EDSTT * 60

            fio_args = [
                "--direct=1",
                "--thread",
                "--numjobs=1",
                f"--filesize={fio_file.file_size}",
                f"--filename={fio_file.filepath}",
                "--rw=randrw",
                "--iodepth=1",
                "--bs=4096",
                "--rwmixread=50",
                "--output-format=json",
                f"--output={os.path.join(step.directory,'fio.json')}",
                "--verify=crc32c",
                "--verify_dump=1",
                "--verify_state_save=0",
                "--verify_async=2",
                "--continue_on_error=verify",
                "--time_based",
                f"--runtime={max_fio_runtime_sec}",
                "--name=fio",
            ]
            fio_baseline = fio.RunFio(fio_args, step.directory, volume=suite.volume)
            rqmts.no_io_errors(step, fio_baseline)
            rqmts.no_data_corruption(step, fio_baseline)

        # -----------------------------------------------------------------------------------------
        # Windows workaround, need 10 min before can run self-test again.  Looks like this is
        # a driver bug as doesn't happen in linux or WinPE
        # -----------------------------------------------------------------------------------------
        if "Windows" == platform.system():
            if max_fio_runtime_sec < WINDOWS_WA_SEC:
                time.sleep(WINDOWS_WA_SEC - max_fio_runtime_sec)
                log.debug(f"Waiting {WINDOWS_WA_SEC} seconds for Windows workaround.")

        # -----------------------------------------------------------------------------------------
        # Step : Run fio and self-test concurrently
        # -----------------------------------------------------------------------------------------
        with TestStep(test, "Selftest and IO", "Run selftest and IO concurrently") as step:

            log.debug(f"Sleeping for {IDLE_WAIT_SEC} seconds before fio.")
            time.sleep(IDLE_WAIT_SEC)

            fio_args = [
                "--direct=1",
                "--thread",
                "--numjobs=1",
                f"--filesize={fio_file.file_size}",
                f"--filename={fio_file.filepath}",
                "--rw=randrw",
                "--iodepth=1",
                "--bs=4096",
                "--rwmixread=50",
                "--output-format=json",
                f"--output={os.path.join(step.directory,'fio.json')}",
                "--verify=crc32c",
                "--verify_dump=1",
                "--verify_state_save=0",
                "--verify_async=2",
                "--continue_on_error=verify",
                "--time_based",
                f"--runtime={max_fio_runtime_sec}",
                "--name=fio",
            ]
            fio_concurrent = fio.RunFio(fio_args, step.directory, volume=suite.volume, wait=False)
            time.sleep(1)

            selftest_concurrent = Selftest(
                nvme=suite.nvme,
                directory=step.directory,
                extended=True,
                limit_min=EDSTT,
            )

            fio_concurrent.stop()
            rqmts.no_io_errors(step, fio_concurrent)
            rqmts.no_data_corruption(step, fio_concurrent)

            rqmts.selftest_pass(step, selftest_concurrent)
            rqmts.selftest_runtime(step, selftest_concurrent)
            rqmts.selftest_monotonicity(step, selftest_concurrent)
            rqmts.selftest_linearity(step, selftest_concurrent, test.data["linearity limit"])
            rqmts.selftest_poweron_hours(step, selftest_concurrent)

            test.data["concurrent"] = selftest_concurrent.data

        # -----------------------------------------------------------------------------------------
        # Step : Read NVMe info and compare against starting info
        # -----------------------------------------------------------------------------------------
        steps.test_end_info(test, start_info)
