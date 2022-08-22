# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Console command that reads information from NVMe drive.

Reads NVMe drive information using the Admin Commands: Get Log Page, Get Feature, Identify Controller, and
Identify Namespace. A few parameters, such as PCIe location and link info, are read from the OS.

Logs to the current directory.  The readnvme.log contains the console output and the nvme.info.json contains
the NVMe parameters in json format.

The debug and verbose parameters enable additional logging and keeps additional files for the purpose of
debugging the script or device failure. The full debug output is alway saved in the debug.log regardless of
these parameters.

Command Line Parameters
    --nvme, -n      Integer NVMe device number, can be found using listnvme.
    --pdf, -p       Flag to create PDF report.
    --describe, -d  Display descriptions for each parameter.
    --all, -a       Display all parameters.
    --list, -l      Display parameters as a list.
    --hex, -x       Display raw data read as hex format.
    --run_id, -i    String to use for the results directory name.
    --verbose, -V   Flag for additional logging, verbose logging.
    --debug, -D     Flag for maximum logging for debugging.

**Return Value**

    Returns 0 if the read passes and non-zero if it fails.

**Example**

    This example reads the information of NVMe 0.  To display all NVMe parameters to the console add --all.
    To display the raw data in hex format use --hex.

    .. highlight:: none
    .. code-block:: python

        readnvme  --nvme 0
        readnvme  --nvme 0 --all
        readnvme  --nvme 0 --hex

    * `Example console output (readnvme.log) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/readnvme/readnvme.log>`_
    * `Example console output with --all (readnvme.log) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/readnvme_all/readnvme.log>`_
    * `Example console output with --hex (readnvme.log) <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/readnvme_hex/readnvme.log>`_

"""  # noqa: E501
import argparse
import logging
import os
import sys

from nvmetools.apps.nvmecmd import check_nvmecmd_permissions
from nvmetools.info import Info
from nvmetools.support.exit import exit_on_exception
from nvmetools.support.log import start_logger


def _parse_arguments() -> None:
    """Parse input arguments from command line."""
    parser = argparse.ArgumentParser(
        description=read_nvme.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-n", "--nvme", type=int, default=0, help="NVMe drive number (e.g. 0)", metavar="#")
    parser.add_argument("-d", "--describe", help="Display parameter descriptions", action="store_true")
    parser.add_argument("-l", "--list", dest="as_list", help="Display parameters as list", action="store_true")
    parser.add_argument(
        "-x", "--hex", dest="as_hex", help="Display information in hex format", action="store_true"
    )
    parser.add_argument("-a", "--all", dest="as_all", help="Display all parameters", action="store_true")
    parser.add_argument("-p", "--pdf", dest="create_pdf", help="Create a pdf report", action="store_true")
    parser.add_argument("-V", "--verbose", help="Verbose log mode", action="store_true")
    parser.add_argument("-D", "--debug", help="Debug mode", action="store_true")
    return vars(parser.parse_args())


def read_nvme(
    nvme: int = 0,
    as_list: bool = False,
    as_hex: bool = False,
    as_all: bool = False,
    describe: bool = False,
    create_pdf: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Read and display NVMe information.

    Reads NVMe information using the nvmecmd utility. This utility creates a file named
    nvme.info.json with the entire set of information. This script reads nvme.info.json
    and displays some or all of the NVMe information.

    All parameters are displayed if --all specified.  Parameters are displayed as a list
    if --list specified.  Parameter descriptions are displayed if --describe specified.

    Information is displayed as hex data if --hex specified.  If this option is specified
    these options have no effect: --list, --all, and --description.

    The console output is logged to readnvme.log.  If the --pdf option is specified an
    nvme_info.pdf file is created.  All information is in the json file nvme.info.json.

    Additional logging for debug occurs if --debug or --verbose are specified.  The most
    logging occurs with the debug option.

    Args:
        nvme (int): NVMe device number.  Can be found with listnvme.
        as_hex (bool):  Displays information in hex format if True.
        as_list (bool):  Displays information as a list if True.
        as_all (bool):  Displays all parameters if True.
        describe (bool):  Display parameter descriptions if True.
        create_pdf (bool): Creates the pdf report if True.
        verbose (bool):  Displays additional logging if True.
        debug (bool): Displays all possible logging if True.

    Returns:
       returns 0 if all tests pass, else returns integer error code
    """
    try:
        directory = os.path.join(os.path.abspath("."))
        log_level = logging.INFO

        if debug:
            log_level = logging.DEBUG
        elif verbose:
            log_level = logging.VERBOSE

        start_logger(directory, log_level, "readnvme.log")
        check_nvmecmd_permissions()

        info = Info(
            nvme=nvme,
            directory=directory,
            description=describe,
            verbose=verbose,
        )
        if as_hex:
            info.show_hex()
            sys.exit()

        if as_all:
            info.show_all()
        else:
            if as_list:
                info.show_list()
            else:
                info.show()

        # Create report if specified, only load report module if using it because it's slow

        if create_pdf:
            from nvmetools.report import InfoReport

            report = InfoReport(info)
            report.save()

        sys.exit()

    except Exception as e:
        exit_on_exception(e)


def main() -> None:
    """Allow command line operation with unique arguments."""
    args = _parse_arguments()
    read_nvme(**args)


if __name__ == "__main__":
    main()
