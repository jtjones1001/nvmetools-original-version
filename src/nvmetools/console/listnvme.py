# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that lists NVMe drives in the system.

.. highlight:: none

Assigns each NVMe drive an NVMe number.  On Windows, the NVMe number is the same as the physical drive number
(2 = physicaldrive2) and on linux it is the /dev/nvme# number (3 = /dev/nvme3).

**Command Line Parameters**

    There are no command line parameters

**Return Value**

    Returns 0 if passes and non-zero if it fails.

**Example**

    .. code-block::

        listnvme

    Example console output

    .. code-block::

        EPIC NVMe Utilities, version 0.0.7, www.epicutils.com, Copyright (C) 2022 Joe Jones

        On Window systems the NVMe number is the physical drive number.
        For example, physicaldrive2 would be listed as NVMe 2.

        On Linux systems the NVMe number is the nvme devices number.
        For example, /dev/nvme2 would be listed as NVMe 2.

            LIST OF NVME DRIVES

            NVMe 0 : Sandisk WDC WDS250G2B0C-00PXH0 250GB
            NVMe 1 : Samsung SSD 970 EVO Plus 250GB

"""  # noqa: E501

import logging
import os
import sys

from nvmetools.apps.nvmecmd import check_nvmecmd_permissions
from nvmetools.info import Info
from nvmetools.support.exit import exit_on_exception
from nvmetools.support.log import start_logger


def main() -> None:
    """List NVMe drives in the system."""
    try:
        directory = os.path.join(os.path.abspath("."))
        log = start_logger(directory, logging.INFO, "listnvme.log")

        check_nvmecmd_permissions()

        info = Info(nvme="*", directory=directory)

        log.info(" On Window systems the NVMe number is the physical drive number.", indent=False)
        log.info(" For example, physicaldrive2 would be listed as NVMe 2.\n", indent=False)

        log.info(" On Linux systems the NVMe number is the nvme devices number.", indent=False)
        log.info(" For example, /dev/nvme2 would be listed as NVMe 2.\n", indent=False)

        log.info("LIST OF NVME DRIVES\n")
        for nvme in info.info["_metadata"]["system"]["nvme list"]:
            nvme_string = nvme.replace("DRIVE", "NVMe")
            log.info(f"{nvme_string}")

        log.info("")
        sys.exit(0)

    except Exception as e:
        exit_on_exception(e)


if __name__ == "__main__":
    main()
