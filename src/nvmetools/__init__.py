# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Test and report framework.

This package uses the following:

   - black formatter with wider line length defined in pyproject.toml
   - flake8 linter with custom settings defined in setup.cfg
   - pytest unit tests defined in tests folder
   - The Google Docstring format.  Style Guide:  http://google.github.io/styleguide/pyguide.html
   - Sphinx extension: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html

To release package to test pypi:
   python3 -m build
   twine check dist/*
   twine upload -r testpypi dist/*

To disable pycache in venv...

   export PYTHONDONTWRITEBYTECODE=1

firefox view mode
 about:config, pdfjs.defaultZoomValue to page-fit

"""

import os
from importlib.metadata import metadata

__copyright__ = "Copyright (C) 2023 Joe Jones"
__brandname__ = "EPIC NVMe Utilities"
__website__ = "www.epicutils.com"
__package_name__ = "nvmetools"

try:
    __version__ = metadata("nvmetools")["Version"]
except Exception:
    __version__ = "N/A"

TEST_SUITE_DIRECTORY = os.path.expanduser("~/Documents/nvmetools/suites")
USER_INFO_DIRECTORY = os.path.expanduser("~/Documents/nvmetools/drives")

PACKAGE_DIRECTORY = os.path.dirname(__file__)
SRC_DIRECTORY = os.path.split(PACKAGE_DIRECTORY)[0]
TOP_DIRECTORY = os.path.split(SRC_DIRECTORY)[0]
RESOURCE_DIRECTORY = os.path.join(PACKAGE_DIRECTORY, "resources")
DEFAULT_INFO_DIRECTORY = os.path.join(RESOURCE_DIRECTORY, "drives")
RESULTS_FILE = "result.json"

import nvmetools.requirements as rqmts
import nvmetools.apps.fio as fio

from nvmetools.support.log import log
from nvmetools.support.info import Info, InfoSamples
from nvmetools.support.framework import TestCase, TestStep, TestSuite

import nvmetools.steps as steps
import nvmetools.cases as tests
