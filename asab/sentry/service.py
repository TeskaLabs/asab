import asab
import sys
import os
import re
import logging
import json

L = logging.getLogger(__name__)


try:
	import sentry_sdk
	import sentry_sdk.integrations.aiohttp
	import sentry_sdk.integrations.asyncio
	import sentry_sdk.integrations.logging
except ModuleNotFoundError:
	L.critical("Package for Sentry SDK not found. Install it with: pip install sentry-sdk")
	sys.exit(1)


class SentryService(asab.Service):
	"""
	Service for Sentry SDK integration.

	Sentry is an error tracking and performance monitoring platform.
	When the service is initialized and `data_source_name` is set,
	all unhandled exceptions, error log messages are sent as Events to sentry.io,
	together with lines of code where the error happened, structured data and values of variables.

	Configuration:
	```ini
	[sentry]
	data_source_name=
	```

	Examples:
	```python
	sentry_svc = app.get_service("SentryService")

	try:
		call_collapsing_function()
	except Exception as e:
		sentry_svc.capture_exception(e)

	sentry_svc.capture_message("User was deleted from database.")
	```

	"""

	def __init__(self, app, service_name: str):
		super().__init__(app, service_name)

		# DATA SOURCE NAME (DSN)
		# format: https://<public key>@o<secret key>.ingest.sentry.io/<project id>
		# DSN is automatically generated when new project is created
		# and can be modified: Settings > Client Keys (DSN) > Key Details
		self.DataSourceName = asab.Config.get("sentry", "data_source_name", fallback="")
		if len(self.DataSourceName) == 0:
			self.DataSourceName = os.getenv("SENTRY_DSN", "")
		if len(self.DataSourceName) == 0:
			L.error("Data source name is not set. Specify it via SENTRY_DSN env variable or in configuration: [sentry] data_source_name.")

		# LOGGING LEVELS
		levels = {
			"debug": logging.DEBUG,
			"info": logging.INFO,
			"notice": asab.LOG_NOTICE,
			"warning": logging.WARNING,
			"error": logging.ERROR,
			"critical": logging.CRITICAL
		}

		self.LoggingBreadCrumbsLevel = levels.get(asab.Config.get("sentry:logging", "breadcrumbs").lower(), "notice")
		self.LoggingEventsLevel = levels.get(asab.Config.get("sentry:logging", "events").lower(), "error")

		# ENVIRONMENT (e.g. "production", "testing", ...)
		self.Environment = asab.Config.get("sentry", "environment")  # default: "develop"

		# RELEASE
		# Release can be obtained from MANIFEST.json if exists
		path = asab.Config.get("general", "manifest")
		if path == "":
			if os.path.isfile("/app/MANIFEST.json"):
				path = "/app/MANIFEST.json"
			elif os.path.isfile("/MANIFEST.json"):
				path = "/MANIFEST.json"
			elif os.path.isfile("MANIFEST.json"):
				path = "MANIFEST.json"

		if len(path) != 0:
			try:
				with open(path) as f:
					manifest = json.load(f)
			except Exception as e:
				L.exception("Error when reading manifest for reason {}".format(e))

		else:
			manifest = None

		if manifest:
			self.Release = manifest.get("version", fallback="not specified")
		else:
			self.Release = "not specified"

		# PERFORMANCE MONITORING
		# traces sample rate: percentage of captured events
		# prevents overcrowding when deployed to production
		# default: 100%
		self.TracesSampleRate = asab.Config.getfloat("sentry", "traces_sample_rate")
		assert 0 <= self.TracesSampleRate <= 1.0, "Traces sample rate must be between 0 and 1."

		sentry_sdk.init(
			dsn=self.DataSourceName,
			integrations=[
				sentry_sdk.integrations.aiohttp.AioHttpIntegration(),
				sentry_sdk.integrations.asyncio.AsyncioIntegration(),
				sentry_sdk.integrations.logging.LoggingIntegration(
					level=self.LoggingBreadCrumbsLevel,
					event_level=self.LoggingEventsLevel,
				),
			],
			traces_sample_rate=self.TracesSampleRate,  # percentage of captured events
			environment=self.Environment,  # e.g. "production", "develop"
			release=self.Release,  # version of the microservice, e.g., v23.40-alpha
			auto_session_tracking=True,  # session info about interaction between user and app
			debug=False,  # ...sends many irrelevant messages
		)
		# TODO: Investigate CA certs, TLS/SSL, Security Tokens, Allowed Domains

		# ADDITIONAL GLOBAL TAGS
		# These tags will be set manually or automatically by Remote Control
		self.NodeId = os.getenv("NODE_ID", None)  # e.g. "lmio-box-testing-1"
		self.ServiceId = os.getenv("SERVICE_ID", None)  # e.g. "lmio-service"
		self.InstanceId = os.getenv("INSTANCE_ID", None)  # e.g. "lmio-service-01"

		if self.NodeId:
			sentry_sdk.set_tag("node_id", self.NodeId)
		if self.ServiceId:
			sentry_sdk.set_tag("service_id", self.ServiceId)
		if self.InstanceId:
			sentry_sdk.set_tag("instance_id", self.InstanceId)


	def capture_exception(self, error=None, scope=None, **scope_args):
		"""
		Capture caught exception and send it to Sentry.

		Args:
			error (str, optional): Error message that will be sent. If not specified, the one currently held in `sys.exc_info()` is sent.

		Examples:
		```python
		try:
			call_collapsing_function()
		except Exception as e:
			sentry_svc.capture_exception(e)
		```
		"""
		return sentry_sdk.capture_exception(error=error, scope=scope, **scope_args)

	def capture_message(self, message, level=None, scope=None, **scope_args):
		"""
		Send textual information to Sentry.

		Args:
			message (str):  Text message that will be sent.
		"""
		return sentry_sdk.capture_message(message=message, level=level, scope=scope, **scope_args)

	def set_tag(self, key: str, value) -> None:
		"""
		Add custom tag to the current scope.

		Tags are key-value string pairs that are both indexed and searchable. They can help you quickly both access related events and view the tag distribution for a set of events.

		Tag is set only for the current scope (function, method, class, module).

		Args:
			key (str): Tag key. Tag keys have a maximum length of 32 characters and can contain only letters (a-zA-Z), numbers (0-9), underscores (_), periods (.), colons (:), and dashes (-).
			value: Tag value. Tag values have a maximum length of 200 characters and they cannot contain the newline (`\\n`) character.
		"""

		# Check key format
		if not (0 < len(key) <= 32):
			L.error("Tag key '{}' is too long.".format(key))
			return

		key_pattern = re.compile("^[a-zA-Z0-9_.:-]+$")
		if key_pattern.match(key) is None:
			L.error("Tag '{}' contains invalid characters.".format(key))
			return

		# Check value format
		if not (0 < len(value) <= 200):
			L.error("Tag value '{}' is too long.".format(value))
			return

		if "\n" in value:
			L.error("Tag value {} contains '\\n' character.")
			return

		return sentry_sdk.set_tag(key, value)

	def set_tags(self, tags_dict: dict) -> None:
		"""
		Add multiple custom tags to the current scope.

		Tags are key-value string pairs that are both indexed and searchable. They can help you quickly both access related events and view the tag distribution for a set of events.

		Tags are set only for the current scope (function, method, class, module).

		Args:
			tags_dict (dict): Dictionary of tag keys and values.
		"""
		for key, value in tags_dict.items():
			self.set_tag(key, value)

	def transaction(self, span_operation: str, span_name: str):
		"""
		Start a new transaction.

		Transactions are used for performance monitoring.

		This method is used as a context manager.

		Args:
			span_operation (str): Displayed span operation name that cannot be filtered, e.g., 'task'.
			span_name (str): Displayed span name that can be filtered.

		Returns:
			Transaction: A context manager that measures time operation of the task inside.

		Examples:
		```python
		with sentry_svc.transaction("speed test", "test sleeping"):
			time.sleep(1.0)
		```
		"""
		return sentry_sdk.start_transaction(op=span_operation, name=span_name)

	def span(self, operation: str, description: str):
		"""
		Create a child span within custom transaction.

		This method is used as a context manager.

		Args:
			operation (str): Displayed span operation name that cannot be filtered, e.g., 'task'.
			description (str): Displayed span name that can be filtered.

		Returns:
			Span: A context manager that measures time operation of the task inside.

		Examples:
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
		"""
		return sentry_sdk.start_span(op=operation, description=description)
