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


.. Hidden TOCs

.. toctree::
   :caption: Tool User
   :maxdepth: 2
   :hidden:

   info_commands
   test_commands

.. toctree::
    :maxdepth: 2
    :caption: Test Developer
    :hidden:

    framework
    test_suites
    test_cases
    test_steps
    verifications
    information



