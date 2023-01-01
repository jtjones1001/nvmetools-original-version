# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""This module provides classes to read and verify NVMe information.

The Info and InfoSamples classes read most of the NVMe information using the nvmecmd utility.
This utility uses the Admin Commands Get Log Page, Get Feature, Identify Controller, and Identify Namespace
to read drive information.  Some NVMe information, such as PCIe location and link info, are read
from the OS.
"""

import csv
import glob
import json
import os

from nvmetools.apps.nvmecmd import Read
from nvmetools.nvme_test import NvmeTest, verify_requirement
from nvmetools.settings import ADMIN_COMMAND_AVG_LIMIT_MS, ADMIN_COMMAND_MAX_LIMIT_MS, RqmtId
from nvmetools.support.conversions import BYTES_IN_GB, as_datetime, as_float, as_int
from nvmetools.support.log import log

MAX_TEMP_SENSORS = 8


class _NvmeMismatch(Exception):
    def __init__(self, nvme: int, file_nvme: str) -> None:
        self.code = 56
        self.nvmetools = True
        super().__init__(f"Info file NVMe: {file_nvme} doesn't match provided NVMe: {nvme}")


class Info:
    """Read and verify NVMe information."""

    def __init__(
        self,
        nvme: int = 0,
        directory: str = ".",
        verbose: bool = False,
        description: bool = False,
        from_file: str = None,
        cmd_file: str = "read",
    ) -> None:
        """Class to read, compare, and verify NVMe information.

        Args:
            nvme: NVMe number, from listnvme.
            directory: Directory to log results.
            verbose:  Verbose logging if True.
            description: Display parameter descriptions if True.
            from_file: Read info from this file if specified.
            cmd_file: Use this nvmecmd command file to read the information.


        This example reads NVMe 1 information and logs the files to the ./read_info directory.  It then
        displays the firmware and SMART information.

            .. code-block::

                nvme_info = Info(nvme=1, directory = './read_info')
                nvme_info.fw()
                nvme_info.smart()

        The cmd_file specifies the information to read.  For example, the logpage02 cmd file only reads
        SMART information using the Get Log Page 2 command.  The default is the read cmd file which reads
        all the information.  This example reads the SMART information from log page 2.

            .. code-block::

                nvme_info = Info(nvme=1, cmd_file="logpage02", directory = './smart_info')

        This example reads NVMe 2 at the start of a script, verifies the info requirements, then does some
        stuff like IO stress.  At the end of the script it reads the info again and compares against the info
        at the start.  If any static parameters changed or SMART counter decremented this fails.  It also
        verifies the requirements on the end info.

            .. code-block::

                start_info = Info(nvme=2, directory = './start_info)
                if start_info.verify() != 0:
                    ...  # handle error here

                ... # Do some stuff here

                end_info = Info(nvme=2, directory = './end_info')
                if (end_info.compare(start_info) + end_info.verify()) != 0:
                    ...  # handle error here

        Attributes:
            parameters: Dictionary of NVMe parameters where the key is the parameter name and the value is the\
            parameter value.
            return_code: Number of errors found, if no errors returns 0

        """
        self._nvme = nvme
        self._directory = directory
        self._description = description
        self._verbose = verbose

        if from_file is None:
            log.debug(f"Creating instance of Info by reading nvme device {nvme}")
            log.debug("")
            self._nvmecmd = Read(nvme, directory, cmd_file=cmd_file)
            self.return_code: int = self._nvmecmd.return_code
            self.info = self._nvmecmd.info
        else:
            log.debug(f"Creating instance of Info from file {from_file}")
            log.debug("")
            try:
                with open(from_file, "r") as file_object:
                    self.info = json.load(file_object)
                self.return_code: int = 0
            except Exception:
                raise Exception(f"Corrupted or missing nvmecmd file: {from_file}")

            file_nvme = int(self.info["nvme"]["description"].split(":")[0].split()[-1])
            if (nvme is not None) and (nvme != file_nvme):
                raise _NvmeMismatch(nvme, file_nvme)
            self._directory = os.path.dirname(from_file)

        summary_file = os.path.join(self._directory, "read.summary.json")
        if os.path.exists(summary_file):

            with open(summary_file, "r") as file_object:
                summary = json.load(file_object)

            command_times = []
            for entry in summary["command times"]:
                command_times.append(entry["time in ms"])

            self._data = {
                "avg_time": sum(command_times) / len(command_times),
                "max_time": max(command_times),
            }
        else:
            self._data = []

        parameters = self.info["nvme"]["parameters"]

        # Add some useful parameters here, may not exist depending on cmd file used

        try:
            throttle_time_sec = 0

            if parameters["Thermal Management Temperature 1 Time"]["value"] != "Disabled":
                throttle_time_sec += as_int(parameters["Thermal Management Temperature 1 Time"]["value"])
            if parameters["Thermal Management Temperature 2 Time"]["value"] != "Disabled":
                throttle_time_sec += as_int(parameters["Thermal Management Temperature 2 Time"]["value"])
            if parameters["Warning Composite Temperature Time"]["value"] != "Not Reported":
                throttle_time_sec += as_int(parameters["Warning Composite Temperature Time"]["value"]) * 60
            if parameters["Critical Composite Temperature Time"]["value"] != "Not Reported":
                throttle_time_sec += as_int(parameters["Critical Composite Temperature Time"]["value"]) * 60

            parameters["Time Throttled"] = {
                "compare type": "counter",
                "description": "Total time throttled in seconds",
                "name": "Time Throttled",
                "source": "Log Page 2",
                "value": f"{throttle_time_sec}",
            }
        except KeyError:
            pass

        try:
            ns1_active_lba = parameters["Namespace 1 Active LBA Format"]["value"]
            size_string = parameters[f"Namespace 1 LBA {ns1_active_lba} Data Size (LBADS)"]["value"]
            size_string = size_string.split("=")[-1].split(")")[0]

            parameters["Namespace 1 Active LBA Size"] = {
                "compare type": "exact",
                "description": "Size in bytes of the active LBA for Namespace 1",
                "name": "Namespace 1 Active LBA Size",
                "source": "Identify Namepsace",
                "value": size_string,
            }
        except KeyError:
            pass

        self.parameters: dict = {}
        for parameter in self.info["nvme"]["parameters"]:
            self.parameters[parameter] = self.info["nvme"]["parameters"][parameter]["value"]

        try:
            self.model = self.parameters["Model Number (MN)"].strip().replace(" ", "_")
        except KeyError:
            self.model = "N/A"

        try:
            self.size = int(self.parameters["Size"].split()[0]) * BYTES_IN_GB
        except KeyError:
            self.size = 0

    def _as_lat(self, name: str) -> str:
        if self.parameters[name] == "Not Reported":
            return " "
        return self.parameters[name].split("(")[0].strip()

    def _as_nop(self, name: str) -> str:
        if self.parameters[name] == "True":
            return "Yes"
        return " "

    def _as_pwr(self, name: str) -> str:
        if self.parameters[name] == "Not Reported":
            return " "
        return self.parameters[name].replace("Watts", "W")

    def _as_pwr2(self, name: str) -> str:
        return self.parameters[name].split("=")[1].strip(")")

    def _get_changes(self, start_parameters: dict, end_parameters: dict) -> int:
        # Gets the changes between start and end parameters
        self._static_parameters = 0
        self._dynamic_parameters = 0
        self._counter_parameters = 0
        self._static_mismatches = []
        self._counter_decrements = []
        self._counters = []

        for parameter in end_parameters:
            if end_parameters[parameter]["compare type"] == "exact":
                self._static_parameters += 1
                if end_parameters[parameter]["value"] != start_parameters[parameter]["value"]:
                    log.error(
                        f"-------> FAIL : Static parameter {parameter} changed from "
                        + f"{start_parameters[parameter]['value']}"
                        + f" to {end_parameters[parameter]['value']}"
                    )
                    self._static_mismatches.append(
                        {
                            "name": parameter,
                            "start": start_parameters[parameter]["value"],
                            "end": end_parameters[parameter]["value"],
                        }
                    )
            elif end_parameters[parameter]["compare type"] == "counter":
                self._counter_parameters += 1
                if parameter == "Data Read" or parameter == "Data Written":
                    end_value = as_float(end_parameters[parameter]["value"])
                    start_value = as_float(start_parameters[parameter]["value"])
                else:
                    end_value = as_int(end_parameters[parameter]["value"])
                    start_value = as_int(start_parameters[parameter]["value"])
                if end_value < start_value:
                    log.error(
                        f"-------> FAIL : Counter {parameter} decremented from "
                        + f"{start_parameters[parameter]['value']} "
                        + f"to {end_parameters[parameter]['value']}"
                    )
                    self._counter_decrements.append(
                        {
                            "name": parameter,
                            "start": start_parameters[parameter]["value"],
                            "end": end_parameters[parameter]["value"],
                        }
                    )
                self._counters.append(
                    {
                        "name": parameter,
                        "start": start_parameters[parameter]["value"],
                        "end": end_parameters[parameter]["value"],
                        "delta": end_value - start_value,
                    }
                )
            else:
                self._dynamic_parameters += 1

        return len(self._static_mismatches) + len(self._counter_decrements)

    def _save_delta_file(self, start_parameters: dict, end_parameters: dict) -> None:
        # Saves the start/end differences into csv fle

        delta_file = os.path.join(self._directory, "delta.csv")
        with open(delta_file, mode="w", newline="") as delta_csv_file:
            csv_writer = csv.writer(delta_csv_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(["Parameter", "Start", "End", "Delta"])
            for parameter in end_parameters:
                if end_parameters[parameter]["compare type"] == "counter":

                    if parameter == "Data Read" or parameter == "Data Written":
                        end_value = as_float(end_parameters[parameter]["value"])
                        start_value = as_float(start_parameters[parameter]["value"])
                    else:
                        end_value = as_int(end_parameters[parameter]["value"])
                        start_value = as_int(start_parameters[parameter]["value"])

                    csv_writer.writerow(
                        [
                            parameter,
                            start_parameters[parameter]["value"],
                            end_parameters[parameter]["value"],
                            end_value - start_value,
                        ]
                    )

    def _verify_compare_requirements(
        self, test: NvmeTest = None, verify_poh: bool = False, verify_no_throttle: bool = False
    ) -> int:
        # verify compare requirements, no static changes, counter decrements, errors increasing, throttling, etc.
        failed_verifications = 0
        failed_verifications += verify_requirement(
            RqmtId.NO_STATIC_PARAMETER_CHANGE,
            name="Static parameters, such as Model Number, shall not change",
            limit=0,
            value=len(self._static_mismatches),
            passed=(len(self._static_mismatches) == 0),
            test=test,
        )
        failed_verifications += verify_requirement(
            RqmtId.NO_COUNTER_PARAMETER_DECREMENT,
            name="SMART counters, such as Data Written, shall not reset or decrement",
            limit=0,
            value=len(self._counter_decrements),
            passed=(len(self._counter_decrements) == 0),
            test=test,
        )
        failed_verifications += verify_requirement(
            RqmtId.NO_ERROR_INCREASE,
            name="Media and Data Integrity Errors shall not increase",
            limit=0,
            value=self._media_errors,
            passed=(self._media_errors == 0),
            test=test,
        )
        if verify_no_throttle:
            failed_verifications += verify_requirement(
                RqmtId.NO_THROTTLE,
                name="Thermal throttle time shall not increase",
                limit=0,
                value=self._time_throttled,
                passed=(self._media_errors == 0),
                test=test,
            )
        if verify_poh:
            failed_verifications += verify_requirement(
                RqmtId.PWR_ON_HOURS_CHANGE,
                name="Change in Power On Hours shall be within 1 hour of actual time change",
                limit=1,
                value=f"{self._poh_delta:0.2f} Hours",
                passed=(self._poh_delta < 1),
                test=test,
            )
        return failed_verifications

    def compare(
        self, start: dict, test: NvmeTest = None, verify_poh: bool = False, verify_no_throttle: bool = False
    ) -> int:
        """Compare two sets of NVMe information.

        Args:
            start: Dictionary with start NVMe information to compare against.
            test: Instance of NvmeTest to update.
            verify_poh:  Verify Power On Hours delta if True.
            verify_no_throttle: Verify no throttling occurred if True.

        Returns:
            The number of errors found.

        This method verifies no static parameters changed, no SMART counters decremented, and no errors
        increased between the two sets of information.  If verify_poh is True then verifies the system
        time difference matches the drive power on hour difference.  If verify_no_throttle is True then
        verifies no throttling occurred.

        This example reads NVMe 2 at the start of a script and then does some stuff.   Later it reads the info
        again and compares against the start info.

            .. code-block::

                start_info = Info(nvme=2, directory = './start_info)

                ... # Do some stuff here

                end_info = Info(nvme=2, directory = './end_info')

                if end_info.compare(start_info) != 0:
                    ...  # handle error here
        """
        compare_errors = 0
        end = self.info
        start_parameters = start["nvme"]["parameters"]
        end_parameters = end["nvme"]["parameters"]
        self._save_delta_file(start_parameters, end_parameters)

        self._media_errors = as_int(end_parameters["Media and Data Integrity Errors"]["value"]) - as_int(
            start_parameters["Media and Data Integrity Errors"]["value"]
        )
        self._time_throttled = int(end_parameters["Time Throttled"]["value"]) - int(
            start_parameters["Time Throttled"]["value"]
        )
        self._power_on_delta = as_int(end_parameters["Power On Hours"]["value"]) - as_int(
            start_parameters["Power On Hours"]["value"]
        )
        actual_delta = as_datetime(end["_metadata"]["date"]) - as_datetime(start["_metadata"]["date"])
        self._poh_delta = abs(actual_delta.total_seconds() / 3600 - self._power_on_delta)

        verify_no_throttle = verify_no_throttle and "Time Throttled" in end_parameters
        verify_poh = verify_poh and "Power On Hours" in end_parameters

        compare_errors += self._get_changes(start_parameters, end_parameters)
        compare_errors += self._verify_compare_requirements(test, verify_poh, verify_no_throttle)

        if test is not None:
            test.data["static parameters"] = self._static_parameters
            test.data["dynamic parameters"] = self._dynamic_parameters
            test.data["counter parameters"] = self._counter_parameters

            test.data["static mismatches"] = self._static_mismatches
            test.data["counter decrements"] = self._counter_decrements
            test.data["counters"] = self._counters
            test.data["media error increase"] = self._media_errors
            test.data["date start read"] = start["_metadata"]["date"]
            test.data["date end read"] = end["_metadata"]["date"]

            test.data["power on delta"] = self._poh_delta

        return compare_errors

    def _list_param(self, name: str, value: str, description: str = "") -> None:
        if not self._description:
            log.info(f"   {name.strip():50} {value.strip():35}")
        else:
            log.info(f"   {name.strip():50} {value.strip():35}    {description}")

    def _log_header(self, title: str, width: int = 90, indent: int = 2) -> None:
        log.info(" " * indent + "-" * width)
        log.info(" " * (indent + 1) + title)
        log.info(" " * indent + "-" * width)

    def _log_param(self, name: str) -> None:
        value = self.parameters[name]
        description = self.info["nvme"]["parameters"][name]["description"]
        self._list_param(name, value, description)

    def _show(self, as_list: bool = False) -> None:
        self._log_header(f"NVME DRIVE {self._nvme}  ({self.parameters['OS Location'].split()[-1]})")

        self._list_param(
            "Vendor",
            self.parameters["Subsystem Vendor"],
            self.info["nvme"]["parameters"]["Subsystem Vendor"]["description"],
        )
        self._log_param("Model Number (MN)")
        self._log_param("Serial Number (SN)")
        self._log_param("Size")
        self._log_param("Version (VER)")
        log.info("")

        self.namespace()
        self.fw()
        self.features()
        self.errors()
        self.smart(as_list)
        self.power(as_list)
        self.pci(as_list)

    def show_all(self, cmd_filter: str = None) -> None:
        """List all NVMe parameters.

        Args:
            cmd_filter:  Display only parameters that contain this string.  Case sensitive.

        This example reads NVMe 2 and displays all parameters with power in their name.

            .. code-block::

                start_info = Info(nvme=2, directory = './start_info)
                start_info.show_all("power")
        """
        log.info("")
        for param in self.parameters:
            if cmd_filter is None or cmd_filter in param:
                self._log_param(param)

    def errors(self) -> None:
        """Display NVMe error information."""
        log.info("")
        self._log_param("Critical Warnings")
        self._log_param("Media and Data Integrity Errors")
        self._log_param("Number Of Failed Self-Tests")
        self._log_param("Number of Error Information Log Entries")

    def features(self) -> None:
        """Display NVMe features."""
        log.info("")

        self._list_param(
            "Maximum Data Transfer Size (MDTS)",
            self._as_pwr2("Maximum Data Transfer Size (MDTS)"),
            self.info["nvme"]["parameters"]["Maximum Data Transfer Size (MDTS)"]["description"],
        )

        # Timestamp add later
        if self.parameters["Host Memory Buffer Preferred Size (HMPRE)"] != "Not Supported":

            self._log_param("Enable Host Memory (EHM)")
            if self.parameters["Enable Host Memory (EHM)"] == "Enabled":
                self._list_param(
                    "Host Memory Buffer Size (HSIZE)",
                    self.parameters["Host Memory Buffer Size (HSIZE)"] + " pages",
                    self.info["nvme"]["parameters"]["Host Memory Buffer Size (HSIZE)"]["description"],
                )

        self._log_param("Volatile Write Cache (VWC)")
        if self.parameters["Volatile Write Cache (VWC)"] == "Supported":
            self._log_param("Volatile Write Cache Enable (WCE)")

    def fw(self) -> None:
        """Display detailed firmware information."""
        log.info("")

        self._log_param("Firmware Revision (FR)")
        self._log_param("Firmware Slots")
        self._log_param("Firmware Activation Without Reset")

        if self._verbose:
            self._log_param("Firmware Commit and Image Download Commands")
            self._log_param("Firmware Update Granularity (FWUG)")
            self._log_param("Firmware Activation Notices")
            self._log_param("Firmware Activation Notices Enable")
            self._log_param("Maximum Time for Firmware Activation (MTFA)")

            self._log_param("Firmware Active Slot")
            self._log_param("Firmware Pending Slot")
            self._log_param("Firmware Slot 1 Read Status")

            number_slots = int(self.parameters["Firmware Slots"])

            for slot in range(1, (1 + number_slots)):
                self._log_param(f"Firmware Slot {slot} Revision")

    def show_hex(self) -> None:
        """Display results from NVMe Admin Commands in hex format."""
        for command in self.info["raw hex data"]:
            self._log_header(command, width=106)
            for line in self.info["raw hex data"][command]:
                log.info("   " + line)

    def show_list(self) -> None:
        """Display NVMe information as a list."""
        self._show(as_list=True)

    def namespace(self) -> None:
        """Display NVMe namespace information."""
        self._log_param("Number of Namespaces (NN)")
        self._log_param("Namespace 1 Size")
        self._log_param("Namespace 1 Active LBA Size")

        self._list_param(
            "Namespace 1 EUID",
            self.parameters["Namespace 1 IEEE Extended Unique Identifier (EUI64)"],
            self.info["nvme"]["parameters"]["Namespace 1 IEEE Extended Unique Identifier (EUI64)"]["description"],
        )
        self._list_param(
            "Namespace 1 NGUID",
            self.parameters["Namespace 1 Globally Unique Identifier (NGUID)"],
            self.info["nvme"]["parameters"]["Namespace 1 Globally Unique Identifier (NGUID)"]["description"],
        )

    def pci(self, as_list: bool = False) -> None:
        """Display PCIe information.

        Args:
            as_list: Display information as a list.  Default is display in a table.
        """
        log.info("")

        if as_list:
            if self._verbose:
                self._log_param("PCI Vendor ID (VID)")
                self._log_param("PCI Device ID")
                self._log_param("PCI Width")
                self._log_param("PCI Speed")
                self._log_param("PCI Rated Width")
                self._log_param("PCI Rated Speed")
                self._log_param("PCI Location")
                self._log_param("Root PCI Vendor ID")
                self._log_param("Root PCI Device ID")
                self._log_param("Root PCI Location")
            else:
                self._log_param("PCI Width")
                self._log_param("PCI Speed")
                self._log_param("PCI Location")
        else:

            self._log_param("PCI Width")
            self._log_param("PCI Speed")
            self._log_param("PCI Rated Width")
            self._log_param("PCI Rated Speed")
            log.info("")
            self._log_header(f"{'PCI':12}{'Vendor':20}{'Vendor ID':13}{'Device ID':13}Location")

            log.info(
                f"{'   Endpoint':15}{self.parameters['Controller Vendor']:20}"
                + f"{self.parameters['PCI Vendor ID (VID)']:13}"
                + f"{self.parameters['PCI Device ID']:13}"
                + f"{self.parameters['PCI Location']} "
            )
            log.info(
                f"{'   Root':15}{' ':20}{self.parameters['Root PCI Vendor ID']:13}"
                + f"{self.parameters['Root PCI Device ID']:13}"
                + f"{self.parameters['Root PCI Location']} "
            )

    def _list_states(self, name: str) -> None:
        log.info("")
        states = int(self.parameters["Number of Power States Support (NPSS)"])
        for state in range(states):
            self._log_param(f"Power State {state} {name}")

    def power(self, as_list: bool = False) -> None:
        """Display power information.

        Args:
            as_list: Display information as a list.  Default is display in a table.
        """
        states = int(self.parameters["Number of Power States Support (NPSS)"])
        if as_list:

            self._list_states("Maximum Power (MP)")

            if self._verbose:
                self._list_states("Active Power (ACTP)")
                self._list_states("Idle Power (IDLP)")

                self._list_states("Entry Latency (ENLAT)")
                self._list_states("Exit Latency (EXLAT)")

                self._list_states("Non-Operational State (NOPS)")

                self._list_states("Relative Read Latency (RRL)")
                self._list_states("Relative Read Throughput (RRT)")
                self._list_states("Relative Write Latency (RWL)")
                self._list_states("Relative Write Throughput (RWT)")

        else:

            log.info("")
            title = "State   NOP    Max         Active      Idle        Entry Latency   Exit Latency"
            self._log_header(title)

            for state in range(states):
                row = f"   {state:<8}"
                row += f"{self._as_nop(f'Power State {state} Non-Operational State (NOPS)'):7}"
                row += f"{self._as_pwr(f'Power State {state} Maximum Power (MP)'):12}"
                row += f"{self._as_pwr(f'Power State {state} Active Power (ACTP)'):12}"
                row += f"{self._as_pwr(f'Power State {state} Idle Power (IDLP)'):12}"
                row += f"{self._as_lat(f'Power State {state} Entry Latency (ENLAT)'):16}"
                row += f"{self._as_lat(f'Power State {state} Exit Latency (EXLAT)')}"
                log.info(row)
        log.info("")

        try:
            self._log_param("Autonomous Power State Transition")
            self._log_param("Autonomous Power State Transition Enable (APSTE)")
        except BaseException:
            self._list_param("Autonomous Power State Transition", "Not Supported"),
            ""
        try:
            self._log_param("Non-Operational Power State Permissive Mode")
            self._log_param("Non-Operational Power State Permissive Mode Enable (NOPPME)")
        except BaseException:
            self._list_param("Non-Operational Power State Permissive Mode", "Not Supported", "")

    def show(self) -> None:
        """Display NVMe information."""
        self._show()

    def smart(self, as_list: bool = False) -> None:
        """Display SMART information.

        Args:
            as_list: Display information as a list.  Default is display in a table.
        """
        log.info("")
        self.temperature(as_list=as_list)
        self._log_param("Available Spare")
        self._log_param("Available Spare Threshold")
        self._log_param("Controller Busy Time")
        self._log_param("Data Read")
        self._log_param("Data Written")
        self._log_param("Host Read Commands")
        self._log_param("Host Write Commands")
        self._log_param("Percentage Used")
        self._log_param("Power On Hours")
        self._log_param("Power Cycles")
        self._log_param("Unsafe Shutdowns")

    def temperature(self, as_list: bool = False) -> None:
        """Display temperature information.

        Args:
            as_list: Display information as a list.  Default is display in a table.
        """
        total_time = as_int(self.parameters["Time Throttled"])
        ttt = (
            f"{total_time/3600:,.3f} Hours " + f"({total_time/(as_int(self.parameters['Power On Hours'])):,.1f} %)"
        )
        if as_list:

            # Temperature Readings

            self._log_param("Composite Temperature")

            for index in range(MAX_TEMP_SENSORS):
                if f"Temperature Sensor {index}" in self.parameters:
                    self._log_param(f"Temperature Sensor {index}")

            # Thresholds

            log.info("")
            self._log_param("Thermal Management Temperature 1 (TMT1)")
            self._log_param("Thermal Management Temperature 2 (TMT2)")
            self._log_param("Warning Composite Temperature Threshold (WCTEMP)")
            self._log_param("Critical Composite Temperature Threshold (CCTEMP)")

            # Throttle Information

            log.info("")

            self._list_param(
                "Total Throttle Time",
                ttt,
                "Total time device is throttled for all levels, % time is % of Power-On Hours",
            )

            self._log_param("Thermal Management Temperature 1 Time")
            self._log_param("Thermal Management Temperature 2 Time")
            self._log_param("Warning Composite Temperature Time")
            self._log_param("Critical Composite Temperature Time")

            if self._verbose:
                log.info("")
                self._log_param("Thermal Management Temperature 1 Count")
                self._log_param("Thermal Management Temperature 2 Count")

                log.info("")
                self._log_param("Composite Temperature Under Threshold")

                for index in range(MAX_TEMP_SENSORS):
                    if f"Temperature Sensor {index}" in self.parameters:
                        self._log_param(f"Temperature Sensor {index} Under Threshold")

                log.info("")
                self._log_param("Composite Temperature Over Threshold")

                for index in range(MAX_TEMP_SENSORS):
                    if f"Temperature Sensor {index}" in self.parameters:
                        self._log_param(f"Temperature Sensor {index} Over Threshold")

                # Features
                log.info("")
                self._log_param("Host Controlled Thermal Management (HCTMA)")
                self._log_param("Minimum Thermal Management Temperature (MNTMT)")
                self._log_param("Maximum Thermal Management Temperature (MXTMT)")
        else:

            # Temperature table

            title = f"{'Temperature':18}{'Value':15}{'Under Threshold':20}{'Over Threshold'}"
            self._log_header(title, width=70)

            log.info(
                f"   {'Composite':18}"
                + f"{self.parameters['Composite Temperature']:15}"
                + f"{self.parameters['Composite Temperature Under Threshold']:20}"
                + f"{self.parameters['Composite Temperature Over Threshold']}"
            )
            for index in range(MAX_TEMP_SENSORS):
                if f"Temperature Sensor {index}" in self.parameters:
                    name = f"Sensor {index}"
                    value = self.parameters[f"Temperature Sensor {index}"]
                    under = self.parameters[f"Temperature Sensor {index} Under Threshold"]
                    over = self.parameters[f"Temperature Sensor {index} Over Threshold"]
                    log.info(f"   {name:18}{value:15}{under:20}{over}")

            # Throttle table

            log.info("")
            title = f"{'Throttle':14}{'Total':12}{'TMT1':12}{'TMT2':12}{'WCTEMP':12}{'CCTEMP':12}"
            self._log_header(title, width=72)

            log.info(
                f"   {'Time (Hrs)':14}"
                + f"{total_time/3600:<12,.3f}"
                + f"{as_int(self.parameters['Thermal Management Temperature 1 Time'])/3600:<12,.3f}"
                + f"{as_int(self.parameters['Thermal Management Temperature 2 Time'])/3600:<12,.3f}"
                + f"{as_int(self.parameters['Warning Composite Temperature Time'])/3600:<12,.3f}"
                + f"{as_int(self.parameters['Critical Composite Temperature Time'])/3600:<12,.3f}"
            )
            log.info(
                f"   {'Threshold':14}"
                + f"{' ':12}"
                + f"{self.parameters['Thermal Management Temperature 1 (TMT1)']:12}"
                + f"{self.parameters['Thermal Management Temperature 2 (TMT2)']:12}"
                + f"{self.parameters['Warning Composite Temperature Threshold (WCTEMP)']:12}"
                + f"{self.parameters['Critical Composite Temperature Threshold (CCTEMP)']:12}"
            )
            log.info(
                f"   {'Count':14}"
                + f"{' ':12}"
                + f"{self.parameters['Thermal Management Temperature 1 Count']:12}"
                + f"{self.parameters['Thermal Management Temperature 2 Count']:12}"
                + f"{'--':12}"
                + f"{'--':12}"
            )

        log.info("")

    def verify(
        self, test: NvmeTest = None, start: dict = None, verify_poh: bool = False, verify_no_throttle: bool = False
    ) -> int:
        """Verify requirements for NVMe information.

        Args:
            start: Dictionary with start NVMe information to compare against.
            test: Instance of NvmeTest to update.
            verify_poh:  Verify Power On Hours delta if True.
            verify_no_throttle: Verify no throttling occurred if True.

        Returns:
            Number of errors, if no errors returns 0.

        This method verifies no critical warnings are asserted.  If the start information is provided
        the compare method is also called.

        This example reads NVMe 2 at the start of a script, verifies the info requirements, then does some
        stuff like IO stress.  At the end of the script it reads the info again, verifies no errors and
        compares against the info at the start.

            .. code-block::

                start_info = Info(nvme=2, directory = './start_info)

                ... # Do some stuff here

                end_info = Info(nvme=2, directory = './end_info')

                if end_info.verify(start_info) != 0:
                    ...  # handle error here
        """
        failed_verifications = 0

        failed_verifications += verify_requirement(
            RqmtId.NO_CRITICAL_WARNINGS,
            name="There shall be no critical warnings",
            limit="No",
            value=self.parameters["Critical Warnings"],
            passed=(self.parameters["Critical Warnings"] == "No"),
            test=test,
        )
        if "avg_time" in self._data:

            failed_verifications += verify_requirement(
                RqmtId.ADMIN_COMMAND_AVG_LATENCY,
                name=f"Admin Command average latency shall be less than {ADMIN_COMMAND_AVG_LIMIT_MS} mS",
                limit=ADMIN_COMMAND_AVG_LIMIT_MS,
                value=f"{self._data['avg_time']:0.2f} mS",
                passed=(self._data["avg_time"] < ADMIN_COMMAND_AVG_LIMIT_MS),
                test=test,
            )

        if "max_time" in self._data:

            failed_verifications += verify_requirement(
                RqmtId.ADMIN_COMMAND_MAX_LATENCY,
                name=f"Admin Command maximum latency shall be less than {ADMIN_COMMAND_MAX_LIMIT_MS} mS",
                limit=ADMIN_COMMAND_MAX_LIMIT_MS,
                value=f"{self._data['max_time']:0.2f} mS",
                passed=(self._data["max_time"] < ADMIN_COMMAND_MAX_LIMIT_MS),
                test=test,
            )

        if start is not None:
            failed_verifications += self.compare(
                start.info,
                test,
                verify_poh=verify_poh,
                verify_no_throttle=verify_no_throttle,
            )
        return failed_verifications


class InfoSamples:
    """Read and compare multiple samples of NVMe information."""

    def __init__(
        self,
        nvme: int = 0,
        directory: str = ".",
        samples: int = 1,
        interval: int = 0,
        cmd_file: str = "read",
        wait: bool = True,
    ) -> None:
        """Class to read multiple samples of NVMe information.

        Args:
            nvme: NVMe number, from listnvme.
            directory: Directory to log results.
            samples:  Number of samples to read.
            interval: Time interval between samples in mS.
            cmd_file: The nvmecmd command file to use.
            wait: If True waits for all samples to complete.

        The cmd_file specifies the information to read.  For example, the logpage02 cmd file only reads
        SMART information using the Get Log Page 2 command.

        The wait flag determines if the instance waits until sampling is complete or immediately continues.
        This allows sampling while other activity, such as IO stress, is done in parallel. The wait() or
        stop() methods can be called to stop sampling.

        The verify mehtod verifies the sample requirements such as Admin Commands must complete without
        error and within the time limit. It also verifies NVMe information does not unexpectedly change
        across samples.

        This example reads NVMe 0 information 100 times with 2 seconds between reads and then prints
        the minimum and maximum temperatures across all samples.

            .. code-block::

                samples = InfoSamples(nvme=0, samples=100, interval=2000)
                print(samples.min_temp)
                print(samples.max_temp)

        Attributes:
            data_written: String with total data written across all samples in GB (e.g. '4.654 GB')
            data_read: String with total data read across all samples in GB
            max_temp: String with maximum temperature read across all samples in Celsius (e.g. '81 C')
            min_temp: String with minimum temperature read across all samples in Celsius (e.g. '27 C')
            return_code: Number of errors, if no errors then 0
            time_throttled:  String with time throttled in seconds (e.g. '14 sec')

        """
        log.debug(f"Reading {samples} samples of nvme device {nvme}")

        self._nvme = nvme
        self._directory = directory
        self._data = {}
        self._data["interval ms"] = interval
        self._data["samples"] = samples

        self._nvmecmd = Read(
            nvme=nvme,
            directory=directory,
            samples=samples,
            interval=interval,
            cmd_file=cmd_file,
            wait=False,
        )
        if wait:
            self.wait()

    def _save_admin_times_file(self) -> None:
        # save admin command execution times into admin_command_times.csv
        self._total_commands = len(self._summary["command times"])
        self._total_command_fails = 0

        each_command = {}
        command_times = []

        csv_file = os.path.join(self._directory, "admin_command_times.csv")

        with open(csv_file, mode="w", newline="") as times_csv_file:
            csv_writer = csv.writer(times_csv_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(["Timestamp", "Command", "Time(mS)", "ReturnCode", "Bytes"])

            cmd_filter = None
            for entry in self._summary["command times"]:
                if cmd_filter is None or cmd_filter == entry["admin command"]:
                    command_times.append(entry["time in ms"])
                    if entry["admin command"] not in each_command:
                        each_command[entry["admin command"]] = []
                    each_command[entry["admin command"]].append(entry["time in ms"])
                    if int(entry["return code"]) != 0:
                        self._total_command_fails += 1
                    csv_writer.writerow(
                        [
                            entry["timestamp"],
                            entry["admin command"],
                            entry["time in ms"],
                            entry["return code"],
                            entry["bytes returned"],
                        ]
                    )

        # display the admin command times

        self._data["avg_time"] = sum(command_times) / len(command_times)
        self._data["max_time"] = max(command_times)
        self._data["read_fails"] = 0
        self._data["compare_fails"] = 0
        self._command_types = len(each_command)
        self._counter_mismatches = self._summary["read details"]["counter mismatches"]
        self._static_mismatches = self._summary["read details"]["static mismatches"]

        for sample in self._summary["read details"]["sample"]:
            if sample["message"].find("failed read") != -1:
                self._data["read_fails"] += 1

            if sample["message"].find("failed compare") != -1:
                self._data["compare_fails"] += 1

        log.verbose("")
        log.verbose("Admin command times as measured by InfoSamples:")
        log.verbose("")
        for command in each_command:
            average = sum(each_command[command]) / len(each_command[command])
            log.verbose(
                f"\t     {command:35} Avg: {average:6.2f}mS \
                Min: {min(each_command[command]):6.2f}mS \
                Max: {max(each_command[command]):6.2f}mS \
                Count: {len(each_command[command]):6}"
            )

        if len(each_command) > 1:
            average = sum(command_times) / len(command_times)
            log.verbose(" ")
            log.verbose(
                f"\t     {'All Commands':35} Avg: {average:6.2f}mS \
                Min: {min(command_times):6.2f}mS \
                Max: {max(command_times):6.2f}mS \
                Count: {len(command_times):6}"
            )
        log.verbose("")

    def _save_attributes_file(self) -> None:
        # save SMART attributes to nvme_attributes.csv
        filepath = os.path.join(self._directory, "nvme_attributes.csv")

        start_time = as_datetime(self._summary["read details"]["sample"][0]["timestamp"])
        last_read = as_float(self._summary["read details"]["sample"][0]["Data Read"])
        last_write = as_float(self._summary["read details"]["sample"][0]["Data Written"])

        first_read = as_float(self._summary["read details"]["sample"][0]["Data Read"])
        first_write = as_float(self._summary["read details"]["sample"][0]["Data Written"])

        first_wctemp = as_int(self._summary["read details"]["sample"][0]["Warning Composite Temperature Time"])
        first_cctemp = as_int(self._summary["read details"]["sample"][0]["Critical Composite Temperature Time"])
        first_tmt1 = as_int(self._summary["read details"]["sample"][0]["Thermal Management Temperature 1 Time"])
        first_tmt2 = as_int(self._summary["read details"]["sample"][0]["Thermal Management Temperature 2 Time"])

        composite_temperature = []

        with open(filepath, mode="w", newline="") as file_object:
            csv_writer = csv.writer(file_object, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(
                [
                    "Timestamp",
                    "Temperature",
                    "Data Written",
                    "Data Read",
                    "Data Written Delta",
                    "Data Read Delta",
                    "Power State",
                    "Percentage Used",
                    "WCTEMP",
                    "CCTEMP",
                    "TMT1",
                    "TMT2",
                ]
            )
            for sample in self._summary["read details"]["sample"]:
                if "Current Power State" in sample:
                    power_state = as_int(sample["Current Power State"])
                else:
                    power_state = "N/A"
                composite_temperature.append(as_int(sample["Composite Temperature"]))
                csv_writer.writerow(
                    [
                        (as_datetime(sample["timestamp"]) - start_time).total_seconds(),
                        as_int(sample["Composite Temperature"]),
                        as_float(sample["Data Written"]) - first_write,
                        as_float(sample["Data Read"]) - first_read,
                        as_float(sample["Data Written"]) - last_write,
                        as_float(sample["Data Read"]) - last_read,
                        power_state,
                        as_int(sample["Percentage Used"]),
                        as_int(sample["Warning Composite Temperature Time"]) - first_wctemp,
                        as_int(sample["Critical Composite Temperature Time"]) - first_cctemp,
                        as_int(sample["Thermal Management Temperature 1 Time"]) - first_tmt1,
                        as_int(sample["Thermal Management Temperature 2 Time"]) - first_tmt2,
                    ]
                )
                last_read = as_float(sample["Data Read"])
                last_write = as_float(sample["Data Written"])

        # Assign the class temp attributes

        self.min_temp: str = f"{min(composite_temperature)} C"
        self.max_temp: str = f"{max(composite_temperature)} C"

    def _save_delta_file(self) -> None:
        # calculate differences between first and last sample SMART counters and save in sample_delta.csv

        first_sample_file = os.path.join(self._directory, "nvme.info.sample-1.json")
        self._first_sample = Info(nvme=None, from_file=first_sample_file)

        sample_files = os.path.join(self._directory, "nvme.info.*.json")
        last_sample_file = sorted(filter(os.path.isfile, glob.glob(sample_files)))[-1]
        self._last_sample = Info(self._nvme, from_file=last_sample_file)

        start_parameters = self._first_sample.info["nvme"]["parameters"]
        end_parameters = self._last_sample.info["nvme"]["parameters"]

        with open(os.path.join(self._directory, "sample_delta.csv"), mode="w", newline="") as delta_csv_file:
            csv_writer = csv.writer(delta_csv_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(["Parameter", "Start", "End", "Delta"])
            for parameter in end_parameters:
                if end_parameters[parameter]["compare type"] == "counter":

                    if parameter == "Data Read" or parameter == "Data Written":
                        end_value = as_float(end_parameters[parameter]["value"])
                        start_value = as_float(start_parameters[parameter]["value"])
                    else:
                        end_value = as_int(end_parameters[parameter]["value"])
                        start_value = as_int(start_parameters[parameter]["value"])

                    csv_writer.writerow(
                        [
                            parameter,
                            start_parameters[parameter]["value"],
                            end_parameters[parameter]["value"],
                            end_value - start_value,
                        ]
                    )

                    # Assign class attributes

                    if parameter == "Data Read":
                        self.data_read: str = f"{float(end_value - start_value):.3f} GB"
                    elif parameter == "Data Written":
                        self.data_written = f"{float(end_value - start_value):.3f} GB"
                    elif parameter == "Time Throttled":
                        self.time_throttled = f"{int(end_value - start_value)} sec"

    def wait(self) -> None:
        """Wait for samples to be read.

        When sampling was started with wait=False and the sampling has not completed, this function
        waits until sampling has completed.

        This example reads NVMe 0 information 1000 times with 1 seconds between reads.

            .. code-block::

                samples = InfoSamples(nvme=0, samples=1000, interval=1000, wait=False)
                ...                         # Do some stuff like IO stress
                samples.wait()              # Then wait for samples to finish
        """
        self._nvmecmd.wait()
        self.return_code: int = self._nvmecmd.return_code

        self.info = self._nvmecmd.info
        self.parameters = self.info["nvme"]["parameters"]
        self._summary = self._nvmecmd.summary

        # create the summary log fies

        self._save_delta_file()
        self._save_attributes_file()
        self._save_admin_times_file()

    def stop(self) -> None:
        """Stop sampling gracefully.

        When sampling is started with wait=False and has not completed this method stops sampling gracefully
        to allow log files to be created.

        This example reads NVMe 0 information every 1 second until stopped.  The samples parameter is set
        very high so it will not complete in a reasonable time.  After some stuff is done the sampling is
        stopped.

            .. code-block::

                samples = InfoSamples(nvme=0, samples=1000000, interval=1000, wait=False)
                ...                          # Do some stuff with unknown execution time
                samples.stop()               # Now stop reading the information
        """
        self._nvmecmd.stop()
        self.wait()

    def verify(self, test: NvmeTest = None) -> int:
        """Verify requirements for samples.

        Verifies all Admin Commands completed without error and within the latency limits defined in the user
        settings.  Each sample read is checked to make sure no static parameters changed (e.g. Model) and no
        counters (e.g. Data Written) decremented or reset.

        Args:
            test: Instance of NvmeTest to update with the verify results

        Returns:
            Number of failed requirements.  If all requirements passed then returns 0.

        This example reads NVMe 0 information 10 times and then verifies the samples.

            .. code-block::

                samples = InfoSamples(nvme=0, samples=10, interval=1000)

                if samples.verify() != 0:
                    ...                         # handle failed requirements here

        """
        failed_verifications = 0
        failed_verifications += verify_requirement(
            RqmtId.ADMIN_COMMAND_RELIABILITY,
            name="Admin Commands shall reliably complete without error",
            limit=0,
            value=self._data["read_fails"],
            passed=(self._data["read_fails"] == 0),
            test=test,
        )
        failed_verifications += verify_requirement(
            RqmtId.NO_STATIC_PARAMETER_CHANGE,
            name="Static parameters, such as Model Number, shall not change",
            limit=0,
            value=self._static_mismatches,
            passed=(self._static_mismatches == 0),
            test=test,
        )
        failed_verifications += verify_requirement(
            RqmtId.NO_COUNTER_PARAMETER_DECREMENT,
            name="SMART counters, such as Data Written, shall not reset or decrement",
            limit=0,
            value=self._counter_mismatches,
            passed=(self._counter_mismatches == 0),
            test=test,
        )
        failed_verifications += verify_requirement(
            RqmtId.ADMIN_COMMAND_AVG_LATENCY,
            name=f"Admin Command average latency shall be less than {ADMIN_COMMAND_AVG_LIMIT_MS} mS",
            limit=ADMIN_COMMAND_AVG_LIMIT_MS,
            value=f"{self._data['avg_time']:0.2f} mS",
            passed=(self._data["avg_time"] < ADMIN_COMMAND_AVG_LIMIT_MS),
            test=test,
        )
        failed_verifications += verify_requirement(
            RqmtId.ADMIN_COMMAND_MAX_LATENCY,
            name=f"Admin Command maximum latency shall be less than {ADMIN_COMMAND_MAX_LIMIT_MS} mS",
            limit=ADMIN_COMMAND_MAX_LIMIT_MS,
            value=f"{self._data['max_time']:0.2f} mS",
            passed=(self._data["max_time"] < ADMIN_COMMAND_MAX_LIMIT_MS),
            test=test,
        )
        return failed_verifications
