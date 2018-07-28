Logging
=======

.. py:currentmodule:: asab

ASAB logging is built on top of a standard Python ``logging`` module.
It means that it logs to ``stderr`` when running on a console and ASAB also provides file and syslog output (both RFC5424 and RFC3164) for background mode of operations.

Log timestamps are captured with sub-second precision (depending on the system capabilities) and displayed including microsecond part.


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

The command-line argument ``-v`` enables verbose logging, respectively sets ``logging.DEBUG`` and ``asyncio`` debuging.

The selected verbose mode is avaiable at ``asab.Config["logging"]["verbose"]`` boolean option.


Logging to file
---------------

The command-line argument ``-l`` on command-line enables logging to file.

It is implemented using ``logging.handlers.RotatingFileHandler`` from a Python standard library.

A configuration section ``[[logging:file]]`` can be used to specify details about desired syslog logging.

Example of the configuration file section:

.. code:: ini

    [[logging:file]]
    path=/var/log/asab.log
    format="%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s",
    datefmt="%%d-%%b-%%Y %%H:%%M:%%S.%%f"

*Note*: Putting non-empty ``path`` option in the configuration file is the equivalent for ``-l`` argument respectively it enables logging to file as well.


Logging to syslog
-----------------

The command-line argument ``-s`` enables logging to syslog.

A configuration section ``[[logging:syslog]]`` can be used to specify details about desired syslog logging.

Example of the configuration file section:

.. code:: ini

	[[logging:syslog]]
	enabled=true
	format=5
	address=tcp://syslog.server.lan:1554/


``enabled`` is equivalent to command-line switch ``-s`` and it enables syslog logging target.

``format`` speficies which logging format will be used.
Possible values are:

- ``5`` for  (new) syslog format (`RFC 5424 <https://tools.ietf.org/html/rfc5424>`_ ) ,
- ``3`` for old BSD syslog format (`RFC 3164 <https://tools.ietf.org/html/rfc3164>`_ ), typically used by ``/dev/log`` and 
- ``m`` for Mac OSX syslog flavour that is based on BSD syslog format but it is not fully compatible.

The default value is ``3`` on Linux and ``m`` on Mac OSX.

``address`` specifies the location of the Syslog server. It could be a UNIX path such as ``/dev/log`` or URL.
Possible URL values:

- ``tcp://syslog.server.lan:1554/`` for Syslog over TCP
- ``udp://syslog.server.lan:1554/`` for Syslog over UDP
- ``unix-connect:///path/to/syslog.socket`` for Syslog over UNIX socket (stream)
- ``unix-sendto:///path/to/syslog.socket`` for Syslog over UNIX socket (datagram), equivalent to ``/path/to/syslog.socket``, used by a ``/dev/log``.

The default value is a ``/dev/log`` on Linux or ``/var/run/syslog`` on Mac OSX.


Structured data
---------------

ASAB supports a structured data to be added to a log entry.
It follows the `RFC 5424 <https://tools.ietf.org/html/rfc5424>`_, section ``STRUCTURED-DATA``.
Structured data are a dictionary, that has to be seriazable to JSON.

.. code:: python

	L.info("Hello world!", struct_data={'key1':'value1', 'key2':2})


Reference
---------

.. automodule:: asab.log
    :members:
    :undoc-members:
    :show-inheritance:
