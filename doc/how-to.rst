How to ...
==========

This chapter contains asorted collection of useful ASAB guides.


How to deploy ASAB into LXC container
-------------------------------------

1. Prepare LXC container based on Alpine Linux

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

	$ apk add --no-cache python3
	$ python3 -m ensurepip
	$ rm -r /usr/lib/python*/ensurepip
	$ pip3 install --upgrade pip setuptools


5. Deploy ASAB

.. code-block:: bash

	$ pip3 install asab python-daemon


6. (Optionally if you want to use :py:mod:`asab.web` module) install aiohttp dependecy

.. code-block:: bash

	$ pip3 install aiohttp


7. Use OpenRC to automatically start/stop ASAB application

.. code-block:: bash

	$ vi /etc/init.d/asab-app


Adjust the example of `OpenRC init file <https://github.com/TeskaLabs/asab/blob/master/doc/asab-openrc>`_. 

.. code-block:: bash

	$ chmod a+x /etc/init.d/asab-app
	$ rc-update add asab-app


How to start/stop ASAB application with systemd
-----------------------------------------------

1. Create a new Systemd unit file in /etc/systemd/system/:

.. code-block:: bash

	$ sudo vi /etc/systemd/system/asab.service


Adjust the example of `SystemD unit file <https://github.com/TeskaLabs/asab/blob/master/doc/asab.service>`_. 


2. Let systemd know that there is a new service:

.. code-block:: bash

	$ sudo systemctl enable asab


To reload existing unit file after changing, use this:

.. code-block:: bash

	$ sudo systemctl daemon-reload


3. ASAB Application Server service for systemd is now ready.


Start of ASAB Server
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

	$ sudo service asab start


Stop of ASAB Server
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

	$ sudo service asab stop

