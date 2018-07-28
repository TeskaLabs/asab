Containerisation
================

ASAB is designed for deployment into containers such as LXC/LXD or Docker.
It allows to build e.g. microservices that provides REST interface or consume MQ messages while being deployed into a container for a sake of the infrastructure flexibility.


ASAB in a LXC/LXD container
---------------------------

1. Prepare LXC/LXD container based on Alpine Linux

.. code-block:: bash

	$ lxc launch images:alpine/3.8 asab


2. Swich into a container

.. code-block:: bash

	$ lxc exec asab -- /bin/ash


3. Adjust a container

.. code-block:: bash

	$ sed -i 's/^tty/# tty/g' /etc/inittab


4. Prepare Python3 environment

.. code-block:: bash

	$ apk update
	$ apk upgrade
	$ apk add --no-cache python3
	$ apk add --no-cache python3
	$ python3 -m ensurepip
	$ rm -r /usr/lib/python*/ensurepip
	$ pip3 install --upgrade pip setuptools


5. Deploy ASAB

.. code-block:: bash

	$ pip3 install asab


6. Deploy dependencies

.. code-block:: bash

	$ pip3 install asab python-daemon


7. (Optionally if you want to use :py:mod:`asab.web` module) install aiohttp dependecy

.. code-block:: bash

	$ pip3 install aiohttp


8. Use OpenRC to automatically start/stop ASAB application

.. code-block:: bash

	$ vi /etc/init.d/asab-app


Adjust the example of `OpenRC init file <https://github.com/TeskaLabs/asab/blob/master/doc/asab-openrc>`_. 

.. code-block:: bash

	$ chmod a+x /etc/init.d/asab-app
	$ rc-update add asab-app


*Note*: If you need to install python packages that require compilation using C compiler, you have to add following dependencies:

.. code-block:: bash

	$ apk add python3-dev
	$ apk add gcc
	$ apk add musl-dev


