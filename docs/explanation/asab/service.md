Service
=======

Service objects are registered at the service registry, managed by an
application object. See `Application.Services`{.interpreted-text
role="any"} for more details.

An example of a typical service class skeleton:

``` {.python}
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
```

This is how a service is created and registered:

``` {.python}
mysvc = MyService(app, "my_service")
```

This is how a service is located and used:

``` {.python}
mysvc = app.get_service("my_service")
mysvc.service_method()
```

Each service is identified by its name.

A reference to an :py`Application`{.interpreted-text role="class"}
object instance.

Lifecycle
---------

Called when the service is initialized. It can be overriden by an user.

Called when the service is finalized e.g. during application exit-time.
It can be overriden by an user.
