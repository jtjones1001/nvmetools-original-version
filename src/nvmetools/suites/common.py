# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
import platform
import sys
import time

from nvmetools import TestSuite, tests
from nvmetools.support.conversions import is_admin


def firmware(args):
    """Test Suite to verify firmware features.

    Args:
        args: dictionary of NVMe parameters passed from testnvme command

    This suite runs Test Cases to verify firmware update, firmware activate, firmware download,
    and firmware security features.
    """
    with TestSuite("Firmware", firmware.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.firmware_update(suite)
        tests.firmware_activate(suite)
        tests.firmware_download(suite)
        tests.firmware_security(suite)

        tests.suite_end_info(suite, info)


def functional(args):
    """Test Suite to verify functional features.

    Args:
        args: dictionary of NVMe parameters passed from testnvme command

    This suite verifies the reliability and performance of the admin commands, SMART attributes,
    and timestamp.

    """
    with TestSuite("Functional", functional.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.admin_commands(suite)
        tests.background_smart(suite)
        tests.smart_data(suite)
        tests.timestamp(suite)

        tests.short_selftest(suite)

        tests.suite_end_info(suite, info)


def health(args):
    """Verifies drive health and wear with self-test diagnostic and SMART attributes.

    Check NVMe is a short Test Suite that verifies drive health and wear by running the drive
    diagnostic, reviewing SMART data and Self-Test history.
    """
    if platform.system() == "Windows" and not is_admin():
        print(" This script requires running with admin (root) privileges")
        sys.exit(1)

    with TestSuite("Check NVMe", health.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)
        tests.short_diagnostic(suite)
        tests.suite_end_info(suite, info)


def performance(args):
    """Test suite to measure NVMe IO performance.

    Measures IO peformance for several conditions including short and long bursts of reads
    and writes."""

    with TestSuite("Performance Test", performance.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.short_burst_performance(suite)
        tests.long_burst_performance(suite)

        tests.aspm_latency(suite)
        tests.nonop_power_times(suite)

        tests.data_compression(suite)
        tests.data_deduplication(suite)

        tests.read_buffer(suite)

        tests.big_file_writes(suite)
        tests.big_file_reads(suite)

        tests.short_burst_performance_full(suite)
        tests.long_burst_performance_full(suite)

        tests.suite_end_info(suite, info)


def selftest(args):
    """Short and extended self-test."""

    if platform.system() == "Windows" and not is_admin():
        print(" This script requires running with admin (root) privileges")
        sys.exit(1)

    with TestSuite("Selftest", selftest.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.short_selftest(suite)

        if platform.system() == "Windows":
            time.sleep(600)
        tests.extended_selftest(suite)

        tests.suite_end_info(suite, info)


def stress(args):
    """Test suite to verify drive reliaility under IO stress."""

    with TestSuite("Stress", stress.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.high_bandwidth_stress(suite)
        tests.high_iops_stress(suite)
        tests.burst_stress(suite)
        tests.temperature_cycle_stress(suite)

        tests.suite_end_info(suite, info)
