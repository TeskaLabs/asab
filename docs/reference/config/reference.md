# Configuration

The configuration is provided by `asab.Config` object which is a singleton. 
It means that you can access `asab.Config` from any place of your code, without need of explicit initialization.

```python
import asab

app = asab.Application() #(1)! 

...

my_conf_value = asab.Config['section_name']['key1'] #(2)!
```

1. Initialize application object and hence the configuration.
2. Access configuration values anywhere.


## Based on ConfigParser object

The `asab.Config` is inherited from [the standard `configparser.ConfigParser` class](https://docs.python.org/3/library/configparser.html#customizing-parser-behaviour)
which implements a basic configuration language that provides a structure similar to what's found in Microsoft Windows INI files.

!!! example "Basic usage:"

    Example of the configuration file:

    ``` ini
    [section name]
    key=value
    keys can contain spaces = values can contain spaces

    you can use = equal signs
    as well as: colons
    extra spaces are : removed

    [another section]
    final answer = 42
    are you sure = true

    numerical values are held as: strings
    booleans are also: strings
    use these functions: getint(), getfloat(), getboolean()
    ```

    And this is how you access configuration values:

    ``` python
    >>> asab.Config['section name']['key']
    'value'
    >>> asab.Config.get('another section', 'final answer')
    '42'
    >>> asab.Config.getint('another section', 'final answer')
    42
    >>> asab.Config.getboolean('another section', 'are you sure')
    True
    ```

!!! warning "Be careful with comments:"

    ```ini
    [comments]
    # Comments in empty lines are supported
    key = value # inline comments are not supported!

    # That would prevent URL fragments from being read:
    path = https://www.netlog.org/path#fragment
    ```


!!! example "Multiline configuration entry:"

    A multiline configuration entries are supported:

    ``` ini
    multiline_values = are
        handled just fine as
        long as they are indented
        deeper than the first line
        of a value
    chorus: I'm a lumberjack, and I'm okay
        I sleep all night and I work all day
    ```

## Loading configuration from a file


If a configuration file name is specified,the configuration is automatically
loaded from a configuration file during [initialization time of `Application`](../../application/reference/#init-time).
There are three ways how to include a configuration file:

1. by specifying the `-c` command-line argument:

    ``` shell
    python3 my_app.py -c ./etc/sample.conf
    ```


2. by running the application with `ASAB_CONFIG` environment variable set:

    ``` shell
    export ASAB_CONFIG="./etc/sample.conf"
    python3 my_app.py
    ```

3. by setting the variable during the init-time:

    ```python
    class MyApplication(asab.Application)
        async def initialize(self):
            asab.Config["general"]["config_file"] = "./etc/sample.conf"
    ```




### Including other configuration files

You can specify one or more additional configuration files that are
loaded and merged from an main configuration file. 
It is done by `[general] include` configuration value.

``` ini
[general]
include=./etc/site.conf:./etc/site.d/*.conf
```

Multiple paths are separated by [`os.pathsep`](https://docs.python.org/3/library/os.html?highlight=os%20pathsep#os.pathsep) value, which is `:` on Unix and `;` on Windows.
The path can be specified as a glob (e.g. use of `*` and `?` wildcard characters),
it will be expanded by [`glob` module](https://docs.python.org/3/library/glob.html?highlight=glob#module-glob).
Included configuration files may not exists, this situation is silently ignored.

You can also use a multiline configuration entry:

``` ini
[general]
include=
    ./etc/site.conf
    ./etc/site.d/*.conf
```

## Including ZooKeeper node in the configuration

The separator between includes is newline or space - it means that space MUST NOT be in the names of nodes in the ZooKeeper.

The ZooKeeper node can contain a configuration file in .conf, .json or .yaml format.

You can specify servers and path of the ZooKeeper node directly in the include option:

```ini
[general]
include=zookeeper://localhost:2181/asab/config/config-test.yaml
```

It is also possible to name only the node path in this section and use zookeeper configuration section to read the location of ZooKeeper servers. Using the environment variable `ASAB_ZOOKEEPERS_SERVERS` is also a possible option.

```ini
[general]
include=zookeeper:///asab/config/config-test.yaml
```





## Default values

This is how you can extend configuration default values:

``` python

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

!!! warning

    Only simple types (`string`, `int` and `float`) are allowed in the
    configuration values. Do not use complex types such as lists,
    dictionaries or objects because these are impossible to provide via
    configuration files etc.


## Environment variables

Environment variables found in values are automatically expanded.

```ini
[section_name]
persistent_dir=${HOME}/.myapp/
```

```python
>>> asab.Config['section_name']['persistent_dir']
'/home/user/.myapp/'
```

There is a special environment variable `${THIS_DIR}` that
is expanded to a directory that contains a current configuration file.
It is useful in complex configurations that utilizes included
configuration files etc.

``` {.ini}
[section_name]
my_file=${THIS_DIR}/my_file.txt
```

Another environment variable [${HOSTNAME}]{.title-ref} contains the
application hostname to be used f. e. in logging file path.

``` {.ini}
[section_name]
my_file=${THIS_DIR}/${HOSTNAME}/my_file.txt
```

## Passwords


[passwords] section in the configuration serves to securely store
passwords, which are then not shown publicly in the default API config
endpoint's output.

It is convenient for the user to store passwords at one place, so that
they are not repeated in many sections of the config file(s).

Usage is as follows:

``` {.ini}
[connection:KafkaConnection]
password=${passwords:kafka_password}

[passwords]
kafka_password=<MY_SECRET_PASSWORD>
```

## Obtaining seconds

The seconds can be obtained using [getseconds()]{.title-ref} method for
values with different time units specified in the configuration:

``` {.ini}
[sleep]
sleep_time=5.2s
another_sleep_time=10d
```

The available units are:

> -   `y` ... years
> -   `M` ... months
> -   `w` ... weeks
> -   `d` ... days
> -   `h` ... hours
> -   `m` ... minutes
> -   `s` ... seconds
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
will return the URL. If it's not the same it will raise an error.

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

## Reference

::: asab.config

