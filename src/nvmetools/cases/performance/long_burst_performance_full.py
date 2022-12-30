# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
from nvmetools import TestCase, steps
from nvmetools.cases.performance.long_burst_lib import _run_burst


def long_burst_performance_full(suite):
    """Measure performance of long bursts of IO reads and writes.

    Runs a long burst of IO on the volume specified.  This burst consists of:
      1) idle time to ensure device temperature and activity is stable
      2) read or write IO using fio
      3) idle to ensure device return to idle temperature

    The volume provided (volume) must exist on the physical device provided (nvme).
    """
    with TestCase(suite, "Long Burst Performance Full Drive", long_burst_performance_full.__doc__) as test:

        test.data["limits"] = suite.device["Long Burst Bandwidth (GB/s)"]
        test.data["random block size"] = RANDOM_BLOCK_SIZE = 4096
        test.data["random queue depth"] = RANDOM_QUEUE_DEPTH = 1
        test.data["sequential block size"] = SEQ_BLOCK_SIZE = 128 * 1024
        test.data["sequential queue depth"] = SEQ_QUEUE_DEPTH = 32

        # -----------------------------------------------------------------------------------------
        # Step : Read NVMe info.  Stop test if critical warnings found.
        # -----------------------------------------------------------------------------------------
        start_info = steps.test_start_info(test)

        # -----------------------------------------------------------------------------------------
        # Step: Create the file for fio to read and write
        # -----------------------------------------------------------------------------------------
        # This step will stop the test if cannot find or create the file.  The test requires the
        # big file. Since this is a stress test it must check the data integrity so the file will
        # be created with verify=True.  Note big files always have verify=True
        # -----------------------------------------------------------------------------------------
        fio_file = steps.create_fio_performance_file(test)

        # -----------------------------------------------------------------------------------------
        # Multiple Steps : Run the bursts with the target IO types
        # -----------------------------------------------------------------------------------------
        for rwmix in [0, 100]:
            _run_burst(
                test,
                suite.nvme,
                suite.volume,
                fio_file,
                "randrw",
                RANDOM_BLOCK_SIZE,
                RANDOM_QUEUE_DEPTH,
                rwmix,
                1,
            )
        for rwmix in [0, 100]:
            _run_burst(
                test,
                suite.nvme,
                suite.volume,
                fio_file,
                "rw",
                SEQ_BLOCK_SIZE,
                SEQ_QUEUE_DEPTH,
                rwmix,
                1,
            )
        # -----------------------------------------------------------------------------------------
        # Step : Read NVMe info and compare against starting info
        # -----------------------------------------------------------------------------------------
        # This test reads the full information and verifies no counter decrements, static parameter
        # changes, no critical warnings, and no error count increases.
        # -----------------------------------------------------------------------------------------
        steps.test_end_info(test, start_info)