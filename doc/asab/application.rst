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


PubSub
------

.. py:attribute:: Application.PubSub

The application-wide publish-Subscribe broker.

For more details, go to :py:class:`asab.PubSub`.

PubSub Events
^^^^^^^^^^^^^

.. option:: Application.init!

TODO: This ...


.. option:: Application.run!

TODO: This ...


.. option:: Application.exit!

TODO: This ...


.. option:: Application.tick!
.. option:: Application.tick/10!
.. option:: Application.tick/60!
.. option:: Application.tick/300!
.. option:: Application.tick/600!
.. option:: Application.tick/1800!
.. option:: Application.tick/3600!
.. option:: Application.tick/43200!
.. option:: Application.tick/86400!

TODO: This ...


Metrics
-------

.. py:attribute:: Application.Metrics

Application Metrics.

For more details, see :py:class:`asab.metrics.Metrics`.


Lifecycle
---------

The application lifecycle is divided into 3 phases: init-time, run-time and exit-time.

Init-time
^^^^^^^^^

.. py:method:: Application.__init__()

The init-time happens during :py:class:`Application` constructor call.
The Publish-Subscribe event :any:`Application.init!` is published during init-time.
The :class:`Config` is loaded during init-time.


.. py:method:: Application.parse_args()

TODO: This..



.. py:method:: Application.initialize()

The application object executes asynchronous callback ``Application.initialize()``, which can be overriden by an user.

.. code:: python

    class MyApplication(asab.Application):
        async def initialize(self):
            # Custom initialization
            from module_sample import Module
            self.add_module(Module)


Run-time
^^^^^^^^^

.. py:method:: Application.run()

Enter a run-time. This is where the application spends the most time typically.
The Publish-Subscribe event :any:`Application.run!` is published when run-time begins.


.. py:method:: Application.main()

The application object executes asynchronous callback ``Application.main()``, which can be overriden.
If ``main()`` method is completed without calling ``stop()``, then the application server will run forever (this is the default behaviour).

.. code:: python

    class MyApplication(asab.Application):
        async def main(self):
            print("Hello world!")
            self.stop()


.. py:method:: Application.stop()

Terminate  ``Application.stop()`` the run-time and commence the exit-time.
This method is automatically called by SIGINT, SIGTERM. It also includes a response to Ctrl-C on UNIX-like system.
When this method is called 3x, it abruptly exits the application (aka emergency abort).


Exit-time
^^^^^^^^^

The Publish-Subscribe event :any:`Application.exit!` is published when exit-time begins.

.. py:method:: Application.finalize()

The application object executes asynchronous callback ``Application.finalize()``, which can be overriden by an user.

.. code:: python

    class MyApplication(asab.Application):
        async def finalize(self):
            # Custom finalization
            ...


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


.. py:method:: Application.register_service(service_name, service)

Add a ``Service`` into a registry using provided ``service_name``.


.. py:attribute:: Application.Services

A dictionary of registered services.
