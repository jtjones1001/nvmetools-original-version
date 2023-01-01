# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""This module provides classes to create PDF reports for NVMe tests and information.

The InfoReport class creates a PDF report for the NVMe information collected with the readnvme console
command.  The HealthReport class creates the PDF report for the test results from the checknvme console
command.

This module uses the reportlab package to create the PDF files and matplotlib to create the charts within
the PDF file.  More details here:

    `ReportLab site  <https://docs.reportlab.com/>`_

    `matplotlib site <https://matplotlib.org/>`_
"""

import copy
import datetime
import glob
import json
import os
import pathlib
import platform
import subprocess
import time

import matplotlib.pyplot as plt

from nvmetools import TESTRUN_DIRECTORY
from nvmetools.features import (
    drive_changes,
    drive_diagnostic,
    drive_features,
    drive_health,
    drive_info,
    drive_wear,
)
from nvmetools.info import Info
from nvmetools.nvme_test import AbortedTestError, TEST_RESULTS_FILE, load_user_drive_test_script
from nvmetools.settings import TestId
from nvmetools.support.conversions import as_int
from nvmetools.support.custom_reportlab import (
    FAIL_COLOR,
    FAIL_TEXT_STYLE,
    Heading,
    LIMIT_COLOR,
    PASS_COLOR,
    SUBHEADING2_STYLE,
    SUBHEADING_STYLE,
    TABLE_ROW_GRAY_COLOR,
    TABLE_STYLE,
    TABLE_STYLE_NO_HEADER,
    TABLE_TEXT_STYLE,
    TEXT_STYLE,
    TestResult,
    TestSuiteResult,
    TestTime,
    TitlePage,
    USABLE_WIDTH,
    convert_plot_to_image,
    save_reportlab_report,
)
from nvmetools.support.log import log

from reportlab.platypus import PageBreak, Paragraph, Table


class InfoReport:
    """Class to create PDF report file for NVMe information.

    This class uses the reportlab package to create a PDF file summarizing the information read from an
    NVMe device with the Info class.

    Example:
        Create a report object using an instance of the Info class and then save the report to a PDF file
        Note the Info class is defined in another module (info.py)::

            info = Info(nvme=0)   # refer to info.py module for details on this command

            report = InfoReport(info)
            report.save(filepath="./nvme_info.pdf")

    Attributes:
        filepath: Path to the PDF report file created.
    """

    __DEFAULT_REPORT_NAME = "readnvme.pdf"

    def __init__(self, info: Info) -> None:
        """Initialize the report but don't create the file.

        Args:
           info : The NVMe information to summarize in the PDF file.
        """
        self.filepath: str = os.path.join(".", InfoReport.__DEFAULT_REPORT_NAME)
        self._elements: list = []
        self._nvme_info: dict = info.info
        self.add_info()

    def _get_value(self, parameter: str) -> str:
        """Get NVMe parameter from the ["nvme"]["parameters"] section."""
        if parameter in self._nvme_info["nvme"]["parameters"]:
            return self._nvme_info["nvme"]["parameters"][parameter]["value"]
        else:
            return " "

    def add_aborted_test(self) -> None:
        """Add standard error message when a test did not complete."""
        self.add_paragraph(
            """The test data indicates the test aborted and did not complete.   Review the test data for
            errors that aborted the test exection.
            """
        )

    def add_exception_report(self, error: Exception) -> None:
        """Add standard text when an exception occurs when adding a test result to the report.

        If an exception occurs when adding a test result to the report this function adds a standard message
        with the exception details.  The function doesn't reraise the exception so the report can still be
        finished.

        Args:
           error (Exception):  The exception that occurred.
        """
        log.exception(error)
        self.add_paragraph(
            f"""A fatal error occurred creating the report for this test.  This most likely is
            caused by corrupted or incomplete test data.  Review the test data for errors
            that aborted the test exection.
            <br/<br/>
            The error details are: {error}"""
        )

    def add_heading(self, text: str) -> None:
        """Add text in heading format with an underline.

        Args:
           text:  The text to add as a heading.
        """
        self._elements.append(Heading(text))

    def add_info(self) -> None:
        """Add NVMe information summary table."""
        self.add_heading("NVME INFORMATION")
        table_data = [
            ["VENDOR", "MODEL", "SIZE", "VERSION"],
            [
                self._get_value("Subsystem Vendor"),
                self._get_value("Model Number (MN)"),
                self._get_value("Size"),
                self._get_value("Version (VER)"),
            ],
        ]
        self.add_table(table_data, [100, 200, 100, 100])

        if self._get_value("Enable Host Memory (EHM)") == "Enabled":
            hmb_value = f"Enabled. Size = {self._get_value('Host Memory Buffer Size (HSIZE)')} pages"
        else:
            hmb_value = "Disabled"

        apst_value = (
            f"{self._get_value('Autonomous Power State Transition')} and "
            + f"{self._get_value('Autonomous Power State Transition Enable (APSTE)')}"
        )
        table_data = [
            ["PARAMETER", "VALUE"],
            ["Serial Number", self._get_value("Serial Number (SN)")],
            ["Number Of Namespaces", self._get_value("Number of Namespaces (NN)")],
            ["Namespace 1 EUI64", self._get_value("Namespace 1 IEEE Extended Unique Identifier (EUI64)")],
            ["Namespace 1 NGUID", self._get_value("Namespace 1 Globally Unique Identifier (NGUID)")],
            ["Namespace 1 Size", self._get_value("Namespace 1 Size")],
            ["Namespace 1 LBA Size", self._get_value("Namespace 1 Active LBA Size")],
            ["Firmware", self._get_value("Firmware Revision (FR)")],
            ["Firmware Slots", self._get_value("Firmware Slots")],
            ["Firmware Activation Without Reset", self._get_value("Firmware Activation Without Reset")],
            ["Host Memory Buffer", hmb_value],
            ["Autonomous Power State Transition", apst_value],
            ["Volatile Write Cache", self._get_value("Volatile Write Cache Enable (WCE)")],
            ["Host Throttle Threshold TMT1", self._get_value("Thermal Management Temperature 1 (TMT1)")],
            ["Host Throttle Threshold TMT2", self._get_value("Thermal Management Temperature 2 (TMT2)")],
            [
                "Drive Throttle Threshold WCTEMP",
                self._get_value("Warning Composite Temperature Threshold (WCTEMP)"),
            ],
            [
                "Drive Throttle Threshold CCTEMP",
                self._get_value("Critical Composite Temperature Threshold (CCTEMP)"),
            ],
        ]
        self.add_table(table_data, [250, 250])

        self.add_subheading("Power States")

        table_data = [["STATE", "NOP", "MAX POWER", "ENTRY LATENCY", "EXIT LATENCY"]]
        for index in range(int(self._get_value("Number of Power States Support (NPSS)"))):
            table_data.append(
                [
                    f"{index}",
                    self._get_value(f"Power State {index} Non-Operational State (NOPS)"),
                    self._get_value(f"Power State {index} Maximum Power (MP)"),
                    self._get_value(f"Power State {index} Entry Latency (ENLAT)"),
                    self._get_value(f"Power State {index} Exit Latency (EXLAT)"),
                ]
            )
        self.add_table(table_data, [60, 60, 100, 140, 140])

        self.add_subheading("PCIe")

        table_data = [
            ["PCI", "VENDOR", "VID", "DID", "WIDTH", "SPEED", "ADDRESS"],
            [
                "Endpoint",
                self._get_value("Subsystem Vendor"),
                self._get_value("PCI Vendor ID (VID)"),
                self._get_value("PCI Device ID"),
                self._get_value("PCI Width"),
                self._get_value("PCI Speed"),
                self._get_value("PCI Location"),
            ],
            [
                "Root",
                "",
                self._get_value("Root PCI Vendor ID"),
                self._get_value("Root PCI Device ID"),
                "",
                "",
                self._get_value("Root PCI Location"),
            ],
        ]
        self.add_table(table_data, [50, 90, 50, 50, 45, 75, 140])
        self.add_pagebreak()
        self.add_smart_attributes()

    def add_pagebreak(self) -> None:
        """Add a pagebreak."""
        self._elements.append(PageBreak())

    def add_paragraph(self, text: str) -> None:
        """Add paragraph of text in standard style.

        Args:
           text:  The text to add in paragraph style.
        """
        self._elements.append(Paragraph(text, style=TEXT_STYLE))

    def add_parameter_table(self) -> None:
        """Add table with parameter information.

        Adds a table that includes the name, description, and value of each NVMe parameter.
        """
        param_table = [["NAME", "DESCRIPTION", "VALUE"]]

        for param in self._nvme_info["nvme"]["parameters"]:
            param_table.append(
                [
                    Paragraph(param),
                    Paragraph(self._nvme_info["nvme"]["parameters"][param]["description"]),
                    Paragraph(self._nvme_info["nvme"]["parameters"][param]["value"]),
                ]
            )
        self.add_table(param_table, [100, 300, 100])

    def add_smart_attributes(self) -> None:
        """Add SMART attributes.

        Adds a table that includes the SMART attributes.  If start and end information exists then the
        table includes the attribute name, start value, end value, and delta values.  Otherwise the
        table includes the attribute name and value.
        """
        self.add_subheading("SMART ATTRIBUTES")

        # if have start and end info then include both and their delta values

        if hasattr(self, "compare_info"):
            table_data = [["PARAMETER", "START", "END", "DELTA"]]
            for counter in self.compare_info["data"]["counters"]:
                if counter["delta"] == 0:
                    tmp = ""
                elif counter["name"] == "Data Read" or counter["name"] == "Data Written":
                    tmp = f"{counter['delta']:,.3f}"
                else:
                    tmp = f"{counter['delta']:,}"
                table_data.append([counter["name"], counter["start"], counter["end"], tmp])
            self.add_table(table_data, [220, 100, 100, 80])
        else:
            table_data = [["PARAMETER", "VALUE"]]
            for parameter in self._nvme_info["nvme"]["parameters"]:
                if self._nvme_info["nvme"]["parameters"][parameter]["compare type"] == "counter":
                    table_data.append([parameter, self._get_value(parameter)])
            self.add_table(table_data, [300, 100])

    def add_subheading(self, text: str) -> None:
        """Add text in subheading format.

        Args:
           text:  The text to add as a subheading.
        """
        self._elements.append(Paragraph(text, style=SUBHEADING_STYLE))

    def add_subheading2(self, text: str) -> None:
        """Add text in subheading2 format.

        Args:
           text:  The text to add as a subheading2.
        """
        self._elements.append(Paragraph(text, style=SUBHEADING2_STYLE))

    def add_table(
        self,
        rows: list[list[str]],
        widths: list[int],
        align: str = "LEFT",
        start_row: int = 0,
        bg_color: str = None,
        fail_fmt: bool = False,
    ) -> None:
        """Add generic table.

        Args:
           rows:  First element is row 0, first element in row 0 is column 0 data.
           widths:  First element is column 0 width, next is column 1 width, etc.
           align:  String to align columns to left, center, or right
           start_row: If 0 then table has a header.
           bg_color: Background color for a row.
           fail_fmt:  Use fail formatting if True.
        """
        if len(rows) == 0:
            return

        # Create the table style based on header or not, fail formatting, and background color.

        if start_row == 0:
            table_style = copy.deepcopy(TABLE_STYLE)
            first_data_row = 1
        else:
            table_style = copy.deepcopy(TABLE_STYLE_NO_HEADER)
            first_data_row = 0

        for row_number, table_row in enumerate(rows):

            if row_number >= first_data_row and (row_number + start_row) % 2 == 0 and bg_color is None:
                table_style.add(
                    "BACKGROUND",
                    (0, row_number),
                    (-1, row_number),
                    TABLE_ROW_GRAY_COLOR,
                )
            elif bg_color == "GRAY":
                table_style.add(
                    "BACKGROUND",
                    (0, row_number),
                    (-1, row_number),
                    TABLE_ROW_GRAY_COLOR,
                )

            if row_number >= first_data_row and fail_fmt:
                if table_row[-1] == "PASS":
                    table_style.add("TEXTCOLOR", (-1, row_number), (-1, row_number), PASS_COLOR)
                elif table_row[-1] == "FAIL":
                    table_style.add("TEXTCOLOR", (-1, row_number), (-1, row_number), FAIL_COLOR)

                table_style.add("FONT", (-1, row_number), (-1, row_number), "Helvetica-Bold")

        table = Table(
            rows,
            colWidths=widths,
            style=table_style,
            hAlign=align,
            spaceBefore=12,
            spaceAfter=12,
        )
        self._elements.append(table)

    def save(self, filepath: str = None) -> None:
        """Save the report as a PDF file.

        Saves the report as a PDF file.

        Args:
           filepath: Optional path to the file to create.
        """
        if filepath is not None:
            self.filepath = filepath

        log.debug(f"Saving report: {filepath}")

        save_reportlab_report(self.filepath, self._elements, add_header_footer=False)

    def show(self) -> None:
        """Show the PDF report in a new window.

        If the PDF report file exists then will show (display) it in a new window.  If the report file does
        not exist, the function returns.
        """
        if os.path.exists(self.filepath):
            if "Windows" == platform.system():
                subprocess.Popen([self.filepath], shell=True)
            else:
                subprocess.call(["open", self.filepath])  # noqa : S607


class HealthReport(InfoReport):
    """Class to create PDF report file for NVMe health check results."""

    _DEFAULT_REPORT_NAME = "nvme_health_check.pdf"
    _DEFAULT_TITLE = "NVMe Health Check"
    _DEFAULT_DESCRIPTION = "Verifies drive health and wear with diagnostic and SMART"

    def __init__(self, results_directory: str = "", title: str = "", description: str = "") -> None:
        """Class to create PDF report file for NVMe health check results.

        Args:
           results_directory: Optional directory with results, if not provided uses latest results.
           title: Optional title for the report.
           description: Optional description for the report.

        This class uses the reportlab package to create a PDF file summarizing the test results from the
        NVMe health check.  The directory with the completed health check results must be provided.

        **Example**

        Create a report object using the results in the directory ./results/check_nvme and then save the report
        object to a PDF file.::

            report = HealthReport(results_directory = "./results/check_nvme")
            report.save(filepath = "./results/check_nvme/health_summary.pdf")

        Attributes:
            filepath: Path to the PDF report file created.
        """
        try:
            # If no path given use the latest test run from the default directory

            if results_directory == "":
                list_of_files = glob.glob(f"{TESTRUN_DIRECTORY}/*")
                results_directory = max(list_of_files, key=os.path.getctime)
                if not os.path.isdir(results_directory):
                    raise Exception(f"No Test Run results found at default path:{TESTRUN_DIRECTORY}")
            elif not os.path.isdir(results_directory):
                raise Exception(f"Results directory provided does not exist: {results_directory}")

            self.filepath = os.path.join(results_directory, self._DEFAULT_REPORT_NAME)

            # Setup vars

            if title == "":
                title = HealthReport._DEFAULT_TITLE
            if description == "":
                self.description = HealthReport._DEFAULT_DESCRIPTION
            else:
                self.description = description

            log.info(f" Creating report at: {self.filepath}", indent=False)

            self.drive_name = "N/A"

            self._results_directory = results_directory
            self._elements = []
            self._testsuite_requirements = 0
            self._testsuite_pass = 0
            self._testsuite_fail = 0
            self._nvme_info = None

            # Read in the data from each test to get info needed for title and
            # summary pages then call custom flowable for title page and then build
            # summary page

            self._read_test_results()
            self._elements.append(TitlePage(self.drive_name, title, self.description, time.strftime("%B %d, %Y")))
            self._add_summary()

            # Display results for each test based on time they completed, first one
            # completed is displayed first and so on.  New tests must be added to
            # this for loop along with their matching function

            for time_key in self._start_times:
                test_data = self._all_results[time_key]  # for readability
                self._add_test_heading(test_data)
                self._add_requirement_table(test_data)
                self._get_test_report(test_data)

            # Add the appendices to the end of the report

            self._add_requirement_results_appendix()
            self._add_references_appendix()
            self._add_parameters_appendix()

        except Exception:
            log.exception("Failed to create test report")

    def _add_debug_summary(self) -> None:
        pass

    def _add_performance_info(self) -> None:
        pass

    def _add_parameters_appendix(self) -> None:
        self.add_pagebreak()
        self.add_heading("Appendix C: Parameter Values")
        self.add_parameter_table()

    def _add_references_appendix(self) -> None:
        self.add_pagebreak()
        self.add_heading("Appendix B: References")
        self.add_paragraph(
            """
                1.  nvmetools, python package distributed on PYPI that generated this report.
            """
        )

    def _add_requirement_results_appendix(self) -> None:
        self.add_pagebreak()
        self.add_heading("Appendix A: Requirement Results")
        self.add_paragraph(
            """
            A requirement can be verified multiple times within a test run or even within a test.  The table
            below lists the results for each attempt to verify a requirement.
            """
        )
        req_table = [["ID", "NAME", "PASS", "FAIL"]]
        for req in sorted(self._requirements):
            pstyle = TEXT_STYLE if self._requirements[req]["FAIL"] == 0 else FAIL_TEXT_STYLE
            req_table.append(
                [
                    Paragraph(str(self._requirements[req]["ID"]), pstyle),
                    Paragraph(self._requirements[req]["NAME"], pstyle),
                    Paragraph(str(self._requirements[req]["PASS"]), pstyle),
                    Paragraph(str(self._requirements[req]["FAIL"]), pstyle),
                ]
            )
        self.add_table(req_table, [40, 350, 50, 50])

    def _add_requirement_table(self, test_data: dict) -> None:
        if test_data["result"] == "skipped" or test_data["result"] == "aborted":
            return

        table_data = [["ID", "REQUIREMENT", "RESULT"]]
        for requirement in sorted(test_data["requirements"]["condensed"]):
            name = test_data["requirements"]["condensed"][requirement]["name"]
            if test_data["requirements"]["condensed"][requirement]["fail"] == 0:
                result = "PASS"
            else:
                result = "FAIL"
            table_data.append([requirement, Paragraph(f"{name}", style=TABLE_TEXT_STYLE), result])
        self.add_table(table_data, [40, USABLE_WIDTH - 100, 60], fail_fmt=True)

    def _add_summary(self) -> None:
        self.add_pagebreak()
        self.add_heading("SUMMARY")
        self.add_paragraph(f"""{self.overview}""")

        if self.specification is None:
            self.add_paragraph("The user did NOT provide information from the drive specification.")
        else:
            if self.specification["client"] is True:
                drive_type = "client"
            else:
                drive_type = "enterprise"
            self.add_paragraph(
                f"""The user provided information that this NVMe drive is a {drive_type} drive
                with {self.specification['warranty']} year warranty and
                {self.specification['tbw']}TB TBW."""
            )
        self.add_paragraph(
            f"""A total of {len(self._all_results)} tests were run that attempted to verify
            {self._testsuite_pass + self._testsuite_fail} unique requirements."""
        )
        self._elements.append(
            TestSuiteResult(
                self._testsuite_pass,
                self._testsuite_fail,
                self._testsuite_start,
                self._testsuite_end,
                self._testsuite_duration,
            )
        )
        self._add_debug_summary()

        table_data = [["TEST", "RESULT"]]
        table_row_start = 0

        for index, time_key in enumerate(self._start_times):

            test_data = self._all_results[time_key]  # for readability

            if test_data["return code"] == 0:
                table_data.append([test_data["name"], "PASS"])
            else:
                table_data.append([test_data["name"], "FAIL"])

                if len(test_data["requirements"]) > 0:
                    self.add_table(table_data, [450, 50], start_row=table_row_start, fail_fmt=True)
                    table_row_start = index
                    if index % 2 == 0:
                        bg = "WHITE"
                    else:
                        bg = "GRAY"
                    # if len(test_data["requirements"]) > 0:
                    table_data = []

                    for req in test_data["requirements"]["condensed"]:
                        if test_data["requirements"]["condensed"][req]["fail"] != 0:
                            table_data.append(
                                [
                                    Paragraph(
                                        f"RQMT {test_data['requirements']['condensed'][req]['id']}: "
                                        + f"{test_data['requirements']['condensed'][req]['name']}"
                                    ),
                                    "FAIL",
                                ]
                            )

                    self.add_table(table_data, [350, 50], align="CENTER", start_row=1, bg_color=bg, fail_fmt=True)

                    table_data = []

        if len(table_data) != 0:
            self.add_table(table_data, [450, 50], start_row=table_row_start, fail_fmt=True)

        self.add_pagebreak()
        self.add_info()
        self.add_paragraph("<br/><br/>")
        self.add_heading("System Information")
        self._add_system_info()
        self.add_paragraph("<br/><br/>")
        self._add_performance_info()

    def _add_system_info(self) -> None:
        if "system" in self._nvme_info["_metadata"]:
            system = self._nvme_info["_metadata"]["system"]
            table_data = [
                ["PARAMETER", "VALUE"],
                ["Supplier", system["manufacturer"]],
                ["Model", system["model"]],
                ["BIOS", system["bios version"]],
                ["Hostname", system["hostname"]],
                ["OS", system["os"]],
            ]
            self.add_table(table_data, [200, 200])

    def _add_test_heading(self, test_data: dict) -> None:
        """Add text in test heading format."""
        self.add_pagebreak()
        self.add_heading(test_data["name"])
        self._elements.append(TestResult(test_data))
        self._elements.append(TestTime(test_data))

    def _get_test_report(self, test_data: dict) -> None:

        report_functions = {
            "Drive Info": drive_info.report,
            "Drive Wear": drive_wear.report,
            "Drive Health": drive_health.report,
            "Drive Features": drive_features.report,
            "Drive Diagnostic": drive_diagnostic.report,
            "Drive Parameter Change": drive_changes.report,
        }

        if test_data["title"] in report_functions:
            report_functions[test_data["title"]](self, test_data)

    def _read_test_results(self) -> None:
        """Read individual test results."""
        end_info_filepath = pathlib.Path(
            os.path.join(
                self._results_directory,
                f"{TestId.DRIVE_CHANGE}_drive_parameter_change",
                TEST_RESULTS_FILE,
            )
        )
        if end_info_filepath.exists():
            with open(end_info_filepath, "r") as file_object:
                self.compare_info = json.load(file_object)

        if self._nvme_info is None:
            info_filepath = pathlib.Path(
                os.path.join(self._results_directory, f"{TestId.DRIVE_INFO}_drive_info", "nvme.info.json")
            )
            if info_filepath.exists():
                self._nvme_info = Info(nvme=None, from_file=info_filepath).info

        if self._nvme_info is None:
            raise Exception("Could not find baseline device data")

        log.debug("reading test results for test report")
        testrun_name = pathlib.Path(self._results_directory).name
        list_of_results = glob.glob(f"{self._results_directory}/*/{TEST_RESULTS_FILE}")

        log.debug("\n")
        log.debug(f"Testrun Name :    {testrun_name}")
        log.debug(f"Testrun location: {self._results_directory}")
        log.debug(f"Test Results      {len(list_of_results)}")
        log.debug("\n")

        self._start_times = []
        self._all_results = {}
        self._requirements = {}

        # for each test read in the results
        for result_file in list_of_results:
            test_pass = 0
            test_fail = 0
            try:
                with open(result_file, "r") as file_object:
                    json_info = json.load(file_object)

                for requirement in json_info["requirements"]["condensed"]:

                    if requirement not in self._requirements:
                        self._requirements[requirement] = {
                            "ID": json_info["requirements"]["condensed"][requirement]["id"],
                            "PASS": json_info["requirements"]["condensed"][requirement]["pass"],
                            "FAIL": json_info["requirements"]["condensed"][requirement]["fail"],
                            "NAME": json_info["requirements"]["condensed"][requirement]["name"],
                        }
                    else:
                        self._requirements[requirement]["PASS"] += json_info["requirements"]["condensed"][
                            requirement
                        ]["pass"]
                        self._requirements[requirement]["FAIL"] += json_info["requirements"]["condensed"][
                            requirement
                        ]["fail"]

                self._all_results[json_info["start time"]] = json_info
                self._start_times.append(json_info["start time"])

                log.debug(
                    f"Test Name     : {pathlib.Path(result_file).parent.name:30s} "
                    + f" Total: {len(json_info['requirements'])}    Pass: {test_pass}   "
                    + f" Fail: {test_fail}"
                )

            except Exception:
                raise Exception(f"Could not open result file {result_file}")

        self._testsuite_requirements = len(self._requirements)
        for req in self._requirements:
            if self._requirements[req]["FAIL"] != 0:
                self._testsuite_fail += 1
            elif self._requirements[req]["PASS"] != 0:
                self._testsuite_pass += 1

        self._start_times.sort()
        self.testrun_end = self._all_results[self._start_times[-1]]["end time"]

        tmp_start = datetime.datetime.strptime(
            self._all_results[self._start_times[0]]["start time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        tmp_end = datetime.datetime.strptime(
            self._all_results[self._start_times[-1]]["end time"], "%Y-%m-%d %H:%M:%S.%f"
        )
        delta = tmp_end - tmp_start
        self._testsuite_start = datetime.datetime.strftime(tmp_start, "%b %d, %Y - %H:%M:%S.%f")[0:-3]
        self._testsuite_end = datetime.datetime.strftime(tmp_end, "%b %d, %Y - %H:%M:%S.%f")[0:-3]
        self._testsuite_duration = str(delta)[0:-3]

        self.drive_name = f"{self._nvme_info['nvme']['description'].split(':',1)[1].strip()}"
        self.model = self._nvme_info["nvme"]["parameters"]["Model Number (MN)"]["value"].strip().replace(" ", "_")

        drive_script = load_user_drive_test_script(self.model)

        if drive_script is None:
            self.specification = None
        else:
            self.specification = drive_script.DRIVE_SPECIFICATION

        if self.description == "":
            self.description = f"Report for {testrun_name} Test of above NVMe installed \
                in {self._nvme_info['_metadata']['system']['manufacturer']} model \
                {self._nvme_info['_metadata']['system']['model']}."

            self.overview = self.description + "."
        else:
            self.overview = self.description
            self.overview += f"  The NVMe tested was the {self.drive_name} installed in a \
                {self._nvme_info['_metadata']['system']['manufacturer']} system, model \
                {self._nvme_info['_metadata']['system']['model']}."

    def add_diagnostic_progress_plot(self, time: list[float], progress: list[float]) -> None:
        """Add progress plot for diagnostic test.

        Adds plot of self-test progress vs time from the diagnostic test to the report.   Time is in minutes
        and progress in percent.

        Args:
           time: Data series indicating time completed in minutes.
           progress: Data series indicating percent completed from log page 6.
        """
        fig, ax = plt.subplots(figsize=(6, 2))

        ax.set_xlabel("Time (Minutes)")
        ax.set_ylabel("Progress (%)")
        ax.get_yaxis().set_label_coords(-0.075, 0.5)
        ax.plot(time, progress, label="Progress", linewidth=2)
        self._elements.append(convert_plot_to_image(fig, ax))

    def add_diagnostic_temperature_plot(self, time: list[float], temp: list[float]) -> None:
        """Add temperature plot for diagnostic test.

        Adds plot of self-test time vs temperature from the diagnostic test to the report.   Time is in minutes
        and temperature in Celsius.

        Args:
           time: Data series indicating time completed in minutes.  Series is a list of floats in the same\
           order as temp.
           temp: Data series indicating composite temperature in Celsius as a list of floats.
        """
        fig, ax1 = plt.subplots(figsize=(6, 4))

        self.add_throttle_lines(plt)  # Add horizontal lines indicating thermal throttle limits
        ax1.set_xlabel("Time (Minutes)")
        ax1.set_ylabel("Temperature (C)")
        ax1.get_yaxis().set_label_coords(-0.075, 0.5)
        ax1.plot(time, temp, linewidth=1)
        plt.legend(bbox_to_anchor=(1.05, 0.5), loc="center left")
        self._elements.append(convert_plot_to_image(fig, ax1))

    def add_test_result_intro(self, test_result: dict) -> None:
        """Add test result summary for the test.

        Adds single line to report that indicates if the test failed any requirements.

        Args:
           test_result: Test results from json file.
        """
        self.add_subheading("RESULTS")

        if test_result["result"] == "aborted":
            raise AbortedTestError

        test_failed = False
        for rqmt in test_result["requirements"]["condensed"]:
            if test_result["requirements"]["condensed"][rqmt]["fail"] != 0:
                test_failed = True

        if test_failed:
            self.add_paragraph("One or more requirements failed verification and are listed in the table above.")
        else:
            self.add_paragraph("All requirements passed verification.")

    def add_throttle_lines(self, plt: plt) -> None:
        """Add thermal throttle lines to plot.

        Adds horizontal lines to a plot indicating the thermal throttle limits of CCTEMP, WCTEMP, TMT2,
        and TMT1.

        Args:
           plt: Plot to add the lines too.
        """
        value = self._get_value
        if value("Critical Composite Temperature Threshold (CCTEMP)") != "Not Reported":
            plt.axhline(
                y=as_int(value("Critical Composite Temperature Threshold (CCTEMP)")),
                linewidth=1,
                color=LIMIT_COLOR,
                linestyle="-",
                label="CCTEMP",
            )
        if value("Warning Composite Temperature Threshold (WCTEMP)") != "Not Reported":
            plt.axhline(
                y=as_int(value("Warning Composite Temperature Threshold (WCTEMP)")),
                linewidth=1.5,
                color=LIMIT_COLOR,
                linestyle="--",
                label="WCTEMP",
            )

        if value("Thermal Management Temperature 2 (TMT2)") != "Disabled":
            plt.axhline(
                y=as_int(value("Thermal Management Temperature 2 (TMT2)")),
                linewidth=1.5,
                color=LIMIT_COLOR,
                linestyle=(0, (3, 1, 1, 1, 1, 1)),
                label="TMT2",
            )
        if value("Thermal Management Temperature 1 (TMT1)") != "Disabled":
            plt.axhline(
                y=as_int(value("Thermal Management Temperature 1 (TMT1)")),
                linewidth=1.5,
                color=LIMIT_COLOR,
                linestyle=":",
                label="TMT1",
            )

    def save(self, filepath: str = None) -> None:
        """Save the report as a PDF file.

        Saves the report as a PDF file with a header and footer.

        Args:
           filepath: Optional path to the file to create.
        """
        if filepath is not None:
            self.filepath = filepath

        log.debug(f"Saving report: {filepath}")

        save_reportlab_report(self.filepath, self._elements, drive=self.drive_name, add_header_footer=True)
