# Sentry Integration

[Sentry.io](https://docs.sentry.io/) is a platform for error-tracking and performance monitoring. [Sentry's Python SDK](https://docs.sentry.io/platforms/python/?original_referrer=https%3A%2F%2Fduckduckgo.com%2F) enables automatic reporting of errors, exceptions and identifies performance issues.

!!! tip
	For the quick start with Sentry.io, you can read [the official documentation](https://docs.sentry.io/product/sentry-basics/?original_referrer=https%3A%2F%2Fduckduckgo.com%2F).

Sentry sends **events** (errors or transactions) to sentry.io together with additional event data (such as timestamps, server names, web browser names, stack traces, etc) and **attachments** (config or log files that are related to an error event). Similar events are grouped into **issues**. Every event has its **fingerprint** that Sentry uses to group events together. You can also add custom **tags** to each event and then filter on them. To create a trail of events that happened prior to an issue, Sentry uses **breadcrumbs**, which are very similar to logs, but can record more rich structured data.

**Transactions** are used for performance monitoring. A transaction represents the operation you want to measure or track, like a page load, page navigation, or asynchronous task. Transaction events are grouped by the transaction name. Moreover, you can monitor child tasks within a single transaction by creating child **spans**.

## Configuration 

When the [Sentry Service](#integration) is integrated to the ASAB microservice, it can be configured to send events to Sentry.io workspace.  

After you create a new project in Sentry.io, [DSN (data source name)](https://docs.sentry.io/product/sentry-basics/dsn-explainer/?original_referrer=https%3A%2F%2Fduckduckgo.com%2F) is generated. You can either set the environment variable or fulfill DSN in the configuration.


=== "DSN in Configuration"
	You can set DSN in the configuration directly:

	```ini title='configuration file'
	[sentry]
	data_source_name=https://<public key>@<secret key>.ingest.sentry.io/<project id>
	```

=== "DSN as environment variable"
	You can provide DSN as environment variable (which is safer, in general) in a `.env` file.

	``` shell title='.env'
	export SENTRY_DSN=https://<public key>@<secret key>.ingest.sentry.io/<project id>
	```

	Then use this variable in `docker-compose.yaml` file.

	```yaml title="docker-compose.yaml"
	my-asab-service:
		image: my.asab.based.microservice
		...
		environment:
		- SENTRY_DSN=${SENTRY_DSN}
	```

	In the configuration file, `[sentry]` section may be empty, but it has to be there.

	```ini title='configuration file'
	[sentry]
	```

Other options available for sentry:

```ini
[sentry]
environment=production_hogwarts  # will be visible as a tag 'environment'

[sentry:logging]
breadcrumbs=info  # logging level for capturing breadcrumbs
events=notice  # logging level for capturing events
```

!!! tip
	If the application is properly containerized, other tags for Sentry.io are created automatically (using Manifest), such as:
	`appclass`, `release`, `server_name`, `service_id`, `instance_id`, `node_id`.

## Integration

Sentry service is dependent on Python `sentry_sdk` library.

```python title='my_app.py'
import asab

class MyApplication(asab.Application):
	def __init__(self):
		super().__init__()
		if "sentry" in asab.Config.sections():
			import asab.sentry as asab_sentry
			self.SentryService = asab_sentry.SentryService(self)
```

After the service is initialized:

- all uncaught exceptions are sent as events
- all logging messages with priority `ERROR` or higher are sent as events, messages with priority `INFO` or higher are sent as breadcrumbs

## Capturing errors

As mentioned above, uncaught exceptions and errors are sent automatically to Sentry.

To capture caught exception and send it as an event, use `capture_exception()` method.

```python
try:
	call_collapsing_function()
except Exception as e:
	sentry_service.capture_exception(e)
```

To capture a custom message and send it as an event, use `capture_message()` method.

```python
if required_variable is None:
	sentry_service.capture_message("required_variable was not set")
```

For grouping issues together and filtering, you can add custom tags. Tags are set only within the current scope (method, class, module).

```python
def my_function():
	sentry_service.set_tag("method", "my_function")
	sentry_service.set_tags({"foo": "bar", "fooz": "buzz"})
```

!!! info
	Tag names and values cannot be arbitrary strings.
	
	Tag keys can have a maximum length of 32 characters and can contain only letters (a-zA-Z), numbers (0-9), underscores (_), periods (.), colons (:), and dashes (-).

	Tag values can have a maximum length of 200 characters and they cannot contain the newline (\n) character.

	If you try to add a tag with invalid format, it won't be set and error message will be displayed.

## Performance monitoring

To create new transaction for performance monitoring, use the context manager `transaction`:

```python
with sentry_service.transaction("speed test", "test sleeping"):
	time.sleep(1.0)
```

To create a child span, use the context manager `span`:

```python
with sentry_svc.transaction("speed test", "multiple tasks"):
	prepare_task1()
	with sentry_svc.span("task", "task1"):
		task1()
	prepare_task2()
	with sentry_svc.span("task", "task2"):
		task2()
	finalize()
```


## Reference

::: asab.sentry.SentryService
