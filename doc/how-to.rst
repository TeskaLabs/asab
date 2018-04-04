How to ...
==========

This chapter contains asorted collection of useful ASAB guides.


How to deploy ASAB into LXC container
-------------------------------------

1. Prepare LXC container based on Alpine Linux

.. code-block:: bash

	$ lxc launch images:alpine/edge asab


2. Swich into a container

.. code-block:: bash

	$ lxc exec asab -- /bin/ash


3. Adjust a container

.. code-block:: bash

	$ sed -i 's/^tty/# tty/g' /etc/inittab


4. Prepare Python3 environment

.. code-block:: bash

	$ apk add --no-cache python3
	$ python3 -m ensurepip
	$ rm -r /usr/lib/python*/ensurepip
	$ pip3 install --upgrade pip setuptools


5. Deploy ASAB

.. code-block:: bash

	$ pip3 install asab


6. (Optionally if you want to use asab.web module) install aiohttp dependecy

.. code-block:: bash

	$ pip3 install aiohttp


