Configuration {#configuration-ref}
=============

The configuration is provided by :py`Config`{.interpreted-text
role="obj"} object which is a singleton. It means that you can access
:py`Config`{.interpreted-text role="obj"} from any place of your code,
without need of explicit initialisation.

``` {.python}
import asab

# Initialize application object and hence the configuration
app = asab.Application()

# Access configuration values anywhere
my_conf_value = asab.Config['section_name']['key1']
```

Based on ConfigParser
---------------------

The :py`Config`{.interpreted-text role="obj"} is inherited from Python
Standard Library :py`configparser.ConfigParser`{.interpreted-text
role="class"} class. which implements a basic configuration language
which provides a structure similar to what's found in Microsoft Windows
INI files.

Example of the configuration file:

``` {.ini}
[bitbucket.org]
User = hg

[topsecret.server.com]
Port = 50022
ForwardX11 = no
```

And this is how you access configuration values:

``` {.python}
>>> asab.Config['topsecret.server.com']['ForwardX11']
'no'
```

Multiline configuration entry
-----------------------------

A multiline configuration entries are supported. An example:

``` {.ini}
[section]
key=
  line1
  line2
  line3
another_key=foo
```

Automatic load of configuration
-------------------------------

If a configuration file name is specified, the configuration is
automatically loaded from a configuration file during initialiation time
of :py`Application`{.interpreted-text role="class"}. The configuration
file name can be specified by one of `-c` command-line argument (1),
`ASAB_CONFIG` environment variable (2) or config `[general] config_file`
default value (3).

``` {.shell}
./sample_app.py -c ./etc/sample.conf
```

Including other configuration files
-----------------------------------

You can specify one or more additional configuration files that are
loaded and merged from an main configuration file. It is done by
`[general] include` configuration value. Multiple paths are separated by
`os.pathsep` (`:` on Unix). The path can be specified as a glob (e.g.
use of `*` and `?` wildcard characters), it will be expanded by `glob`
module from Python Standard Library. Included configuration files may
not exists, this situation is silently ignored.

``` {.ini}
[general]
include=./etc/site.conf:./etc/site.d/*.conf
```

You can also use a multiline configuration entry:

``` {.ini}
[general]
include=
    ./etc/site.conf
    ./etc/site.d/*.conf
```

Configuration default values
----------------------------

This is how you can extend configuration default values:

``` {.python}
asab.Config.add_defaults(
    {
        'section_name': {
            'key1': 'value',
            'key2': 'another value'
        },
        'other_section': {
            'key3': 'value',
        },
    }
)
```

Only simple types (`string`, `int` and `float`) are allowed in the
configuration values. Don\'t use complex types such as lists,
dictionaries or objects because these are impossible to provide via
configuration files etc.

Environment variables in configration
-------------------------------------

Environment variables found in values are automatically expanded.

``` {.ini}
[section_name]
persistent_dir=${HOME}/.myapp/
```

``` {.python}
>>> asab.Config['section_name']['persistent_dir']
'/home/user/.myapp/'
```

There is a special environment variable [\${THIS\_DIR}]{.title-ref} that
is expanded to a directory that contains a current configuration file.
It is useful in complex configurations that utilizes included
configuration files etc.

``` {.ini}
[section_name]
my_file=${THIS_DIR}/my_file.txt
```

Another environment variable [\${HOSTNAME}]{.title-ref} contains the
application hostname to be used f. e. in logging file path.

``` {.ini}
[section_name]
my_file=${THIS_DIR}/${HOSTNAME}/my_file.txt
```

Passwords in configration
-------------------------

\[passwords\] section in the configuration serves to securely store
passwords, which are then not shown publicly in the default API config
endpoint\'s output.

It is convenient for the user to store passwords at one place, so that
they are not repeated in many sections of the config file(s).

Usage is as follows:

``` {.ini}
[connection:KafkaConnection]
password=${passwords:kafka_password}

[passwords]
kafka_password=<MY_SECRET_PASSWORD>
```

Obtaining seconds
-----------------

The seconds can be obtained using [getseconds()]{.title-ref} method for
values with different time units specified in the configuration:

``` {.ini}
[sleep]
sleep_time=5.2s
another_sleep_time=10d
```

The available units are:

> -   `y` \... years
> -   `M` \... months
> -   `w` \... weeks
> -   `d` \... days
> -   `h` \... hours
> -   `m` \... minutes
> -   `s` \... seconds
> -   `ms` .. miliseconds

If no unit is specified, float of seconds is expected.

The obtainment of the second value in the code can be achieved in two
ways:

``` {.python}
self.SleepTime = asab.Config["sleep"].getseconds("sleep_time")
self.AnotherSleepTime = asab.Config.getseconds("sleep", "another_sleep_time")
```

Obtaining URLs
--------------

A URL can be obtained using a [geturl()]{.title-ref} method that takes
the URL from the config and removes leading and trailing whitespaces and
trailing backslashes.

There is an optional parameter called [scheme]{.title-ref} that can have
any URL scheme like http, https, mongodb etc. Setting it to None, scheme
validation gets bypassed.

Setting the scheme parameter to the same scheme as in the config, it
will return the URL. If it\'s not the same it will raise an error.

There are two ways of obtaining the URL:

``` {.py}
asab.Config["urls"].geturl("teskalabs", scheme="https")
asab.Config.geturl("urls", "github", scheme=None)
```

Example:

``` {.python}
>>> asab.Config["urls"].geturl("teskalabs", scheme="https")
    'https://www.teskalabs.com'
```

For reference this would be the configuration file:

``` {.ini}
[urls]
teskalabs=https://www.teskalabs.com/
github=github.com
```
