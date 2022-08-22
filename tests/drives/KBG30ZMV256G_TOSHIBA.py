# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Define drive specific requirements for user environment."""

from nvmetools.info import Info
from nvmetools.nvme_test import NvmeTest, verify_requirement
from nvmetools.settings import USER_RQMT_ID
from nvmetools.support.conversions import as_float

# Add information about the drive that can only be read from the drive specification
# and cannot be read programmatically.  This includes warranty, TBW, and drive type.

DRIVE_SPECIFICATION = {
    "model": "KBG30ZMV256G TOSHIBA                    ",
    "warranty": 5,
    "tbw": 150,
    "client": True,
    "drive type": "Client",
    "hours per day": 8,
    "warranty hours": 5 * 365 * 8,
    "short burst minimum bandwidth (GB/s)": {
        "Sequential Write, QD32, 128KiB": 1.5,
        "Sequential Read, QD32, 128KiB": 1.5,
        "Random Write, QD1, 4KiB": 0.02,
        "Random Read, QD1, 4KiB": 0.02,
        "Random Write, QD32, 4KiB": 0.2,
        "Random Read, QD32, 4KiB": 0.2,
    },
    "long burst minimum bandwidth (GB/s)": {
        "Sequential Write, QD32, 128KiB": 1.0,
        "Sequential Read, QD32, 128KiB": 1.0,
        "Random Write, QD32, 4KiB": 0.1,
        "Random Read, QD32, 4KiB": 0.1,
    },
}


def verify_user_requirements(test: NvmeTest, info: Info) -> None:
    """Define drive specific requirements.

    This function is called by the drive_features module.  It provides a way for users
    to create drive specific requirements for their environment.

    The first section defines the requirements, the next verifies the requirements,
    and the last section creates the table to include in the pdf report.

    info : instance of drive information from the Info class
    test : instance of NvmeTest
    """
    verify_requirement(
        str(USER_RQMT_ID),
        name="PCIe bus width must be x2",
        limit="x2",
        value=info.parameters["PCI Width"],
        passed=(info.parameters["PCI Width"] == "x2"),
        test=test,
    )
    verify_requirement(
        str(USER_RQMT_ID + 1),
        name="PCIe bus speed must be Gen3 8.0GT/s",
        limit="Gen3 8.0GT/s",
        value=info.parameters["PCI Speed"],
        passed=(info.parameters["PCI Speed"] == "Gen3 8.0GT/s"),
        test=test,
    )
    verify_requirement(
        str(USER_RQMT_ID + 2),
        name="Firmware activation without reset must be supported",
        limit="Supported",
        value=info.parameters["PCI Speed"],
        passed=(info.parameters["Firmware Activation Without Reset"] == "Supported"),
        test=test,
    )
    verify_requirement(
        str(USER_RQMT_ID + 3),
        name="RTD3 Entry Latency (RTD3E) must be less than 10,000,000 uS",
        limit=10000000,
        value=as_float(info.parameters["RTD3 Entry Latency (RTD3E)"].split()[0]),
        passed=(as_float(info.parameters["RTD3 Entry Latency (RTD3E)"].split()[0]) < 10000000),
        test=test,
    )
    verify_requirement(
        str(USER_RQMT_ID + 4),
        name="RTD3 Resume Latency (RTD3R) must be less than 1,000,000 uS",
        limit=1000000,
        value=as_float(info.parameters["RTD3 Resume Latency (RTD3R)"].split()[0]),
        passed=(as_float(info.parameters["RTD3 Resume Latency (RTD3R)"].split()[0]) < 10000000),
        test=test,
    )
    verify_requirement(
        str(USER_RQMT_ID + 5),
        name="Power State 0 Maximum Power (MP) must be less than 5 Watts",
        limit=5,
        value=as_float(info.parameters["Power State 0 Maximum Power (MP)"].split()[0]),
        passed=(as_float(info.parameters["Power State 0 Maximum Power (MP)"].split()[0]) < 5),
        test=test,
    )

    # This list contains information to be displayed in the RESULTS section of the test
    # report for this test

    test.data["report table"] = [
        ["PCI Width", info.parameters["PCI Width"], "Must be x2"],
        ["PCI Speed", info.parameters["PCI Speed"], "Must be Gen3 8.0GT/s"],
        [
            "Firmware Activation Without Reset",
            info.parameters["Firmware Activation Without Reset"],
            "Must be supported",
        ],
        [
            "RTD3 Entry Latency",
            info.parameters["RTD3 Entry Latency (RTD3E)"].split("(")[0],
            "Must be less than 10,000,000 uS",
        ],
        [
            "RTD3 Resume Latency",
            info.parameters["RTD3 Resume Latency (RTD3R)"].split("(")[0],
            "Must be less than 1,000,000 uS",
        ],
        [
            "Power State 0 Maximum Power",
            info.parameters["Power State 0 Maximum Power (MP)"],
            "Must be less than 5 Watts",
        ],
    ]
