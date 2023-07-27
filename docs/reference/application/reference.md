# Application

The `asab.Application` class maintains the global application state. You can provide your own implementation by
creating a subclass. There should be only one `Application` object in the process.

!!! example "Creating a new asab application:"

    ```python
    import asab

    class MyApplication(asab.Application):
        pass

    if __name__ == '__main__':
        app = MyApplication()
        app.run()
    ```

!!! example "Direct use of `Application` object:"

    ``` python
    import asab

    if __name__ == '__main__':
        app = asab.Application()
        app.run()
    ```


## Application Lifecycle

Runtime of the `Application` object is driven by `asyncio` [event loop](https://docs.python.org/3/library/asyncio-eventloop.html) which runs asynchronous tasks and callbacks, performs network IO operations, and runs subprocesses.

The ASAB is designed around the [Inversion of
control](https://en.wikipedia.org/wiki/Inversion_of_control) principle.
It means that the ASAB is in control of the application lifecycle. The
custom-written code receives the flow from ASAB via callbacks or
handlers. Inversion of control is used to increase modularity of the
code and make it extensible.

The application lifecycle is divided into 3 phases: init-time, run-time
and exit-time.

### Init-time

The init-time happens during `Application` constructor call. 
The Publish-Subscribe message `Application.init!` is published during init-time.
The `Config` is loaded during init-time.

The application object executes asynchronous callback `Application.initialize()`, which can be overridden by an user.

``` python
class MyApplication(asab.Application):
    async def initialize(self):
        # Custom initialization
        from module_sample import Module
        self.add_module(Module)
```

### Run-time

The run-time starts after all the modules and services are loaded. This is where the application spends the most time typically.
The Publish-Subscribe message `Application.run!` is published when run-time begins.

The method returns the value of `Application.ExitCode`.

The application object executes asynchronous callback
`Application.main()`, which can be overridden. If `main()` method is
completed without calling `stop()`, then the application server will run
forever (this is the default behaviour).

``` python
class MyApplication(asab.Application):
    async def main(self):
        print("Hello world!")
        self.stop()
```

The method `Application.stop()` gracefully terminates the run-time and
commence the exit-time. This method is automatically called by `SIGINT`
and `SIGTERM`. It also includes a response to `Ctrl-C` on UNIX-like
system. When this method is called 3x, it abruptly exits the application
(aka emergency abort).

The parameter `exit_code` allows you to specify the application exit
code.

!!! note
    You need to install :py`win32api`
    module to use `Ctrl-C` or an emergency abord properly with ASAB on
    Windows. It is an optional dependency of ASAB.

### Exit-time

The application object executes asynchronous callback
`Application.finalize()`, which can be overridden by an user.

``` python
class MyApplication(asab.Application):
    async def finalize(self):
        # Custom finalization
        ...
```

The Publish-Subscribe message `Application.exit!` is published when exit-time begins.

Set the exit code of the application, see `os.exit()` in the Python
documentation. If `force` is `False`, the exit code will be set only if
the previous value is lower than the new one. If `force` is `True`, the
exit code value is set to a `exit_code` disregarding the previous value.

The actual value of the exit code.

The example of the exit code handling in the `main()` function of the
application.

```python
if __name__ == '__main__':
    app = asab.Application()
    exit_code = app.run()
    sys.exit(exit_code)
```

## Registering modules and services


For more details see `Module` class.

Initialize and add a new module. The `module_class` class will be
instantiated during the method call.

``` python
class MyApplication(asab.Application):
    async def initialize(self):
        from my_module import MyModule
        self.add_module(MyModule)
```

A list of modules that has been added to the application.


Each service is identified by its unique service name. For more details
see `Service` class.

Locate a service by its service name in a registry and return the
`Service` object.

``` python
svc = app.get_service("service_sample")
svc.hello()
```

A dictionary of registered services.

## Command-line parser

Creates an `argparse.ArgumentParser`. This method can be overloaded to
adjust command-line argument parser.

Please refer to Python standard library `argparse` for more details
about function arguments.

The application object calls this method during init-time to process a
command-line arguments. `argparse` is
used to process arguments. You can overload this method to provide your
own implementation of command-line argument parser.

The `Description` attribute is a text
that will be displayed in a help text (`--help`). It is expected that
own value will be provided. The default value is `""` (empty string).

## UTC Time

Return the current \"event loop time\" in seconds since the epoch as a
floating point number. The specific date of the epoch and the handling
of leap seconds is platform dependent. On Windows and most Unix systems,
the epoch is January 1, 1970, 00:00:00 (UTC) and leap seconds are not
counted towards the time in seconds since the epoch. This is commonly
referred to as Unix time.

A call of the `time.time()` function could be expensive. This method
provides a cheaper version of the call that returns a current wall time
in UTC.

---
## Documentation

::: asab.application.Application