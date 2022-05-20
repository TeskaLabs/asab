The web server
==============

ASAB provides a web server in a :py:mod:`asab.web` module.
This module offers an integration of a :py:mod:`aiohttp` `web server <http://aiohttp.readthedocs.io/en/stable/web.html>`_.

1. Before you start, make sure that you have :py:mod:`aiohttp` module installed.

.. code-block:: bash

	$ pip3 install aiohttp

2. The following code creates a simple web server application

.. code:: python

	#!/usr/bin/env python3
	import asab
	import asab.web
	import aiohttp

	class MyApplication(asab.Application):

	    def __init__(self):
	        super().__init__()

	        # Load the web service module
	        self.add_module(asab.web.Module)

	        # Locate the web service
	        websvc = self.get_service("asab.WebService")

	        # Create a web container
	        container = asab.web.WebContainer(websvc, 'my:web', config={"listen": "0.0.0.0:8080"})

	        # Add a route to the handler
	        container.WebApp.router.add_get('/hello', self.hello)

	    # This is the web request handler
	    async def hello(self, request):
	        return aiohttp.web.Response(text='Hello!\n')

	if __name__ == '__main__':
	    app = MyApplication()
	    app.run()

3. Test it with `curl`

.. code-block:: bash

	$ curl http://localhost:8080/hello
	Hello!


Web Service
-----------

.. py:currentmodule:: asab.web.service

.. py:class:: WebService

Service localization example:

.. code:: python

	from asab.web import Module
	self.add_module(Module)
	svc = self.get_service("asab.WebService")


.. py:attribute:: WebService.Webapp

An instance of a `aiohttp.web.Application` class.

.. code:: python

	svc.WebApp.router.add_get('/hello', self.hello)


Configuration
-------------

TODO: Listen at `0.0.0.0:80`



Sessions
--------

ASAB Web Service provides an implementation of the web sessions.


.. py:currentmodule:: asab.web.session

.. py:class:: ServiceWebSession

TODO: ...


.. py:function:: session_middleware(storage)

TODO: ...

