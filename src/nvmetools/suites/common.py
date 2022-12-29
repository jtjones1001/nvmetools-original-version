# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
import platform
import time

from nvmetools import TestSuite, tests


def firmware(args):
    """Verify the firmware update process."""

    with TestSuite("Firmware", firmware.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.firmware_update(suite)
        tests.firmware_activate(suite)
        tests.firmware_download(suite)
        tests.firmware_security(suite)

        tests.suite_end_info(suite, info)


def devinfo(args):
    """Read and verify start and end info for development."""
    with TestSuite("Info", devinfo.__doc__, **args) as suite:
        suite.stop_on_fail = False
        info = tests.suite_start_info(suite)
        tests.suite_end_info(suite, info)


def health(args):
    """Verifies drive health and wear with self-test diagnostic and SMART attributes.

    Short two minute test suite to verify drive is healthy.
    """
    with TestSuite("Check NVMe Health", health.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)
        tests.short_diagnostic(suite)
        tests.suite_end_info(suite, info)


def dev(args):
    """Short suite for test development."""
    with TestSuite("Development", dev.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)
        tests.admin_commands(suite)

        # SMART

        tests.background_smart(suite)
        tests.smart_data(suite)

        # Features

        tests.timestamp(suite)

        # Firmware

        tests.firmware_update(suite)
        tests.firmware_activate(suite)
        tests.firmware_download(suite)
        tests.firmware_security(suite)

        # Selftests

        tests.short_selftest(suite)
 

        # Performance tests

        tests.short_burst_performance(suite)
 

        tests.aspm_latency(suite)
        tests.nonop_power_times(suite)

        tests.data_compression(suite)
        tests.data_deduplication(suite)

        tests.read_buffer(suite)

        tests.big_file_writes(suite)
        tests.big_file_reads(suite)

        tests.short_burst_performance_full(suite)
   

        # Stress tests

        tests.high_bandwidth_stress(suite)
        tests.high_iops_stress(suite)
        tests.burst_stress(suite)
        tests.temperature_cycle_stress(suite)

        tests.suite_end_info(suite, info)

def funct(args):
    """Long test suite to verify functionality.

    Short test suite to verify drive health, wear, SMART, self-test and admin command reliability.
    """
    with TestSuite("Long functional", funct.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.admin_commands(suite)
        tests.background_smart(suite)
        tests.smart_data(suite)
        tests.timestamp(suite)

        tests.short_selftest(suite)

        tests.suite_end_info(suite, info)


def perf(args):
    """Test suite to measure NVMe IO performance.

    Measures IO peformance for several conditions including short and long bursts of reads
    and writes."""

    with TestSuite("Performance Test", perf.__doc__, **args) as suite:

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
    with TestSuite("Selftest", selftest.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.short_selftest(suite)

        if platform.system() == "Windows":
            time.sleep(600)
        tests.extended_selftest(suite)

        tests.suite_end_info(suite, info)


def short(args):
    """Short test suite to verify functionality.

    Short test suite to verify drive health, wear, SMART, self-test and admin command reliability.
    """
    with TestSuite("Short", short.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)

        tests.admin_commands(suite)
        tests.background_smart(suite)
        tests.smart_data(suite)
        tests.timestamp(suite)

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


def sink(args):
    """Development Test Suite with all NVMe Test Cases.

    Tests every possible feature including the kitchen sink.
    """

    with TestSuite("Kitchen Sink", sink.__doc__, **args) as suite:

        info = tests.suite_start_info(suite)
        tests.admin_commands(suite)

        # SMART

        tests.background_smart(suite)
        tests.smart_data(suite)

        # Features

        tests.timestamp(suite)

        # Firmware

        tests.firmware_update(suite)
        tests.firmware_activate(suite)
        tests.firmware_download(suite)
        tests.firmware_security(suite)

        # Selftests

        tests.short_selftest(suite)
        if platform.system() == "Windows":
            time.sleep(600)
        tests.extended_selftest(suite)

        # Performance tests

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

        # Stress tests

        tests.high_bandwidth_stress(suite)
        tests.high_iops_stress(suite)
        tests.burst_stress(suite)
        tests.temperature_cycle_stress(suite)

        tests.suite_end_info(suite, info)
