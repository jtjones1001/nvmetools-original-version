# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Functions to start and run external processes."""

import inspect
import os
import platform
import signal
import subprocess
import time

from nvmetools.support.log import log

import psutil


class _ZombieProcess(Exception):
    """nvmetools exception indicating a process could not be killed."""

    def __init__(self, msg: str) -> None:
        self.code = 59
        self.nvmetools = True
        super().__init__(msg)


class RunProcess:
    """Runs a process using subprocess class.

    This class starts a process and either waits for the process to exit or returns without waiting.  The wait
    method can be called at any time that waits for the process to exit.  The stop method attempts to stop a
    process gracefully with CTRL-BREAK, if not successful then kills the process.  The kill methods kills
    without attempting to stop gracefully.

    Attributes:
        start_time (float): Time process started (in fractional seconds) of a performance counter.
        end_time (float): Time process ended (in fractional seconds) of a performance counter.
        run_time (float):  Time the process ran in fractional seconds (end_time - start_time)
        process (class) : process created with the subprocess.Popen class.
        return_code (int):  The return code (exit code) of the proces.
        kill_timeout_sec (int): Time to wait for process to exit after sending signal to kill.
        stop_timeout_sec (int): Time to wait for process to stop after sending signal to stop.
    """

    kill_timeout_sec = 2
    stop_timeout_sec = 10
    _test_suppress_kill = False
    _test_suppress_ctrlbreak = False

    def __init__(self, args: list, directory: str, timeout_sec: int = None, wait: bool = True) -> None:
        """Run the process specified in args.

        Start the process specified in args using subprocess.Popen and either wait for the
        process to end or return after it started.  If the wait parameters is True then will
        wait.

        Args:
            args: List containing the process arguments.
            directory: Working directory for the process to run in.
            timeout_sec: Seconds to wait for process to end before timing out.
            wait:  Waits for process to end if true, else return after process started
        """
        log.frames("RunProcess", inspect.getouterframes(inspect.currentframe(), context=1))
        log.debug(f"Process: {args[0]}")
        for arg in enumerate(args, 1):
            log.debug(f"  arg: {arg}")

        self.start_time = time.perf_counter()
        self.end_time = None
        os.makedirs(directory, exist_ok=True)

        self.process = subprocess.Popen(
            args,
            cwd=directory,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.debug(" ")
        log.debug(f"Process ID:            {self.process.pid}")
        if wait:
            self.wait(timeout_sec)
        else:
            log.debug(" ")

    def kill(self) -> None:
        """Kill the running process.

        Kills the process if still running. If the process does not exit within the
        timeout then a ZombieProcess exception is raised.

        Raises:
            _ZombieProcess: Process could not be killed.
        """
        if self.process.poll() is None:
            try:
                psutil_process = psutil.Process(self.process.pid)

                if RunProcess._test_suppress_kill:
                    log.debug("_test_suppress_kill is enabled, kill has been suppressed")
                else:
                    psutil_process.kill()

                try:
                    self.process.wait(RunProcess.kill_timeout_sec)
                except subprocess.TimeoutExpired:
                    pass

                if self.process.poll() is None:
                    log.debug(f"Failed to kill process {self.process.pid}")
                    raise _ZombieProcess(f"Zombie process {self.process.pid} could not be killed")
                else:
                    self.wait()  # updates return code and end time
                    log.debug(f"Killed process {self.process.pid} ")

            except psutil.NoSuchProcess:
                log.debug(f"Kill process called but process {self.process.pid} was not found")

        else:
            log.debug(f"kill process called but process {self.process.pid} was not running")

    def stop(self) -> None:
        """Stop the running process, try gracefully first then kill if necessary.

        Attempts to stop the process by sending the CTRL-BREAK signal.  The CTRL-C signal is
        not used because it doesn't work for remote execution on Windows systems.

        If the process doesn't stop in the timeout then the kill method is called.
        """
        if self.process.poll() is None:
            try:
                psutil_process = psutil.Process(self.process.pid)
                log.debug(f"Stopping process {psutil_process}")

                if RunProcess._test_suppress_ctrlbreak:
                    log.debug("_test_suppress_ctrlbreak is set so CTRL-BREAK is suppressed")
                else:
                    if "Windows" == platform.system():
                        original_handler = signal.getsignal(signal.SIGBREAK)
                        signal.signal(signal.SIGBREAK, signal.SIG_IGN)

                        # Must use CTRL_BREAK_EVENT here but not in signal class
                        psutil_process.send_signal(signal.CTRL_BREAK_EVENT)

                        time.sleep(1)
                        signal.signal(signal.SIGBREAK, original_handler)
                    else:
                        psutil_process.send_signal(signal.SIGINT)
                        time.sleep(1)

                try:
                    self.process.wait(RunProcess.stop_timeout_sec)
                except subprocess.TimeoutExpired:
                    pass

                if self.process.poll() is None:
                    log.debug(f"Failed to stop process {self.process.pid}, trying kill process ")
                    self.kill()
                else:
                    self.wait()
                    log.debug(f"Stopped process {self.process.pid} ")

            except psutil.NoSuchProcess:
                log.debug(f"Stop process called but process {self.process.pid} was not found")

        else:
            log.debug(f"Stop process called but process {self.process.pid} was not running")

    def wait(self, timeout_sec: int = None) -> int:
        """Wait for process to exit.

        Waits the specified time for the process to exit. If process doesn't exit then
        the stop method is called.  If no timeout specified waits indefinitely.

        Args:
           timeout_sec (int) : Time to wait for process to exit in seconds.

        Returns:
            int: The exit code from the process.
        """
        try:
            self.process.wait(timeout_sec)

            if self.end_time is None:
                self.end_time = time.perf_counter()
                self.run_time = self.end_time - self.start_time
                self.return_code = self.process.returncode

                log.debug(f"Process Run Time:      {self.run_time:.3f} seconds")
                log.debug(f"Process Return Code:   {self.process.returncode}")
                log.debug(" ")

        except subprocess.TimeoutExpired:
            log.debug(f"Process {self.process.pid} timeout expired and will be stopped")
            self.stop()

            if self.end_time is None:
                self.end_time = time.perf_counter()
                self.run_time = self.end_time - self.start_time
                self.return_code = self.process.returncode

                log.debug(f"Process Run Time:      {self.run_time:.3f} seconds")
                log.debug(f"Process Return Code:   {self.process.returncode}")
                log.debug(" ")

        return self.return_code
