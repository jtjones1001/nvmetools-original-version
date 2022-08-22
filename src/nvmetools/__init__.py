# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Read and test NVMe drives using nvmecmd utility.

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
"""
import importlib.metadata
import os
__copyright__ = "Copyright (C) 2022 Joe Jones"
__brandname__ = "EPIC NVMe Utilities"
__website__ = "www.epicutils.com"

TESTRUN_DIRECTORY = os.path.expanduser("~/Documents/nvme/run")
SPECIFICATION_DIRECTORY = os.path.expanduser("~/Documents/nvme/drives")

# TODO:  RTD fails to get the metadata, check into this some more
try:
   metadata = importlib.metadata.metadata("nvmetools")
   __version__ = metadata["version"]
   __package_name__ = metadata["name"]
except Exception:
   __version__ ="N/A"
   __package_name__  = "N/A"


PACKAGE_DIRECTORY = os.path.dirname(__file__)
SRC_DIRECTORY = os.path.split(PACKAGE_DIRECTORY)[0]
TOP_DIRECTORY = os.path.split(SRC_DIRECTORY)[0]
RESOURCE_DIRECTORY = os.path.join(SRC_DIRECTORY, "nvmetools", "resources")
