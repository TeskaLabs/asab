Web Server Tutorial
===================

Welcome to a tutorial on how to create a simple web server with ASAB.


The code
--------

.. include:: web1/app.py
   :code: python

| To start the application, store above code in a file ``app.py``.
| Use ``python3 app.py`` to run it.

The ASAB web server is now available at http://localhost:8080/.


Deeper look
-----------

.. code:: python

    #!/usr/bin/env python3
    import asab

    class MyWebApplication(asab.Application):

        async def initialize(self):
            pass

    if __name__ == '__main__':
        app = MyWebApplication()
        app.run()

This is a standard ASAB code that declares the application class and establishes ``main()`` function for the application.
The :any:`Application.initialize()` method is an application lifecycle method that allows to extend standard initialization of the application with a custom code.

.. code:: python

    import asab.web
    import aiohttp.web

The ASAB web server is a module of ASAB, that is available at `asab.web` for importing.
ASAB web server is built on top of `aiohttp.web <https://docs.aiohttp.org/en/stable/web.html>`_ library.
You can freely use any functionality from `aiohttp.web` library, ASAB is designed to be as much compatible as possible.


.. code:: python

    self.add_module(asab.web.Module)

This is how you load the ASAB module into the application.
The ``asab.web.Module`` provides a ``asab.WebService`` aka a web server.


.. code:: python

    websvc = self.get_service("asab.WebService")

This is how locate a service.


.. code:: python

    websvc.WebApp.router.add_get('/', self.index)

The web service ``websvc`` provides default web application ``WebApp``, which in turn provides a ``router``.
The router is used to map URLs to respective handlers (``self.index`` in this example).
It means that if you access the web server with a path ``/``, it will be handled by a ``self.index()``.


.. code:: python

    async def index(self, request):
        return aiohttp.web.Response(text='Hello, world.\n')

The ``index()`` method is a handler.
A handler must be a coroutine that accepts a ``aiohttp.web.Request`` instance as its only argument and returns a ``aiohttp.web.Response`` instance or equivalent.

For more information, go to `aiohttp.web handler manual page <https://docs.aiohttp.org/en/stable/web_quickstart.html#handler>`_.
