# --------------------------------------------------------------------------------------
# Copyright(c) 2023 Joseph Jones,  MIT License @  https://opensource.org/licenses/MIT
# --------------------------------------------------------------------------------------
from nvmetools import Info, TestCase, TestStep, rqmts


def firmware_security(suite):
    """Verify firmware security features.

    Verifies invalid files cannot be downloaded and activated, partial downloads cannot be activated
    etc.
    """
    with TestCase(suite, "Firmware security", firmware_security.__doc__) as test:
        raise test.Skip
