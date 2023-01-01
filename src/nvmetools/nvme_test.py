# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""This module provides classes to create tests and test suites.

This module provides classes to create aand run Nvme tests and test suites for the sole purpose of testing
NVMe drives.
"""
import copy
import datetime
import importlib.util
import json
import os
import time
import types

from nvmetools import SPECIFICATION_DIRECTORY
from nvmetools.support.conversions import BYTES_IN_KIB
from nvmetools.support.exit import EXCEPTION_EXIT_CODE
from nvmetools.support.log import log

TEST_RESULTS_FILE = "test_result.json"
TESTRUN_WIDTH = 90


class AbortedTestError(Exception):
    """Custom exception to abort test in standard way."""

    def __init__(self) -> None:
        """Add error code and indicate custom exception then propagate."""
        self.code = 57
        self.nvmetools = True
        super().__init__("Test was aborted and did not complete")


class InvalidUserScriptError(Exception):
    """Custom exception to indicates user script is invalid."""

    def __init__(self) -> None:
        """Add error code and indicate custom exception then propagate."""
        self.code = 58
        self.nvmetools = True
        super().__init__("User script is invalid")


def load_user_drive_test_script(model: str, directory: str = SPECIFICATION_DIRECTORY) -> types.ModuleType:
    """Import custom module created by user for a specific drive model.

    Users can create modules for a specfic drive model.  This can be used to load
    drive specific parameters and methods.  If the file is missing None is returned.
    If the file exists but has an error then an exception is raised.

    Args:
        model: Stripped model name with spaces replaced by underscores.
        directory: Optional directory to find script. Default is SPECIFICATION_DIRECTORY

    Returns:
        module: User module or None if doesn't exist

    Raises:
         InvalidUserScriptError: User script is present but has coding error.
    """
    filepath = os.path.join(directory, f"{model}.py")
    if not os.path.exists(filepath):
        return None

    try:
        spec = importlib.util.spec_from_file_location(model, filepath)
        drive_script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(drive_script)
    except Exception:
        raise InvalidUserScriptError

    return drive_script


class NvmeTest:
    """Class for an NVMe test that verifies one or more requirements."""

    def __init__(self, test_id: int, name: str, description: str, directory: str) -> None:
        """Class to create an instance of an NVMe test.

        Args:
           test_id:  Unique integer test ID.
           name: Unique test name.
           description: Short description for the test.
           directory:  Directory to log test results.

        An NVMe test must have an unique ID and name.

        The class creates a subdirectory under the directory parameter to log the test results. The
        subdirectory name is based on the test_id and name.  For example, having a test_id = 10 and
        name = drive_info creates:

            10_drive_info

        The test can have one or more optional steps created with start_step(). Each step has its own
        subdirectory.  The end_step() method is called to end the step.

        The test.end() is called to end the test.  This method returns a dictionary with the test
        results and creates the final logs.

        Attributes:
            data: Dictionary of data parameters
            directory: Directory for test logs
            step_directory: Subdirectory of test directory for step logs
            skipped: Test was skipped
            aborted: Test was aborted
            errors: Number of errors found in test
            step_errors: Number of errors found in test step
        """
        self._start_counter = time.perf_counter()
        self._step = 0
        self.data = {}

        self.error_count = 0
        self.step_errors = 0
        self.aborted = False
        self.skipped = False

        # create directory to log the results too

        dir_name = f"{test_id}_{name.replace(' ','_').lower()}"
        self.directory = os.path.join(directory, dir_name)
        try:
            os.makedirs(self.directory)
        except FileExistsError:
            pass

        # this dictionary holds all results and is returned at end of test
        # and dumped to a json file

        self._result = {
            "name": f"TEST {test_id}: {name}",
            "title": name,
            "description": description,
            "result": "skipped",
            "return code": 50,
            "start time": f"{datetime.datetime.now()}",
            "end time": "N/A",
            "duration (sec)": "N/A",
            "directory": self.directory,
            "directory name": dir_name,
            "requirements": {},
        }
        self._result["requirements"]["trace"] = []
        self._result["requirements"]["condensed"] = {}

        # log banner indicating test started

        log.header(self._result["name"], 45)
        log.info(f"Description : {self._result['description']}")
        log.info(f"Directory   : {self._result['directory']}")
        log.verbose(f"Start Time  : {self._result['start time']}")
        log.info("")

    def abort_on_exception(self, e: Exception = None) -> dict:
        """Abort test when exception occurs.

        Args:
            e: Optional exception to log

        Returns:
           test results as a dictionary
        """
        self.aborted = True
        log.exception("\n    Unknown error occurred in test, send logs to developer \n\n")
        log.info("")
        return self.end(EXCEPTION_EXIT_CODE)

    def end(self, return_code: int = None) -> dict:
        """End test by logging final details.

        Args:
           return_code: Optional return code. Default is number of errors.

        Returns:
           test results as a dictionary
        """
        if return_code is None:
            self.return_code = self.error_count
        else:
            self.return_code = return_code

        # status : aborted, skipped, passed, failed

        if self.aborted:
            self._result["result"] = "aborted"
        elif self.skipped:
            self._result["result"] = "skipped"
        elif self.return_code == 0:
            self._result["result"] = "passed"
        else:
            self._result["result"] = "failed"

        # w/a for tests faster than timer ticks
        if (time.perf_counter() - self._start_counter) < 0.02:
            time.sleep(0.02)

        self._result["duration (sec)"] = time.perf_counter() - self._start_counter
        self._result["end time"] = f"{datetime.datetime.now()}"

        pass_rqmt = 0
        fail_rqmt = 0
        for rqmt in self._result["requirements"]["condensed"]:
            if (
                self._result["requirements"]["condensed"][rqmt]["fail"] == 0
                and self._result["requirements"]["condensed"][rqmt]["pass"] > 0
            ):
                pass_rqmt += 1
            else:
                fail_rqmt += 1

        self._result["requirements"]["total requirements"] = len(self._result["requirements"]["condensed"])
        self._result["requirements"]["fail requirements"] = fail_rqmt
        self._result["requirements"]["pass requirements"] = pass_rqmt

        log.info("")
        log.verbose(f"End Time    : {self._result['end time']} ")
        log.info(f"Duration    : {self._result['duration (sec)']:.3f} seconds")
        log.info(f"Requirements: {pass_rqmt} passed, {fail_rqmt} failed ")
        log.info("")

        if self.return_code == 0:
            self._result["return code"] = 0
            log.info("TEST PASSED")
        else:
            self._result["return code"] = self.return_code
            log.info("----> TEST FAILED", indent=False)
        log.info("")

        self._result["data"] = self.data

        try:
            json_results_file = os.path.join(self._result["directory"], TEST_RESULTS_FILE)
            with open(json_results_file, "w", encoding="utf-8") as f:
                json.dump(self._result, f, ensure_ascii=False, indent=4)
        except Exception:
            raise Exception(f"Failed to create json test result file {json_results_file}")

        log.debug(f"Test returning {self.return_code}")
        return self._result

    def end_step(self, error_count: int = None) -> None:
        """End test step.

        Optional method that allows updating the test and step errors with an integer
        value for additional errors.  Called at the end of the test step.

        Args:
            error_count: Optional number of errors to add to step_errors attribute
        """
        if error_count is not None:
            self.step_errors = self.step_errors + error_count
            self.error_count = self.error_count + error_count

    def skip(self, return_code: int = None) -> dict:
        """Skip test when cannot be run.

        This method is called when a test is skipped.  Typically this occurs when a feature is not supported
        by the drive.

        Args:
           return_code: Optional return code for test end.

        Returns:
           test results as a dictionary
        """
        self.skipped = True
        return self.end(return_code)

    def start_step(self, name: str, description: str) -> None:
        """Start a test step.

        A test step has its own subdirectory under the test directory for logging.  A step also has its own
        error count and pass/fail status.

        Args:
            name: Step name.
            description: Short description of the step.

        """
        self._step += 1
        self.step_errors = 0
        if not name == "":
            self.step_directory = os.path.join(self.directory, f"{self._step}_{name}".lower())
            os.mkdir(self.step_directory)

        log.verbose("")
        log.verbose(f"Step {self._step}: {description}")
        log.verbose("")


class NvmeTestSuite:
    """Class to run a group of NVMe tests (NvmeTest class)."""

    def __init__(
        self,
        title: str,
        description: str,
        details: str,
        nvme: int,
        directory: str,
        volume: str = "",
    ) -> None:
        """Class to run a suite of individual NVMe tests (NvmeTest class).

        Args:
            title: Test suite title.
            description: Short description of the test suite.
            details:  Long description of the test suite.
            nvme: NVMe number to test, see listnvme.
            directory:  Directory to log results.
            volume: Optional volume to test.

        This example is taken from the checknvme console command.  It runs several tests as part of a simple
        test suite that checks NVMe health.

        The run_test input parameter is the module name that contains the test() function to run.  This test()
        function must test a specific NVMe feature.  Results of each test are logged in a subdirectory under
        the test suite directory.

        .. code-block::

            nvme = 0
            title = "NVMe Health Check"
            description = "Verifies drive health and wear with diagnostic and SMART"
            details = "NVMe Health Check is a short Test Suite that verifies drive health and wear
                       by running the drive diagnostic, reviewing SMART data, and
                       checking the Self-Test history."

            test_suite = NvmeTestSuite(title, description, details, nvme, directory)

            test_suite.run_test(drive_info)
            test_suite.run_test(drive_wear)
            test_suite.run_test(drive_health)
            test_suite.run_test(drive_features)
            test_suite.run_test(drive_diagnostic)
            test_suite.run_test(drive_changes)

            test_suite.end()

        Attributes:
            return_code: Number of failing tests, 0 if no tests failed
        """
        self.return_code = 50
        self._tests = []
        self._result = {}
        self._result["requirements"] = {}

        self.passed_tests = 0
        self.failed_tests = 0
        self.passed_rqmts = 0
        self.failed_rqmts = 0

        self.directory = directory
        self.device = nvme
        self.title = title
        self.description = description
        self.details = details
        self._start_counter = time.perf_counter()

        self.test_args = {
            "nvme": nvme,
            "directory": directory,
            "info_file": os.path.join(self.directory, "10_drive_info", "nvme.info.json"),
            "volume": volume,
        }
        log.info(" " + "-" * TESTRUN_WIDTH, indent=False)
        log.info(f" TEST RUN : {title}", indent=False)
        log.info(" " + "-" * TESTRUN_WIDTH, indent=False)
        log.info(f" Description : {description}", indent=False)
        log.info(f" Start Time  : {datetime.datetime.now()}", indent=False)
        log.info(f" Directory   : {self.directory}", indent=False)
        log.info("")

    def run_test(self, test_module_name: types.ModuleType, stop_on_fail: bool = False) -> None:
        """Run an individual NvmeTest test.

        Args:
            test_module_name: Module name that contains the test() function to run.
            stop_on_fail: If True, aborts the test suite if test fails.
        """
        try:
            test = test_module_name.test(**self.test_args)
        except NameError:
            log.info("Test {test_module_name} was not found.")
            self.failed_tests += 1
            return

        if not isinstance(test, dict):
            raise TypeError("NvmeTestSuite run_test received illegal value")
        self._tests.append(test)

        for rqmt in test["requirements"]["condensed"]:
            if rqmt not in self._result["requirements"]:
                self._result["requirements"][rqmt] = copy.copy(test["requirements"]["condensed"][rqmt])
            else:
                self._result["requirements"][rqmt]["pass"] += test["requirements"]["condensed"][rqmt]["pass"]
                self._result["requirements"][rqmt]["fail"] += test["requirements"]["condensed"][rqmt]["fail"]

        if test["return code"] == 0:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            if stop_on_fail:
                raise StopOnFailError

    def end(self) -> None:
        """End the test suite.

        Calling this method updates the logs with the final results.
        """
        if self.failed_tests == 0:
            self.return_code = 0
        else:
            self.return_code = 1

        for rqmt in self._result["requirements"]:
            if self._result["requirements"][rqmt]["fail"] != 0:
                self.failed_rqmts += 1
            else:
                self.passed_rqmts += 1

        duration = time.perf_counter() - self._start_counter

        log.info(f" End Time     : {datetime.datetime.now()}", indent=False)
        log.info(f" Duration     : {duration:.3f} seconds", indent=False)
        log.info(
            f" Tests        : {len(self._tests)} " + f"({self.passed_tests} passed, {self.failed_tests} failed)",
            indent=False,
        )
        log.info(
            f" Requirements : {len(self._result['requirements'])} ({self.passed_rqmts} passed,"
            + f"{self.failed_rqmts} failed)",
            indent=False,
        )

        log.info(" " + "-" * TESTRUN_WIDTH, indent=False)

        if self.failed_tests == 0 and self.passed_tests > 0:
            log.info(" TEST RUN PASSED", indent=False)
        else:
            log.info(" TEST RUN FAILED", indent=False)

        log.info(" " + "-" * TESTRUN_WIDTH, indent=False)


class StopOnFailError(Exception):
    """Custom exception to handle stop on fail."""

    def __init__(self, msg: str = None) -> None:
        """Display message but do not propagate the exception."""
        if msg is None:
            msg = " Aborted Test Run because test failed"
        self.msg = msg
        self.nvmetools = True


def verify_requirement(
    rqmt_id: int, name: str, limit: str, value: str, passed: bool, test: NvmeTest = None
) -> int:
    """Verify the requirement and add to test result.

    Args:
       rqmt_id:  Unique requirement ID as an integer.
       name: Requirement name.
       limit: Limit for requirement verification.
       value:  Requirement value to verify.
       passed: Requirement passed verification if True.
       test: Optional test instance to update with the result.

    Returns:
        Returns 0 if verify passes, returns 1 if verify failed.
    """
    trace_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    if test is not None:
        test._result["requirements"]["trace"].append(
            {
                "id": rqmt_id,
                "name": name,
                "limit": limit,
                "value": value,
                "passed": bool(passed),
                "time": trace_time,
            }
        )
        if rqmt_id not in test._result["requirements"]["condensed"]:
            test._result["requirements"]["condensed"][rqmt_id] = {
                "id": rqmt_id,
                "pass": 0,
                "fail": 0,
                "name": name,
            }
        if passed:
            test._result["requirements"]["condensed"][rqmt_id]["pass"] += 1
        else:
            test._result["requirements"]["condensed"][rqmt_id]["fail"] += 1
            test.error_count += 1
            test.step_errors += 1

    if passed:
        log.verbose(f"PASS :  Requirement {rqmt_id}. {name}   [value: {value}]")
        return 0
    else:
        log.info(f"----> FAIL :  Requirement {rqmt_id}. {name}   [value: {value}]", indent=False)
        return 1
