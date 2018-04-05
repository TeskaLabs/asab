How to ...
==========

This chapter contains asorted collection of useful ASAB guides.


How to build an web application server using ASAB
-------------------------------------------------

ASAB provides a :py:mod:`asab.web` module.
This module offers an integration of a :py:mod:`aiohttp` `web server <http://aiohttp.readthedocs.io/en/stable/web.html>`_.

1. Before you start, make sure that you have :py:mod:`aiohttp` module installed.

.. code-block:: bash

	$ pip3 install aiohttp

2. The following code creates a simple web server application

.. code:: python

	#!/usr/bin/env python3
	import asab
	import aiohttp

	class MyApplication(asab.Application):

	    async def initialize(self):
	        # Loading the web service module
	        from asab.web import Module
	        self.add_module(Module)

	        # Locate web service
	        svc = self.get_service("asab.WebService")

	        # Add a route
	        # `svc.Webapp` is an `aiohttp.web.Application` instance
	        svc.WebApp.router.add_get('/hello', self.hello)

	    # Simplistic view
	    async def hello(self, request):
	        return aiohttp.web.Response(text='Hello!\n')

	if __name__ == '__main__':
	    app = MyApplication()
	    app.run()

3. Test it with `curl`

.. code-block:: bash

	$ curl http://localhost:8080/hello
	Hello!


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

	$ pip3 install asab python-daemon


6. (Optionally if you want to use :py:mod:`asab.web` module) install aiohttp dependecy

.. code-block:: bash

	$ pip3 install aiohttp


