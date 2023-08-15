import asab
import sys
import os
import re
import logging

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

		self.DataSourceName = asab.Config.get("sentry", "data_source_name")
		self.Environment = asab.Config.get("sentry", "environment")
		self.TracesSampleRate = asab.Config.getfloat("sentry", "traces_sample_rate")
		self.Release = asab.Config.get("sentry", "release", fallback=None)
		assert 0 <= self.TracesSampleRate <= 1.0, "Traces sample rate must be between 0 and 1."

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

		print("breadcrumbs:", self.LoggingBreadCrumbsLevel)
		print("events:", self.LoggingEventsLevel)

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
			traces_sample_rate=self.TracesSampleRate,
			environment=self.Environment,
			auto_session_tracking=True,  # session info about interaction between user and app
			debug=False,
		)

		# GLOBAL TAGS
		# These tags will be set by Remote Control automatically.
		self.NodeId = os.getenv("NODE_ID", None)
		self.ServiceId = os.getenv("SERVICE_ID", None)
		self.InstanceId = os.getenv("INSTANCE_ID", None)

		if self.NodeId:
			sentry_sdk.set_tag("node_id", self.NodeId)
		if self.ServiceId:
			sentry_sdk.set_tag("service_id", self.ServiceId)
		if self.InstanceId:
			sentry_sdk.set_tag("instance_id", self.InstanceId)


		print(self.NodeId, self.ServiceId, self.InstanceId)


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
			Transaction: A context manager that measures time operation of a task.
		"""
		return sentry_sdk.start_transaction(op=span_operation, name=span_name)
