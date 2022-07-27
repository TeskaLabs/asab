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
    
    L.warning("Hello world!")


Example of the output to the console:

``25-Mar-2018 23:33:58.044595 WARNING myapp.mymodule Hello world!``


Logging Levels
--------------

ASAB uses Python logging levels with the addition of ``LOG_NOTICE`` level.
``LOG_NOTICE`` level is similar to ``logging.INFO`` level but it is visible in even in non-verbose mode.


.. code:: python

    L.log(asab.LOG_NOTICE, "This message will be visible regardless verbose configuration.")


+----------------+---------------+------------------------------+
| Level          | Numeric value | Syslog Severity level        |
+================+===============+==============================+
| ``CRITICAL``   | 50            | Critical / ``crit`` / 2      |
+----------------+---------------+------------------------------+
| ``ERROR``      | 40            | Error / ``err`` / 3          |
+----------------+---------------+------------------------------+
| ``WARNING``    | 30            | Warning / ``warning`` / 4    |
+----------------+---------------+------------------------------+
| ``LOG_NOTICE`` | 25            | Notice / ``notice`` / 5      |
+----------------+---------------+------------------------------+
| ``INFO``       | 20            | Informational / ``info`` / 6 |
+----------------+---------------+------------------------------+
| ``DEBUG``      | 10            | Debug / ``debug`` / 7        |
+----------------+---------------+------------------------------+
| ``NOTSET``     | 0             |                              |
+----------------+---------------+------------------------------+


Verbose mode
------------

The command-line argument ``-v`` enables verbose logging.
It means that log entries with levels ``DEBUG`` and ``INFO`` will be visible.
It also enables ``asyncio`` debug logging.

The actual verbose mode is avaiable at ``asab.Config["logging"]["verbose"]`` boolean option.

.. code:: python

    L.debug("This message will be visible only in verbose mode.")


Structured data
---------------

ASAB supports a structured data to be added to a log entry.
It follows the `RFC 5424 <https://tools.ietf.org/html/rfc5424>`_, section ``STRUCTURED-DATA``.
Structured data are a dictionary, that has to be seriazable to JSON.

.. code:: python

    L.warning("Hello world!", struct_data={'key1':'value1', 'key2':2})


Example of the output to the console:

``25-Mar-2018 23:33:58.044595 WARNING myapp.mymodule [sd key1="value1" key2="2"] Hello world!``


Logging to file
---------------

The command-line argument ``-l`` on command-line enables logging to file.
Also non-empty ``path`` option in the section ``[logging:file]`` of configuration file enables logging to file as well.

Example of the configuration file section:

.. code:: ini

    [logging:file]
    path=/var/log/asab.log
    format="%%(asctime)s %%(levelname)s %%(name)s %%(struct_data)s%%(message)s",
    datefmt="%%d-%%b-%%Y %%H:%%M:%%S.%%f"
    backup_count=3
    rotate_every=1d


When the deployment expects more instances of the same application to be logging into the same file, 
it is recommended, that the variable hostname is used in the file path:

.. code:: ini

    [logging:file]
    path=/var/log/${HOSTNAME}/asab.log

In this way, the applications will log to seperate log files in different folders,
which is an intended behavior, since race conditions may occur when different application instances
log into the same file.

Logging to console
------------------

ASAB will log to the console only if it detects that it runs in the foreground respectively on the terminal using ``os.isatty``
or if the environment variable ``ASABFORCECONSOLE`` is set to ``1``.
This is useful setup for eg. PyCharm.


Log rotation
^^^^^^^^^^^^

ASAB supports a `log rotation <https://en.wikipedia.org/wiki/Log_rotation>`_.
The log rotation is triggered by a UNIX signal ``SIGHUP``, which can be used e.g. to integrate with ``logrotate`` utility.
It is implemented using ``logging.handlers.RotatingFileHandler`` from a Python standard library.
Also, a time-based log rotation can be configured using ``rotate_every`` option.

``backup_count`` specifies a number of old files to be kept prior their removal.
The system will save old log files by appending the extensions ‘.1’, ‘.2’ etc., to the filename.

``rotate_every`` specifies an time interval of a log rotation.
Default value is empty string, which means that the time-based log rotation is disabled.
The interval is specified by an integer value and an unit, e.g. 1d (for 1 day) or 30M (30 minutes).
Known units are `H` for hours, `M` for minutes, `d` for days and `s` for seconds.


Logging to syslog
-----------------

The command-line argument ``-s`` enables logging to syslog.

A configuration section ``[logging:syslog]`` can be used to specify details about desired syslog logging.

Example of the configuration file section:

.. code:: ini

	[logging:syslog]
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


Logging of obsolete features
----------------------------

It proved to be essential to inform operators about features that are going to be obsoleted.
ASAB offers the unified "obsolete" logger.
This logger can indicate that a particular feature is marked as "obsolete" thru logs.
Such a log message can then be "grepped" from logs uniformly.

It is recommended to include `eol` attribute in the `struct_data` of the log with a `YYYY-MM-DD` date/time of the planned obsoletion of the feature.

Hint: We suggest automating the detection of obsolete warnings in logs so that the operations are informed well ahead of the actual removal of the feature. The string to seek in logs is " OBSOLETE ".

Example of the use:

.. code:: python

    asab.LogObsolete.warning("Use of the obsolete function", struct_data={'eol':'2022-31-12'})


Log example:

``21-Jul-2022 14:32:40.983884 WARNING OBSOLETE [eol="2022-31-12"] Use of the obsolete function``


Reference
---------

.. automodule:: asab.log
    :members:
    :undoc-members:
    :show-inheritance:
