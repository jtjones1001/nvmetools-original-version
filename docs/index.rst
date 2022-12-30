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

updatesuite
-----------
.. automodule:: nvmetools.console.updatesuite


Modules - Info
==============
This module provides functionality to read information about NVMe drives.

nvmetools.support.info
----------------------
.. automodule:: nvmetools.support.info
    :members:


Modules - NVMe Test Framework
=============================
This modules provides classes and functions to test NVMe drives.

nvmetools.support.framework
---------------------------
.. automodule:: nvmetools.support.framework
    :members:


.. toctree::
   :maxdepth: 2
   :caption: Contents:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
