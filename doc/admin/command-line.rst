ASAB Command-line interface
===========================

ASAB-based application provides the command-line interface by default.
Here is an overview of the common command-line arguments.


.. option:: -h , --help

Show a help.


Configuration
-------------

.. option:: -c <CONFIG>,--config <CONFIG>

Load configuration file from a file CONFIG.


Logging
-------

.. option:: -v , --verbose

Increase the logging level to DEBUG aka be more verbose about what is happening.


.. option:: -l <LOG_FILE>,--log-file <LOG_FILE>

Log to a file LOG_FILE.


.. option:: -s , --syslog

Log to a syslog.


Daemon
------

Python module :py:mod:`python-daemon` has to be installed in order to support daemonosation functions.

.. code-block:: bash

    $ pip3 install asab python-daemon


.. option:: -d , --daemonize

Launch the application in the background aka daemonized.

Daemon-related section of :any:`Config` file::

    [daemon]
    pidfile=/var/run/myapp.pid
    uid=nobody
    gid=nobody
    working_dir=/tmp

Configuration options ``pidfile``, ``uid`` , ``gid`` and ``working_dir`` are supported.


.. option:: -k , --kill

Shutdown the application running in the background (started previously with ``-d`` argument).
