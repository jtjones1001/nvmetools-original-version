import os
import logging
import time
import pytest
import sys

from nvmetools.apps.nvmecmd import Read
from nvmetools.support.log import  start_logger

top_directory = os.path.split( os.path.dirname(__file__))[0]
base_directory = os.path.join(top_directory,"__results__","nvmecmd")
log_directory = os.path.join(top_directory,"__results__")

nvme = 0

log = start_logger(log_directory, logging.DEBUG, "pytest.log")

log.info("Running test_nvmecmd.py")
#---------------------------------------------------------------------------
def test_read():
    directory = os.path.join(base_directory,"test_read")

    Info = Read(nvme,directory)

    assert Info.return_code == 0
    assert   Info.run_time < 1.5
#---------------------------------------------------------------------------
def test_logpage2_read():
    directory = os.path.join(base_directory,"test_read")

    Info = Read(nvme,directory,cmd_file="logpage02")

    assert Info.return_code == 0
    assert   Info.run_time < 1.5
#---------------------------------------------------------------------------
def test_two_sample_read():
    directory = os.path.join(base_directory,"test_two_sample_read")

    Info = Read(nvme,directory,samples=2,interval=3000)

    assert Info.return_code == 0
    assert   Info.run_time  > 6.0


# add self-test, logpage2 cmd file, stop, corrupted json file (copy bad file over)
