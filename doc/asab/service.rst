Service
=======

.. py:currentmodule:: asab

.. py:class:: Service(app)

Service objects are registered at the service registry, managed by an application object.
See :any:`Application.Services` for more details.


An example of a typical service class skeleton:

.. code:: python

    class MyService(asab.Service):

        def __init__(self, app, service_name):
            super().__init__(app, service_name)
            ...

        async def initialize(self, app):
            ...


        async def finalize(self, app):
            ...


        def service_method(self):
            ....


This is how a service is created and registered:

.. code:: python

    mysvc = MyService(app, "my_service")


This is how a service is located and used:

.. code:: python

    mysvc = app.get_service("my_service")
    mysvc.service_method()



.. py:data:: Service.Name

The service name.


Service lifecycle
-----------------

.. py:method:: Service.initialize(app)

Called when the service is initialized.
It can be overriden by an user.


.. py:method:: Service.finalize(app)

Called when the service is finalized e.g. during application exit-time.
It can be overriden by an user.
