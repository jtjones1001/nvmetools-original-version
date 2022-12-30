# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""This module provides classes for a NVMe test framework.

The framework consists of Test Suites, Test Cases, Test Steps, and Requirement Verifications.
"""
import datetime
import glob
import inspect
import json
import logging
import os
import platform
import shutil
import time


from nvmetools import DEFAULT_INFO_DIRECTORY, TEST_SUITE_DIRECTORY, USER_INFO_DIRECTORY, __version__
from nvmetools.apps.nvmecmd import check_nvmecmd_permissions
from nvmetools.support.conversions import as_duration, is_admin
from nvmetools.support.log import start_logger
from nvmetools.support.report import create_reports

SKIPPED = "SKIPPED"
PASSED = "PASSED"
FAILED = "FAILED"
ABORTED = "ABORTED"
STARTED = "STARTED"

RESULTS_FILE = "result.json"


class TestStep:
    stop_on_fail = False
    __force_fail = False

    def __init__(self, test, title, description="", *args, **kwargs):
        """Class to run a Test Step.

        A Test Step is run within a Test Case which is run within a Test Suite.  A
        Test Step can contain any number of Verifications. A Test Step fails if any
        Verification fails.  A Test Step passes if all Verifications pass or there are
        no Verifications.

        If the stop_on_fail attribute is True the Step will stop on the first failed verification.

        Args:
            test: Parent TestCase instance running the step
            title: Title of the step
            description: Description of the step

        This example runs a test step with one verification that determines pass/fail.

            .. code-block::

                with TestStep("My step", "This is a very cool step description") as step:
                    rqmts.my_requirement_to_verify(step, value, limit)

        This example runs a test step and enables stop on fail for the first verification.

            .. code-block::

                with TestStep("My step", "This is a very cool step description") as step:

                    step.stop_on_fail = True
                    rqmts.my_requirement_to_verify(step, value, limit)

                    step.stop_on_fail = False
                    rqmts.my_other_requirement_to_verify(step, value, limit)
                    rqmts.my_last_requirement_to_verify(step, value, limit)

        This example runs a test step and passes or fails based on a custom variable.

            .. code-block::

                with TestStep("My step", "This is a very cool step description") as step:

                    if myvalue == "PASS":
                        step.stop(fail=False)
                    else:
                        step.stop()

        Attributes:
            directory:      Working directory
            suite           Grandparent TestSuite instance running the test
            step_number     Step number within the test
            stop_on_fail    If true the step will stop on a failure
            test            Parent TestCase instance running the step
        """
        for item in kwargs.items():
            self.__setattr__(item[0], item[1])

        self._title = title
        self._description = description
        self._start_counter = time.perf_counter()
        self.test = test
        self.suite = test.suite
        self.step_number = test.step_number = test.step_number + 1
        directory_name = f"{test.step_number}_{title.lower().replace(' ','_')}"
        self.directory = os.path.realpath(os.path.join(self.test.directory, directory_name))
        os.makedirs(self.directory, exist_ok=False)

        self.state = {
            "title": title,
            "description": self._description,
            "result": ABORTED,
            "start time": f"{datetime.datetime.now()}"[:-3],
            "end time": "",
            "duration (sec)": "",
            "duration": "",
            "directory": self.directory,
            "directory name": directory_name,
            "verifications": [],
        }

    def __enter__(self):
        log.frames("TestStep", inspect.getouterframes(inspect.currentframe(), context=1))
        log.verbose(f"Step {self.test.step_number}: {self._title}")
        log.verbose("")
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        duration_seconds = time.perf_counter() - self._start_counter
        self.state["end time"] = f"{datetime.datetime.now()}"[:-3]
        self.state["description"] = self._description
        self.state["duration (sec)"] = f"{duration_seconds:.3f}"
        self.state["duration"] = as_duration(duration_seconds)

        pass_vers = sum(ver["result"] is PASSED for ver in self.state["verifications"])
        fail_vers = sum(ver["result"] is not PASSED for ver in self.state["verifications"])

        if self.suite.loglevel > 1:
            if fail_vers != 0:
                log.important("")
            elif pass_vers != 0:
                log.verbose("")

        # End normally

        if exc_type is None:
            if self.__force_fail or fail_vers > 0:
                self.state["result"] = FAILED
            else:
                self.state["result"] = PASSED
            self.test.state["steps"].append(self.state)

        # Stopped because of framework exception, determine pass/fail and then forward exception

        elif hasattr(exc_value, "nvme_framework_exception"):
            if self.__force_fail or fail_vers > 0:
                self.state["result"] = FAILED
            else:
                self.state["result"] = PASSED
            self.test.state["steps"].append(self.state)

            # if step stop then it was handled, else send to parent test case
            if exc_type is not self.Stop:
                return False

        # Stopped with unknown exception, forward to parent test case

        else:
            self.state["result"] = ABORTED
            self.test.state["steps"].append(self.state)
            return False

        if self.state["result"] == FAILED and self.test.stop_on_fail:
            self.test.stop()

        return True

    def stop(self, force_fail=True):
        """Stop the TestStep."""
        self.__force_fail = force_fail
        raise self.Stop

    class Stop(Exception):
        """Framework exception to stop a Test Step."""

        nvme_framework_exception = True

        def __init__(self):
            log.frames("TestStep.Stop", inspect.getouterframes(inspect.currentframe(), context=1))
            log.info("----> STEP STOP", indent=False)
            log.info("")
            super().__init__("TestStep.Stop")


class TestCase:
    stop_on_fail = False
    __force_fail = False

    def __init__(self, suite, title, description="", *args, **kwargs):
        """Class to run a Test Case.

        A Test Case is run within a Test Suite and must contain one or more Test Steps.

        If the stop_on_fail attribute is True the TestCase will stop on the first Test Step.

        Args:
            suite: TestSuite instance that runs the step
            title: Title of the step
            description: Description of the step

        This example creates a test step

            .. code-block::

                with TestSuite("My suite", "This is the test suite") as suite:

                    tests.my_test(suite)
                    tests.my_other_test(suite)

        Attributes:
            directory:      Working directory
            suite           Parent TestSuite instance running the test
            test_number     Test number within the suite
            stop_on_fail    If true the test will stop on a failure
        """
        for item in kwargs.items():
            self.__setattr__(item[0], item[1])

        self.data = {}
        self.suite = suite
        self._steps = []
        self._start_counter = time.perf_counter()
        self._description = description.split("\n")[0]
        self.details = description
        self.step_number = 0
        suite.test_number += 1
        directory_name = f"{suite.test_number}_{title.lower().replace(' ','_')}"
        self.directory = os.path.realpath(os.path.join(self.suite.directory, directory_name))
        os.makedirs(self.directory, exist_ok=False)

        self.state = {
            "number": suite.test_number,
            "title": title,
            "description": self._description,
            "details": self.details,
            "result": ABORTED,
            "start time": f"{datetime.datetime.now()}"[:-3],
            "end time": "",
            "duration (sec)": "",
            "duration": "",
            "directory": self.directory,
            "directory name": directory_name,
            "summary": {
                "steps": {"total": 0, "pass": 0, "fail": 0},
                "rqmts": {"total": 0, "pass": 0, "fail": 0},
                "verifications": {"total": 0, "pass": 0, "fail": 0},
            },
            "steps": [],
            "verifications": [],
            "rqmts": {},
        }

    def __enter__(self):
        log.frames("TestCase", inspect.getouterframes(inspect.currentframe(), context=1))
        log.header(f"TEST {self.suite.test_number} : {self.state['title']}", 45)
        log.info(f"Description : {self.state['description']}")
        log.verbose(f"Start Time  : {self.state['start time']}")
        log.info("")
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        duration_seconds = time.perf_counter() - self._start_counter
        self.state["end time"] = f"{datetime.datetime.now()}"[:-3]
        self.state["description"] = self._description
        self.state["duration (sec)"] = f"{duration_seconds:.3f}"
        self.state["duration"] = as_duration(duration_seconds)
        self.state["data"] = self.data

        fail_steps = sum(step["result"] is not PASSED for step in self.state["steps"])

        if exc_type is None or hasattr(exc_value, "nvme_framework_exception"):
            if exc_type is self.Skip:
                self.state["result"] = SKIPPED
            elif self.__force_fail or fail_steps > 0:
                self.state["result"] = FAILED
            else:
                self.state["result"] = PASSED
        else:
            self.state["result"] = ABORTED

        self.update_summary()

        self.suite.state["tests"].append(self.state)

        results_file = os.path.join(self.directory, RESULTS_FILE)
        with open(results_file, "w", encoding="utf-8") as file_object:
            json.dump(self.state, file_object, ensure_ascii=False, indent=4)

        if self.suite.loglevel == 1:
            log.info("")
        log.verbose(f"End Time    : {self.state['end time']} ")
        log.info(f"Duration    : {self.state['duration (sec)']} seconds")
        log.info(
            f"Verifications: {self.state['summary']['verifications']['pass']} passed, "
            + f"{self.state['summary']['verifications']['fail']} failed "
        )
        log.info("")
        if self.state["result"] == PASSED:
            if self.suite.loglevel == 0:
                log.important(f"    PASS : TEST {self.suite.test_number} : {self.state['title']}", indent=False)
            else:
                log.info("TEST PASSED")
                log.info("")
        elif self.state["result"] == SKIPPED:
            if self.suite.loglevel == 0:
                log.important(f" --> SKIP : TEST {self.suite.test_number} : {self.state['title']}", indent=False)
            else:
                log.info("----> TEST SKIPPED", indent=False)
                log.info("")
        elif self.state["result"] == ABORTED:
            if exc_type is KeyboardInterrupt:
                log.error(" ----> TEST ABORTED BY CTRL-C\n\n")
                self.suite.stop()
            else:
                log.exception(" ----> TEST ABORTED WITH BELOW EXCEPTION\n\n")
                log.error(" ")
        else:
            if self.suite.loglevel == 0:
                log.important(f"--> FAIL : TEST {self.suite.test_number} : {self.state['title']}", indent=False)
            else:
                log.info("----> TEST FAILED", indent=False)
                log.info("")

        if exc_type is self.suite.Stop:
            return False

        if self.state["result"] == FAILED and self.suite.stop_on_fail:
            self.suite.stop()

        return True

    def skip(self, force_fail=False):
        """Skip the TestCase."""
        self.__force_fail = force_fail
        raise self.Skip

    def stop(self, force_fail=True):
        """Stop the TestCase."""
        self.__force_fail = force_fail
        raise self.Stop

    def update_summary(self):
        self.state = update_test_summary(self.state)

    class Skip(Exception):
        """Framework exception to skip a Test Case."""

        nvme_framework_exception = True

        def __init__(self, msg=""):
            log.frames("TestCase.Skip", inspect.getouterframes(inspect.currentframe(), context=1))
            log.info(f"----> TEST SKIP : {msg}", indent=False)
            log.info("")
            super().__init__("TestCase.Skip")

    class Stop(Exception):
        """Framework exception to stop a Test Case."""

        nvme_framework_exception = True

        def __init__(self, msg=""):
            log.frames("TestCase.Stop", inspect.getouterframes(inspect.currentframe(), context=1))
            log.info(f"----> TEST STOP : {msg}", indent=False)
            log.info("")
            super().__init__("TestCase.Stop")


class TestSuite:
    stop_on_fail = False
    loglevel = 1
    __force_fail = False

    def __init__(self, title, description="", *args, **kwargs):
        """Class to complete a Test Suite.

        The TestSuite is the top level of the NVMe test framework consisting of:

            TestSuite
                TestCase
                    TestStep
                        Verification

        A TestSuite must contain one or more TestCases.

        Logging

        Dashboard
        PDF Report

        Args:
            title: Title of the step
            description: Description of the step

        This example runs a test suite with one test case.

            .. code-block::

                with TestSuite("My suite", "This is the description") as suite:
                    tests.my_testcase(suite)

        This example runs a test suite with stop on fail for the first test case.

            .. code-block::

                with TestSuite("My suite", "This is the description") as suite:
                    suite.stop_on_fail = True
                    tests.my_testcase(suite)

                    suite.stop_on_fail = False
                    tests.my_lasttest(suite)

        """
        for item in kwargs.items():
            self.__setattr__(item[0], item[1])

        self._description = description.split("\n")[0]
        self.details = description
        self._title = title
        self.tests = []
        self._start_counter = time.perf_counter()
        self.test_number = 0
        self.data = {}

        self.uid = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.directory = os.path.realpath(
            os.path.join(TEST_SUITE_DIRECTORY, title.lower().replace(" ", "_"), self.uid)
        )
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)
        os.makedirs(self.directory, exist_ok=False)

        self.state = {
            "title": title,
            "description": self._description,
            "details": self.details,
            "result": ABORTED,
            "complete": False,
            "start time": f"{datetime.datetime.now()}"[:-3],
            "end time": "",
            "duration (sec)": "",
            "duration": "",
            "directory": self.directory,
            "script version": __version__,
            "id": self.uid,
            "model": "N/A",
            "system": f"{platform.node()}",
            "location": "N/A",
            "summary": {
                "tests": {"total": 0, "pass": 0, "fail": 0, "skip": 0},
                "rqmts": {"total": 0, "pass": 0, "fail": 0},
                "verifications": {"total": 0, "pass": 0, "fail": 0},
            },
            "tests": [],
            "verifications": [],
            "rqmts": {},
            "data": {},
        }
        global log

        if self.loglevel == 0:
            log = start_logger(self.directory, logging.IMPORTANT, "console.log")
        elif self.loglevel == 1:
            log = start_logger(self.directory, logging.INFO, "console.log")
        elif self.loglevel == 2:
            log = start_logger(self.directory, logging.VERBOSE, "console.log")
        else:
            log = start_logger(self.directory, logging.DEBUG, "console.log")

        check_nvmecmd_permissions()
        self.get_drive_specification()

    def __enter__(self):
        log.frames("TestSuite", inspect.getouterframes(inspect.currentframe(), context=1), indent=False)
        log.important(" " + "-" * 90, indent=False)
        log.important(f" TEST SUITE : {self.state['title']}", indent=False)
        log.important(" " + "-" * 90, indent=False)
        log.info(f" Description : {self.state['description']}", indent=False)
        log.important(f" Start Time  : {datetime.datetime.now()}", indent=False)
        log.important(f" Directory   : {self.directory}", indent=False)
        log.important("")

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        duration_seconds = time.perf_counter() - self._start_counter
        self.state["end time"] = f"{datetime.datetime.now()}"[:-3]

        if "start_info" in self.data:
            self.state["model"] = self.data["start_info"]["parameters"]["Model"]
            self.state["location"] = f"NVMe {self.nvme}"

        self.state["data"] = self.data
        self.state["duration (sec)"] = f"{duration_seconds:.3f}"
        self.state["duration"] = as_duration(duration_seconds)

        fail_tests = sum(test["result"] is not PASSED for test in self.state["tests"])
        aborted_tests = sum(test["result"] is ABORTED for test in self.state["tests"])

        if exc_type is None or exc_type is self.Stop:
            if aborted_tests == 0:
                self.state["complete"] = True

            if self.__force_fail or fail_tests > 0:
                self.state["result"] = FAILED
            else:
                self.state["result"] = PASSED

        else:
            log.exception(" ----> TEST SUITE ABORTED WITH BELOW EXCEPTION\n\n")
            log.error(" ")
            self.state["result"] = ABORTED

        self.update_summary()

        if self.loglevel == 0:
            log.important("")

        log.important(f" End Time     : {self.state['end time'] }", indent=False)
        log.important(f" Duration     : {self.state['duration (sec)']} seconds", indent=False)
        log.info(
            f" Tests        : {self.state['summary']['tests']['total']} "
            + f"({self.state['summary']['tests']['pass']} passed, "
            + f"{self.state['summary']['tests']['fail']} failed)",
            indent=False,
        )
        log.info(
            f" Verifications : {self.state['summary']['verifications']['total']} "
            + f"({self.state['summary']['verifications']['pass']} passed, "
            + f"{self.state['summary']['verifications']['fail']} failed)",
            indent=False,
        )
        log.important(" " + "-" * 90, indent=False)

        if self.state["result"] == PASSED:
            log.important(" TEST SUITE PASSED", indent=False)
        else:
            log.important(" TEST SUITE FAILED", indent=False)

        log.important(" " + "-" * 90, indent=False)

        results_file = os.path.join(self.directory, RESULTS_FILE)
        with open(results_file, "w", encoding="utf-8") as file_object:
            json.dump(self.state, file_object, ensure_ascii=False, indent=4)

        create_reports(
            results_directory=self.directory,
            title=self._title,
            description=self._description,
        )
        return True

    def get_drive_specification(self):
        """Get the drive specification file."""

        if "start_info" in self.state["data"]:
            filename = f"{self.state['data']['start_info']['parameters']['Model No Spaces']}.json"
        else:
            filename = "default.json"

        filepath = os.path.join(USER_INFO_DIRECTORY, filename)

        if not os.path.exists(filepath):
            filepath = os.path.join(DEFAULT_INFO_DIRECTORY, filename)

        if not os.path.exists(filepath):
            filepath = os.path.join(DEFAULT_INFO_DIRECTORY, "default.json")

        with open(filepath, "r") as file_object:
            self.device = json.load(file_object)

    def stop(self, fail=True):
        """Stop the TestSuite."""
        self.__force_fail = fail
        raise self.Stop

    def update_summary(self):
        self.state = update_suite_summary(self.state)

    class Stop(Exception):
        """Framework exception to stop a Test Suite."""

        nvme_framework_exception = True

        def __init__(self):
            log.frames("TestSuite.Stop", inspect.getouterframes(inspect.currentframe(), context=1))
            log.info("----> TEST SUITE STOP", indent=False)
            log.info("")
            super().__init__("TestSuite.Stop")


def update_suite_summary(state):

    # clear summary

    state["summary"] = {
        "tests": {"total": 0, "pass": 0, "fail": 0, "skip": 0},
        "rqmts": {"total": 0, "pass": 0, "fail": 0},
        "verifications": {"total": 0, "pass": 0, "fail": 0},
    }
    state["verifications"] = []
    state["rqmts"] = {}

    # read tests and update

    state["summary"]["tests"]["total"] = len(state["tests"])
    state["summary"]["tests"]["pass"] = sum(test["result"] == PASSED for test in state["tests"])
    state["summary"]["tests"]["fail"] = sum(test["result"] == FAILED for test in state["tests"])
    state["summary"]["tests"]["skip"] = sum(test["result"] == SKIPPED for test in state["tests"])

    for test in state["tests"]:
        for step in test["steps"]:
            for verification in step["verifications"]:
                state["verifications"].append(verification)
                state["summary"]["verifications"]["total"] += 1

                if verification["title"] not in state["rqmts"]:
                    state["rqmts"][verification["title"]] = {"pass": 0, "fail": 0, "total": 0}

                state["rqmts"][verification["title"]]["total"] += 1

                if verification["result"] == PASSED:
                    state["summary"]["verifications"]["pass"] += 1
                    state["rqmts"][verification["title"]]["pass"] += 1
                else:
                    state["summary"]["verifications"]["fail"] += 1
                    state["rqmts"][verification["title"]]["fail"] += 1

    # update requirement summary

    state["summary"]["rqmts"]["total"] = len(state["rqmts"])
    for rqmt in state["rqmts"]:
        if state["rqmts"][rqmt]["fail"] == 0:
            state["summary"]["rqmts"]["pass"] += 1
        else:
            state["summary"]["rqmts"]["fail"] += 1

    # update result if not aborted

    if state["result"] != ABORTED:
        test_fails = sum(ver["result"] is not PASSED for ver in state["tests"])
        if test_fails == 0:
            state["result"] = PASSED
        else:
            state["result"] = FAILED

    return state


def update_suite_files(directory="."):
    """Update Test Suite after results files updated.

    This function updates the Test Suite after a user has manually updated the test results.
    This allows the user to enter manual results and then easily create a new dashboard and
    PDF report.

    To manually update a test result edit the results.json file in the test directory.  In
    the ["steps"] section find the step and verification to change.  Change the "result"
    parameter to "PASSED" or "FAILED".  Recommend completing the "reviewer" parameter and
    the "note" parameter with the reason for the change.

    This function updates the following files in a Test Suite:
        results.json
        dashboard.html
        report.pdf
        <test #>
           results.json

    Args:
        description: Directory containing Test Suite to update
    """

    full_directory = os.path.abspath(directory)
    list_of_test_results = glob.glob(f"{full_directory}/*/{RESULTS_FILE}")
    suite_results_file = os.path.join(full_directory, RESULTS_FILE)

    with open(suite_results_file, "r") as file_object:
        suite_results = json.load(file_object)

    log = start_logger(full_directory, logging.IMPORTANT, "updatesuite_console.log")

    log.important(" " + "-" * 90, indent=False)
    log.important(f" UPDATE TEST SUITE : {suite_results['title']}", indent=False)
    log.important(" " + "-" * 90, indent=False)
    log.info(f" Description : {suite_results['description']}", indent=False)
    log.important(f" Directory   : {full_directory}", indent=False)
    log.important("")

    suite_results["tests"] = []

    for result_file in list_of_test_results:
        with open(result_file, "r") as file_object:
            results = json.load(file_object)

        new_results = update_test_summary(results)
        suite_results["tests"].append(new_results)

        with open(result_file, "w") as file_object:
            json.dump(new_results, file_object, ensure_ascii=False, indent=4)

    suite_results = update_suite_summary(suite_results)

    with open(suite_results_file, "w") as file_object:
        json.dump(suite_results, file_object, ensure_ascii=False, indent=4)

    create_reports(
        results_directory=full_directory,
        title=suite_results["title"],
        description=suite_results["description"],
    )


def update_test_summary(state):
    """Update Test Case summary after results files updated."""

    # clear summary

    state["summary"] = {
        "steps": {"total": 0, "pass": 0, "fail": 0},
        "rqmts": {"total": 0, "pass": 0, "fail": 0},
        "verifications": {"total": 0, "pass": 0, "fail": 0},
    }
    state["rqmts"] = {}
    state["verifications"] = []

    # read steps and update

    for step in state["steps"]:
        step_fails = 0

        state["summary"]["steps"]["total"] += 1

        for verification in step["verifications"]:
            state["verifications"].append(verification)
            state["summary"]["verifications"]["total"] += 1

            if verification["title"] not in state["rqmts"]:
                state["rqmts"][verification["title"]] = {"pass": 0, "fail": 0, "total": 0}
                state["summary"]["rqmts"]["total"] += 1

            if verification["result"] == PASSED:
                state["summary"]["verifications"]["pass"] += 1
                state["rqmts"][verification["title"]]["pass"] += 1
            else:
                state["summary"]["verifications"]["fail"] += 1
                state["rqmts"][verification["title"]]["fail"] += 1
                step_fails += 1

        if step_fails == 0:
            state["summary"]["steps"]["pass"] += 1
            step["result"] = PASSED
        else:
            state["summary"]["steps"]["fail"] += 1
            step["result"] = FAILED

    # update requirement summary

    state["summary"]["rqmts"]["total"] = len(state["rqmts"])
    for rqmt in state["rqmts"]:
        if state["rqmts"][rqmt]["fail"] == 0:
            state["summary"]["rqmts"]["pass"] += 1
        else:
            state["summary"]["rqmts"]["fail"] += 1

    # update result unless skipped or aborted

    if state["result"] != SKIPPED and state["result"] != ABORTED:
        failed_steps = sum(step["result"] is not PASSED for step in state["steps"])
        if failed_steps == 0:
            state["result"] = PASSED
        else:
            state["result"] = FAILED

    return state


def verification(rqmt_id, step, title, verified, value):
    """Verification of a requirement.

    Verification is True if a requirement is met and False if not.  For example, the
    verification of requirement 'Media and Integrity Errors shall be 0' is True if there
    are no errors and False if there are errors.

    This function does not return a value but updates the test step and test case with the
    result of the verification.  If step stop_on_fail is True and the verification fails
    step.stop() is called.

    This function is wrapped in a parent function that defines the requirement to verify.
    For example, this parent function verifies there are no prior self-test failures.

    Args:
        rqmt_id: Unique integer ID that identifies the requirement
        step:  The parent TestStep instance
        title: Title of the requirement
        verifiedean, True if the requirement passes verification
        value:  Value to be reported as the result

    .. code-block::

        def no_prior_selftest_failures(step, info):

            value = int(info.parameters["Number Of Failed Self-Tests"])

            verification(
                rqmt_id=12,
                step=step,
                title="Prior self-test failures shall be 0",
                verified=(value == 0),
                value=value,
            )

    The parent functions are included in a python package that can be imported as rqmts.  This
    code shows how to use the verification defined above.

    .. code-block::

        from nvmetools import rqmts, Info, TestStep

        with TestStep("Selftest failures", "Verify there are no prior selftest failures") as step:
            info = Info(test.suite.nvme, directory=step.directory)
            rqmts.no_prior_selftest_failures(step, info)
    """
    frames = inspect.getouterframes(inspect.currentframe(), context=1)
    log.debug(f"  Verification {frames[1].function} called from {frames[2].filename} line {frames[2].lineno}")

    # must update verification number in test suite directly

    step.suite.state["summary"]["verifications"]["total"] += 1
    ver_number = step.suite.state["summary"]["verifications"]["total"]

    if verified:
        log.verbose(f"  PASS #{ver_number} : {title} [value: {value}]")
    else:
        log.info(f"------> FAIL #{ver_number} : {title} [value: {value}]", indent=False)

    state = {
        "number": ver_number,
        "id": rqmt_id,
        "title": title,
        "result": PASSED if verified else FAILED,
        "value": value,
        "time": f"{datetime.datetime.now()}",
        "reviewer": "",
        "note": "",
        "test": step.test.state["title"],
        "test number": step.test.state["number"],
    }
    step.state["verifications"].append(state)
    step.test.update_summary()

    if step.stop_on_fail and not verified:
        step.stop()
