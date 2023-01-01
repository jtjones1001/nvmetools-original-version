# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
import os
import time

from nvmetools import TestCase, TestStep, fio, log, rqmts, steps


def high_iops_stress(suite, run_time_sec=180):
    """Verify drive reliability under high IOPS stress.

    The test verifies drive reliability under high IO per second stress.  High IOs are obtained
    doing reads and writes with small block sizes and large queue depth.  The goal of this test is
    to maximize the read and write IO and verify the drive is reliable.

    Args:
        suite:  Parent TestSuite instance
    """
    with TestCase(suite, "High iops stress", high_iops_stress.__doc__) as test:

        # -----------------------------------------------------------------------------------------
        # Step : Read NVMe info.  Stop test if critical warnings found.
        # -----------------------------------------------------------------------------------------
        start_info = steps.test_start_info(test)

        # -----------------------------------------------------------------------------------------
        # Step: Get the file for fio to read and write
        # -----------------------------------------------------------------------------------------
        fio_file = steps.get_fio_stress_file(test, start_info.parameters["Size"])

        # -----------------------------------------------------------------------------------------
        # Step : Start sampling SMART and Power State
        # -----------------------------------------------------------------------------------------
        # Start reading SMART and Power State info at a regular interval until stopped.  This data
        # can be used to plot temperature, bandwidth, power states, etc.  Only read SMART and Power
        # State feature to limit impact of reading info on the IO performance
        # -----------------------------------------------------------------------------------------
        info_samples = steps.start_state_samples(test)

        # -----------------------------------------------------------------------------------------
        # Step : Run high IOPS
        # -----------------------------------------------------------------------------------------
        # High IOPS is achieved using sequential addressing, high queue depth, and large block size.
        # The fio utility is used to run the IO.
        # -----------------------------------------------------------------------------------------
        with TestStep(test, "IO stress", "Run high IOPS stress with fio") as step:

            test.data["block size kib"] = 4
            test.data["queue depth"] = 8
            test.data["run time sec"] = run_time_sec
            test.data["sample delay sec"] = 30

            log.debug(f"Waiting {test.data['sample delay sec']} seconds to start IO")
            time.sleep(test.data["sample delay sec"])

            fio_args = [
                "--direct=1",
                "--thread",
                "--numjobs=1",
                f"--filesize={fio_file.file_size}",
                f"--filename={fio_file.filepath}",
                "--rw=randrw",
                "--rwmixread=50",
                f"--iodepth={test.data['queue depth'] }",
                f"--bs={test.data['block size kib']}k",
                "--verify_interval=4096",
                "--verify=crc32c",
                "--verify_dump=1",
                "--verify_state_save=0",
                "--verify_async=2",
                "--continue_on_error=verify",
                "--verify_backlog=1",
                f"--output={os.path.join(step.directory,'fio.json')}",
                "--output-format=json",
                "--time_based",
                f"--runtime={test.data['run time sec']}",
                "--name=fio",
            ]
            fio_result = fio.RunFio(fio_args, step.directory, suite.volume)
            rqmts.no_io_errors(step, fio_result)
            rqmts.no_data_corruption(step, fio_result)

            test.data["read"] = f"{fio_result.data_read_gb:0.1f} GB"
            test.data["read IOPS"] = f"{fio_result.read_ios/(test.data['run time sec']*1000):0.1f} K"
            test.data["written"] = f"{fio_result.data_write_gb:0.1f} GB"
            test.data["write IOPS"] = f"{fio_result.write_ios/(test.data['run time sec']*1000):0.1f} K"

            log.debug(f"Waiting {test.data['sample delay sec']} seconds to stop sampling")
            time.sleep(test.data["sample delay sec"])
        # -----------------------------------------------------------------------------------------
        # Step : Stop reading SMART and Power State information that was started above
        # -----------------------------------------------------------------------------------------
        with TestStep(test, "Verify samples", "Stop sampling and verify no sample errors") as step:
            info_samples.stop()

            rqmts.no_counter_parameter_decrements(step, info_samples)
            rqmts.no_errorcount_change(step, info_samples)

            test.data["min temp"] = info_samples.min_temp
            test.data["max temp"] = info_samples.max_temp
            test.data["time throttled"] = info_samples.time_throttled

        # -----------------------------------------------------------------------------------------
        # Step : Read NVMe info and compare against starting info
        # -----------------------------------------------------------------------------------------
        steps.test_end_info(test, start_info)
