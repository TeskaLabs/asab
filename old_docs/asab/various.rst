Various utility classes
=======================

.. automodule:: asab.abc
    :members:
    :undoc-members:
    :show-inheritance:


Singleton
---------

.. automodule:: asab.abc.singleton
    :members:
    :undoc-members:

Usage:

.. code:: python

    import asab

    class MyClass(metaclass=asab.Singleton):
        ...


Persistent dictionary
---------------------

.. automodule:: asab.pdict
    :members:
    :undoc-members:
    :show-inheritance:


*Note*: A recommended way of initializing the persistent dictionary:

.. code:: python

    PersistentState = asab.PersistentDict("some.file")
    PersistentState.setdefault('foo', 0)
    PersistentState.setdefault('bar', 2)


Timer
-----

.. automodule:: asab.timer
    :members:
    :undoc-members:
    :show-inheritance:


Sockets
-------

.. automodule:: asab.socket
    :members:
    :undoc-members:
    :show-inheritance:
