Module
======

Modules are registered at the module registry, managed by an application
object. See `Application.Modules`{.interpreted-text role="any"} for more
details. Module can be loaded by ASAB and typically provides one or more
`Service`{.interpreted-text role="any"} objects.

Structure
---------

Recommended structure of the ASAB module:

    mymodule/
        __init__.py
        myservice.py

Content of the \`\_\_init\_\_.py\`:

``` {.python}
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
```

And this is how the module is loaded:

``` {.python}
from mymodule import MyModule
app.add_module(MyModule)
```

For more details see `Application.add_module`{.interpreted-text
role="any"}.

Lifecycle
---------

Called when the module is initialized. It can be overriden by an user.

Called when the module is finalized e.g. during application exit-time.
It can be overriden by an user.
