Installation
============
.. code-block:: python

    pip install nvmetools

On Fedora Linux the nvmecmd utility must be granted access to read NVMe devices with the below
commands.  Run the listnvme console command and it will display the below commands with the actual
nvmecmd path.  Run these commands to grant nvmecmd access to read NVMe devices.

.. code-block:: python

    sudo chmod 777 <path to nvmecmd>
    sudo setcap cap_sys_admin,cap_dac_override=ep <path to nvmecmd>

Running any console command before running the above two commands will display the above commands
with <path to nvmecmd> replaced with the actual path.  These can then be cut and pasted into the
terminal.

.. warning::

    It is likely other Linux distributions require the same or similar steps but these have not been
    tested.