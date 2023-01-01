Welcome to the nvmetools documentation
======================================
The nvmetools python package to read and test NVMe drives.

.. warning::
   This is a beta release and has only been tested on a small number of drives, systems, and OS.

Installation
================
.. code-block:: python

    pip install nvmetools

On Linux OS the nvmecmd utility must be granted access to read NVMe devices with the below commands.  Run
the listnvme console command and it will display the below commands with the actual nvmecmd path.  Run these
commands to grant nvmecmd access to read NVMe devices.

.. code-block:: python

    sudo chmod 777 <path to nvmecmd>
    sudo setcap cap_sys_admin,cap_dac_override=ep <path to nvmecmd>

Console commands
================
Console commands are entered directly into the linux terminal or Windows command prompt (CMD).

listnvme
----------
.. automodule:: nvmetools.console.listnvme

readnvme
--------
.. automodule:: nvmetools.console.readnvme

checknvme
---------
.. automodule:: nvmetools.console.checknvme


Modules - Generic
=================
The modules in this section provide functionality to read, test, and report on NVMe drives.  They are
designed to be imported into higher level python scripts.

nvmetools.info
--------------
.. automodule:: nvmetools.info
    :members:

nvmetools.report
----------------
.. automodule:: nvmetools.report
    :members:

nvmetools.nvme_test
-------------------
.. automodule:: nvmetools.nvme_test
    :members: NvmeTest, NvmeTestSuite


Modules - NVMe Features
=======================
Each modules in this section provide a function to test a specific NVMe feature.  These modules are called
from the checknvme console command (checknvme.py)

nvmetools.features.drive_info
-----------------------------------
.. automodule:: nvmetools.features.drive_info

nvmetools.features.drive_wear
-----------------------------------
.. automodule:: nvmetools.features.drive_wear

nvmetools.features.drive_health
-----------------------------------
.. automodule:: nvmetools.features.drive_health

nvmetools.features.drive_features
-----------------------------------
.. automodule:: nvmetools.features.drive_features

nvmetools.features.drive_diagnostic
-----------------------------------
.. automodule:: nvmetools.features.drive_diagnostic

nvmetools.features.drive_changes
-----------------------------------
.. automodule:: nvmetools.features.drive_changes


Future Expansion
=======================
This section lists possible expansions that have been implemented as proof of concepts but not included in
this release.  These examples provide an idea of how this package can be expanded.

  * Fully automated integration test suite using nvmetools and fio. This test suite runs several functional
    and performance tests and then creates a PDF test summary report.  Below is an example report.

    `Test Report for WDC 250GB on Fedora 35 <https://github.com/jtjones1001/nvmetools/blob/e4dbba5f95b5a5b621d131e6db3ea104dc51d1f3/src/nvmetools/resources/documentation/nvme_test.pdf>`_

  * Integration with the TestRail test database system. The TestRail website is used to start the above
    test suite on one or more remote computers.  When the test suite finishes the TestRail database (and
    website) is automatically updated with the results.

  * Integration with a file server.  When the above test suite completes all log and data files are
    copied to a Dropbox account that acts as a file server.   The TestRail database is then updated with
    hyperlinks to the logs and PDF report located on Dropbox.



.. toctree::
   :maxdepth: 2
   :caption: Contents:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
