Application
===========

.. py:currentmodule:: asab

.. py:class:: Application()

The :py:class:`Application` class maintains the global application state.
You can provide your own implementation by creating a subclass.
There should be only one :py:class:`Application` object in the process.

Subclassing:

.. code:: python

    import asab

    class MyApplication(asab.Application):
        pass

    app = MyApplication()
    app.run()


Direct use of :py:class:`Application` object:

.. code:: python

	import asab

	app = asab.Application()
	app.run()



Event Loop
----------

.. py:attribute:: Application.Loop

The :py:mod:`asyncio` event loop that is used by this application.

.. code:: python

    asyncio.ensure_future(my_coro(), loop=Application.Loop)


Publish-Subcribe
----------------

.. py:attribute:: Application.PubSub

The application-wide Publish-Subscribe message bus.

For more details, go to :py:class:`asab.PubSub`.

Well-Known Messages 
^^^^^^^^^^^^^^^^^^^

.. option:: Application.init!

This message is published when application is in the init-time.
It is actually one of the last things done in init-time, so the application environment is almost ready for use.
It means that configuration is loaded, logging is setup, the event loop is constructed etc.


.. option:: Application.run!

This message is emitted when application enters the run-time.


.. option:: Application.exit!

This message is emitted when application enter the exit-time.


.. option:: Application.tick!
.. option:: Application.tick/10!
.. option:: Application.tick/60!
.. option:: Application.tick/300!
.. option:: Application.tick/600!
.. option:: Application.tick/1800!
.. option:: Application.tick/3600!
.. option:: Application.tick/43200!
.. option:: Application.tick/86400!

The application publish periodically "tick" messages.
The default tick frequency is 1 second but you can change it by configuration ``[general] tick_period``.
:any:`Application.tick!` is published every tick. :any:`Application.tick/10!` is published every 10th tick and so on.


Measurements and Metrics
------------------------

.. py:attribute:: Application.Metrics

Application Metrics.

For more details, see :py:class:`asab.metrics.Metrics`.


Application Lifecycle
---------------------

The application lifecycle is divided into 3 phases: init-time, run-time and exit-time.

Init-time
^^^^^^^^^

.. py:method:: Application.__init__()

The init-time happens during :py:class:`Application` constructor call.
The Publish-Subscribe message :any:`Application.init!` is published during init-time.
The :class:`Config` is loaded during init-time.


.. py:method:: Application.initialize()

The application object executes asynchronous callback ``Application.initialize()``, which can be overriden by an user.

.. code:: python

    class MyApplication(asab.Application):
        async def initialize(self):
            # Custom initialization
            from module_sample import Module
            self.add_module(Module)


Run-time
^^^^^^^^

.. py:method:: Application.run()

Enter a run-time. This is where the application spends the most time typically.
The Publish-Subscribe message :any:`Application.run!` is published when run-time begins.


.. py:method:: Application.main()

The application object executes asynchronous callback ``Application.main()``, which can be overriden.
If ``main()`` method is completed without calling ``stop()``, then the application server will run forever (this is the default behaviour).

.. code:: python

    class MyApplication(asab.Application):
        async def main(self):
            print("Hello world!")
            self.stop()


.. py:method:: Application.stop()

The method  ``Application.stop()`` gracefully terminates the run-time and commence the exit-time.
This method is automatically called by ``SIGINT`` and ``SIGTERM``. It also includes a response to ``Ctrl-C`` on UNIX-like system.
When this method is called 3x, it abruptly exits the application (aka emergency abort).

*Note:* You need to install :py:mod:`win32api` module to use ``Ctrl-C`` or an emergency abord properly with ASAB on Windows. It is an optional dependency of ASAB.


Exit-time
^^^^^^^^^

.. py:method:: Application.finalize()

The application object executes asynchronous callback ``Application.finalize()``, which can be overriden by an user.

.. code:: python

    class MyApplication(asab.Application):
        async def finalize(self):
            # Custom finalization
            ...


The Publish-Subscribe message :any:`Application.exit!` is published when exit-time begins.


Module registry
---------------

For more details see :py:class:`Module` class.

.. py:method:: Application.add_module(module_class)

Initialize and add a new module.
The ``module_class`` class will be instantiated during the method call.


.. code:: python

    class MyApplication(asab.Application):
        async def initialize(self):
            from my_module import MyModule
            self.add_module(MyModule)

.. py:attribute:: Application.Modules

A list of modules that has been added to the application.


Service registry
----------------

Each service is identified by its unique service name.
For more details see :py:class:`Service` class.

.. py:method:: Application.get_service(service_name)

Locate a service by its service name in a registry and return the ``Service`` object.

.. code:: python

    svc = app.get_service("service_sample")
    svc.hello()


.. py:attribute:: Application.Services

A dictionary of registered services.


Command-line parser
-------------------

.. py:method:: Application.parse_args()

The application object calls this method during init-time to process a command-line arguments.
:py:mod:`argparse` is used to process arguments.
You can overload this method to provide your own implementation of command-line argument parser.

Default command-line arguments:

.. option:: -h , --help

Show a help.


.. option:: -c <CONFIG>,--config <CONFIG>

Load configuration file from a file CONFIG.


.. option:: -v , --verbose

Increase the logging level to DEBUG aka be more verbose about what is happening.


.. py:data:: Application.Description

The :py:data:`Description` attribute is a text that will be displayed in a help text (``--help``).
It is expected that own value will be provided.
The default value is ``""`` (empty string).

