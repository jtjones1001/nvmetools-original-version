# --------------------------------------------------------------------------------------
# Copyright(c) 2022 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
"""Define user settings that can be set based on specific use cases."""

# fmt: off
# flake8: noqa

WEAR_PERCENT_LIMIT = 80             # Limit for Percentage Used, Data Written, Warranty Hours
THROTTLE_PERCENT_LIMIT = 1          # Limit for percentage throttled checked by the drive health test.
LINEAR_LIMIT = 0.8                  # Limit for linearity of self-test progress reported.
                                    #  ... Range is 0 - 1.0 where 1.0 is perfect linearity.
ADMIN_COMMAND_AVG_LIMIT_MS = 50     # Limits for average latency of admin commands
ADMIN_COMMAND_MAX_LIMIT_MS = 500    # Limits for maximum latency of admin commands

# --------------------------------------------------------------------------------------
# Test ID.  Keeping the test ID in this class makes it easier to ensure they are all
# unique and in the order the tests will be run
# --------------------------------------------------------------------------------------
class TestId:

    DRIVE_INFO = 10  # Keep at 10 for reporting to find it

    NEW_DRIVE = 11
    DRIVE_WEAR = 12
    DRIVE_HEALTH = 13
    DRIVE_FEATURES = 14
    DRIVE_DIAGNOSTIC = 15

    DRIVE_CHANGE = 900

# --------------------------------------------------------------------------------------
# Requirement ID.  Keeping the requirement ID in this class makes it easier to ensure
# they are all unique and to group them into categories
# --------------------------------------------------------------------------------------
class RqmtId:

    NO_CRITICAL_WARNINGS = "001"
    NO_STATIC_PARAMETER_CHANGE = "002"
    NO_COUNTER_PARAMETER_DECREMENT = "003"
    NO_ERROR_INCREASE = "004"
    NO_IO_ERRORS = "005"
    NO_IO_DATA_CORRUPTION = "006"
    PWR_ON_HOURS_CHANGE = "007"
    NO_THROTTLE = "008"

    PERCENTAGE_USED = "110"
    AVAILABLE_SPARE = "111"
    DATA_WRITTEN = "112"
    POWERON_HOURS = "113"

    NO_SELFTEST_FAILS = "114"
    NO_MEDIA_ERRORS = "115"
    TIME_THROTTLED = "116"
    CRITICAL_TIME = "117"

    ADMIN_COMMAND_RELIABILITY = "160"
    ADMIN_COMMAND_CHANGES = "161"
    ADMIN_COMMAND_AVG_LATENCY = "162"
    ADMIN_COMMAND_MAX_LATENCY = "163"

    SELFTEST_RESULT = "200"
    SELFTEST_RUNTIME = "201"
    SELFTEST_MONOTONICITY = "202"
    SELFTEST_LINEARITY = "203"
    SELFTEST_HOURS = "204"

    EXT_SELFTEST_RESULT = "210"
    EXT_SELFTEST_RUNTIME = "211"
    EXT_SELFTEST_MONOTONICITY = "212"
    EXT_SELFTEST_LINEARITY = "213"
    EXT_SELFTEST_HOURS = "214"

USER_RQMT_ID = 900
