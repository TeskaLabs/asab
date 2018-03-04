Application
===========

.. py:currentmodule:: asab

The ``Application`` class maintains global application state.
You can provide your own implementation by creating a subclass.
There should be only one ``Application`` object in the process.

Subclassing:

.. code:: python

    import asab

    class MyApplication(asab.Application):
        pass

    if __name__ == "__main__":
        app = MyApplication()
        app.run()


Direct use of ``Application`` object:

.. code:: python

	import asab

	app = asab.Application()
	app.run()


Components
----------

.. py:attribute:: Application.Loop

The event loop that is used by this application.


.. py:attribute:: Application.PubSub

Publish-Subscribe broker.


.. py:attribute:: Application.Metrics

Application Metrics.


.. py:attribute:: Application.Modules

A list of loaded modules.


.. py:attribute:: Application.Services

A dictionary of registered services.



Lifecycle
---------

The application lifecycle is divided into 3 phases: init-time, run-time and exit-time.

Init-time
^^^^^^^^^
The init-time happens during ``Application.__init__()`` call.
The application object executes asynchronous callback ``Application.initialize()``, which can be overriden by an user.
The Publish-Subscribe event ``Application.init!`` is published during init-time.

.. code:: python

    class MyApplication(asab.Application):
        async def initialize(self):
            # Custom initialization
            from module_sample import Module
            self.add_module(Module)


Run-time
^^^^^^^^^
The run-time starts when method  ``Application.run()`` is executed. This is where the application spends the most time typically.
The Publish-Subscribe event ``Application.run!`` is published when run-time begins. Also Publish-Subscribe event ``Application.tick!`` is published periodically during run-time, a tick period is configured by ``[general] tick_period``. The default period is one second.


Exit-time
^^^^^^^^^
The exit-time begins when method  ``Application.stop()`` is executed. 
The Publish-Subscribe event ``Application.exit!`` is published when exit-time begins.
The application object executes asynchronous callback ``Application.finalize()``, which can be overriden by an user.

.. code:: python

    class MyApplication(asab.Application):
        async def finalize(self):
            # Custom finalization
            ...


TODO: Document argparse

.. automodule:: asab.application
    :members:
    :undoc-members:
    :show-inheritance: