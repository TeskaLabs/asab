# Application

The `asab.Application` class maintains the global application state. You can provide your own implementation by
creating a subclass. There should be only one `Application` object in the process.

!!! example "Creating a new ASAB application:"

	To create a new ASAB application, just create a subclass of `asab.Application` object and use the `run()` method:

	```python title='app.py'
	import asab

	class MyApplication(asab.Application):
		pass

	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	```

	Then run the application from your terminal

	``` shell
	python3 app.py
	```

	and you should see the following output:

	```
	NOTICE asab.application is ready.
	```

	The app will be running until you stop it by `Ctrl+C`.
	
	To create an application that performs some operations and then stops, use the `stop()` method.

	```python title='app_that_terminates.py'
	import asab

	class MyApplication(asab.Application):
		async def main(self):
			print("Hello world!")
			self.stop()

	if __name__ == '__main__':
		app = MyApplication()
		app.run()
	```

	with the output:

	```
	NOTICE asab.application is ready.
	Hello world!
	NOTICE asab.application [sd exit_code="0"] is exiting ...
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
At this time:

- [Configuration](/reference/config/reference) and [command line arguments](#command-line-parser) are loaded and [`asab.Config`](/reference/config/reference/#asab.Config) object is accessed.
- Asynchronous callback `Application.initialize()` is executed.
- [Application housekeeping](/reference/pubsub/reference/#housekeeping) is scheduled.
- [Publish-Subscribe](/reference/pubsub/reference/#well-known-messages) message **Application.init!** is published.


The asynchronous callback `Application.initialize()` is intended to be overridden by an user.
This is where you typically load Modules and register Services, see [Modules and Services](/reference/modules_services/reference) section.

``` python
class MyApplication(asab.Application):
	async def initialize(self):
		# Custom initialization
		from module_sample import Module
		self.add_module(Module)
```

### Run-time

The *run-time* starts after all the modules and services are loaded. This is where the application typically spends the most time.
At this time:

- [Publish-Subscribe](/reference/pubsub/reference/#well-known-messages) message **Application.run!** is published.
- The asynchronous callback `Application.main()` is executed.

The coroutine `Application.main()` is intended to be overwritten by an user.
If `main()` method is completed without calling `stop()`, then the application will run forever.

``` python
class MyApplication(asab.Application):
	async def main(self):
		print("Hello world!")
		self.stop()
```

### Exit-time

The method `Application.stop()` gracefully terminates the *run-time* and commences the *exit-time*.
This method is automatically called by `SIGINT` and `SIGTERM`.
It also includes a response to `Ctrl-C` on UNIX-like system.
When this method is called *exactly three times*, it abruptly exits the application (aka emergency abort).

!!! note
	You need to install `win32api` module to use `Ctrl-C` or an emergency abort properly with ASAB on Windows.
	It is an optional dependency of ASAB.

The parameter `exit_code` allows you to specify the application exit code.

At *exit-time*:

- [Publish-Subscribe](/reference/pubsub/reference/#well-known-messages) message **Application.exit!** is published.
- Asynchronous callback `Application.finalize()` is executed.

`Application.finalize()` is intended to be overridden by an user.
It can be used for storing backup data for the next start of the application, custom operations when terminating services, sending signals to other applications etc.

``` python
class MyApplication(asab.Application):
	async def finalize(self):
		# Custom finalization
		...
```


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
## Reference

::: asab.application.Application