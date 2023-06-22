ASAB Command-line interface
===========================

ASAB-based application provides the command-line interface by default.
Here is an overview of the common command-line arguments.

%TODO: option%
-h , \--help
xxx

Show a help.

Configuration
-------------

%TODO: option%
-c \<CONFIG\>,\--config \<CONFIG\>
xxx

Load configuration file from a file CONFIG.

Logging
-------

%TODO: option%
-v , \--verbose
xxx

Increase the logging level to DEBUG aka be more verbose about what is
happening.

%TODO: option%
-l \<LOG\_FILE\>,\--log-file \<LOG\_FILE\>
xxx

Log to a file LOG\_FILE.

%TODO: option%
-s , \--syslog
xxx

Log to a syslog.

Daemon
------

Python module :py`python-daemon`{.interpreted-text role="mod"} has to be
installed in order to support daemonosation functions.

``` {.bash}
$ pip3 install asab python-daemon
```

%TODO: option%
-d , \--daemonize
xxx

Launch the application in the background aka daemonized.

Daemon-related section of `Config`{.interpreted-text role="any"} file:

    [daemon]
    pidfile=/var/run/myapp.pid
    uid=nobody
    gid=nobody
    working_dir=/tmp

Configuration options `pidfile`, `uid` , `gid` and `working_dir` are
supported.

%TODO: option%
-k , \--kill
xxx

Shutdown the application running in the background (started previously
with `-d` argument).
