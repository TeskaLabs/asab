Various utility classes
=======================

# TODO: automodule members="" undoc-members="" show-inheritance=""}
asab.abc
xxx

Singleton
---------

# TODO: automodule members="" undoc-members=""}
asab.abc.singleton
xxx

Usage:

``` {.python}
import asab

class MyClass(metaclass=asab.Singleton):
    ...
```

Persistent dictionary
---------------------

# TODO: automodule members="" undoc-members="" show-inheritance=""}
asab.pdict
xxx

*Note*: A recommended way of initializing the persistent dictionary:

``` {.python}
PersistentState = asab.PersistentDict("some.file")
PersistentState.setdefault('foo', 0)
PersistentState.setdefault('bar', 2)
```

Timer
-----

# TODO: automodule members="" undoc-members="" show-inheritance=""}
asab.timer
xxx

Sockets
-------

# TODO: automodule members="" undoc-members="" show-inheritance=""}
asab.socket
xxx
