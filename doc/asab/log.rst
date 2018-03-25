Logging
=======

.. py:currentmodule:: asab

ASAB configures a standard Python ``logging`` module in a sane way.
It means that: 

1) Output to STDERR
2) Output to syslog (new version)

Note: Microsecond precision


Recommended use
---------------

We recommend to create a logger ``L`` in every module that captures all necessary logging output.
Alternative logging strategies are also supported.

.. code:: python

    import logging
    L = logging.getLogger(__name__)
    
    ...
    
    L.info("Hello world!")


Example of the output to the console:

``25-Mar-2018 23:33:58.044595 INFO myapp.mymodule : Hello world!``

Verbose mode
------------

``-v`` switch -> ``logging.DEBUG`` & asyncio debug.


Structured data
---------------

TODO: ...


Reference
---------

.. automodule:: asab.log
    :members:
    :undoc-members:
    :show-inheritance:
