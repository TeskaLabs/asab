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

``-v`` switch on command-line sets ``logging.DEBUG`` and ``asyncio`` debuging.


Structured data
---------------

ASAB supports a structured data to be added to a log entry.
It follows the RFC 5424, section ``STRUCTURED-DATA``.
Structured data are a dictionary, that has to be seriazable to JSON.

.. code:: python

	L.info("Hello world!", struct_data={'key1':'value1', 'key2':2})



Reference
---------

.. automodule:: asab.log
    :members:
    :undoc-members:
    :show-inheritance:
