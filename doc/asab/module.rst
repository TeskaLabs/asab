Module
======

.. py:currentmodule:: asab

.. py:class:: Module

Modules are registered at the module registry, managed by an application object.
See :any:`Application.Modules` for more details.
Module can be loaded by ASAB and typically provides one or more :any:`Service` objects.


Structure
---------

Recommended structure of the ASAB module::

    mymodule/
        __init__.py
        myservice.py


Content of the `__init__.py`:

.. code:: python

    import asab
    from .myservice import MyService

    # Extend ASAB configuration defaults
    asab.Config.add_defaults({
        'mymodule': {
            'foo': 'bar'
        }
    })

    class MyModule(asab.Module):
        def __init__(self, app):
            super().__init__(app)
            self.service = MyService(app, "MyService")


And this is how the module is loaded:

.. code:: python

    from mymodule import MyModule
    app.add_module(MyModule)

For more details see :any:`Application.add_module`.


Lifecycle
---------

.. py:method:: Module.initialize(app)

Called when the module is initialized.
It can be overriden by an user.


.. py:method:: Module.finalize(app)

Called when the module is finalized e.g. during application exit-time.
It can be overriden by an user.
