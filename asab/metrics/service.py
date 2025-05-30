import configparser
import logging
import asyncio
import os

from ..config import Config
from ..abc import Service
from .metrics import (
	Metric, Counter, EPSCounter, Gauge, DutyCycle, AggregationCounter, Histogram,
	CounterWithDynamicTags, AggregationCounterWithDynamicTags, HistogramWithDynamicTags
)
from .storage import Storage


#

L = logging.getLogger(__name__)

#


class MetricsService(Service):

	def __init__(self, app, service_name):

		super().__init__(app, service_name)

		self.Metrics = set()
		self.MetricToNameAndTags = {}
		self.Targets = []
		self.Tags = {
			"host": app.HostName,
			"appclass": app.__class__.__name__,
		}

		# A identified of the host machine (node); added if available at environment variables
		node_id = os.getenv('NODE_ID', None)
		if node_id is not None:
			self.Tags["node_id"] = node_id

		service_id = os.getenv('SERVICE_ID', None)
		if service_id is not None:
			self.Tags["service_id"] = service_id

		# A unique identifier of a microservice; added as an environment variable.
		instance_id = os.getenv('INSTANCE_ID', None)
		if instance_id is not None:
			self.Tags["instance_id"] = instance_id

		site_id = os.getenv('SITE_ID', None)
		if site_id is not None:
			self.Tags["site_id"] = site_id

		self.Storage = Storage()

		app.PubSub.subscribe("Application.tick/60!", self._on_flushing_event)

		if Config.has_option('asab:metrics', 'target'):
			for target in Config.get('asab:metrics', 'target').split():
				target = target.strip()
				try:
					target_type = Config.get('asab:metrics:{}'.format(target), 'type')
				except configparser.NoOptionError:
					# This allows to specify the type of the target by its name
					target_type = target

				if target_type == 'influxdb':
					from .influxdb import InfluxDBTarget
					target = InfluxDBTarget(self, 'asab:metrics:{}'.format(target))

				elif target_type == 'http':
					from .http import HTTPTarget
					target = HTTPTarget(self, 'asab:metrics:{}'.format(target))

				else:
					raise RuntimeError("Unknown target type {}".format(target_type))

				self.Targets.append(target)

		if Config.getboolean('asab:metrics', 'native_metrics'):
			from .native import NativeMetrics
			self._native_svc = NativeMetrics(self.App, self)


	async def finalize(self, app):
		await self._on_flushing_event("finalize!")


	def del_metric(self, metric_obj):
		"""
		This method deletes an existing metric from the service.
		It has similar signature to other "delete" methods within technologies built by TeskaLabs.

		It is up to the user to call flush when needed.
		"""
		metric_name, metric_tags = self.MetricToNameAndTags[metric_obj]
		self.Storage.delete(metric_name, metric_tags)
		self.Metrics.remove(metric_obj)


	async def flush(self):
		await self._on_flushing_event()


	def clear(self):
		self.Metrics.clear()
		self.Storage.clear()

	def _flush_metrics(self):
		now = self.App.time()

		self.App.PubSub.publish("Metrics.flush!")
		for metric in self.Metrics:
			try:
				metric.flush(now)
			except Exception:
				L.exception("Exception during metric.flush()")

		return now

	async def _on_flushing_event(self, event_type=None):
		if len(self.Metrics) == 0:
			return

		now = self._flush_metrics()

		pending = set()
		for target in self.Targets:
			pending.add(
				asyncio.ensure_future(target.process(self.Storage.Metrics, now))
			)

		while len(pending) > 0:
			done, pending = await asyncio.wait(pending, timeout=180.0, return_when=asyncio.ALL_COMPLETED)


	def _add_metric(self, metric: Metric, metric_name: str, tags=None, reset=None, help=None, unit=None):
		# Add global tags
		metric.StaticTags.update(self.Tags)
		metric.App = self.App

		# Add local static tags
		if tags is not None:
			for key, value in tags.items():
				# Check if every key and value is of type string. If not, try to convert it.
				assert isinstance(key, str), "Cannot add metrics tag: key '{}' is not a string.".format(key)
				assert isinstance(value, str), "Cannot add metrics tag for key '{}': value '{}' is not a string.".format(key, value)
			metric.StaticTags.update(tags)


		metric._initialize_storage(
			self.Storage.add(metric_name, tags=metric.StaticTags.copy(), reset=reset, help=help, unit=unit)
		)

		self.MetricToNameAndTags[metric] = (metric_name, metric.StaticTags.copy())
		self.Metrics.add(metric)

	def create_gauge(self, metric_name: str, tags: dict = None, init_values: dict = None, help: str = None, unit: str = None):
		"""
		The `create_gauge` function creates and returns a Gauge metric with specified parameters.

		Args:
			metric_name (str): The name of the metric you want to create.
			tags (dict): Dictionary where the keys represent the tag names and the values represent the tag values. It allows you
				to categorize and filter metrics based on different dimensions or attributes.
			init_values (dict): The `init_values` parameter is used to set the initial value of the gauge
				metric. Provide pairs of value names and their initial values. If not provided, the gauge
				metric will be initialized with a value of 0.
			help (str): The "help" parameter is used to provide a description or explanation of the metric. It
				can be used to provide additional information about what the metric measures or how it should be
				interpreted.
			unit (str): The "unit" parameter is used to specify the unit of measurement for the metric. It
				helps provide context and understanding for the metric being measured. For example, if the metric is
				measuring the temperature, the unit could be "degrees Celsius".

		Returns:
			an instance of the Gauge class.

		Raises:
			AssertionError: `tags` dictionary has to be of type 'str': 'str'.
		"""

		m = Gauge(init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_counter(self, metric_name: str, tags: dict = None, init_values: dict = None, reset: bool = True, help: str = None, unit: str = None, dynamic_tags: bool = False):
		"""
		The function creates a counter metric with optional dynamic tags and adds it to a metric collection.

		Args:
			metric_name (str): The name of the metric you want to create.
			tags (dict): Dictionary where the keys represent the tag names and the values represent the tag values. It allows you
				to categorize and filter metrics based on different dimensions or attributes.
			init_values (dict): The `init_values` parameter is used to set the initial value of the
				metric. Provide pairs of value names and their initial values. If not provided, the
				metric will be initialized with a value of 0.
			reset (bool): The "reset" parameter is a boolean value that determines whether the counter should
				be reset to initial values every 60 seconds. Defaults to True
			help (str): The "help" parameter is used to provide a description or explanation of the metric. It
				can be used to provide additional information about what the metric measures or how it should be
				interpreted.
			unit (str): The "unit" parameter is used to specify the unit of measurement for the metric. It
				helps provide context and understanding for the metric being measured. For example, if the metric is
				measuring the temperature, the unit could be "degrees Celsius".
			dynamic_tags: Boolean flag. If set to True, the counter will be an instance of the
				"CounterWithDynamicTags" class, which allows tags to be added or removed dynamically. Defaults to False

		Returns:
			the created counter object.

		Raises:
			AssertionError: `tags` dictionary has to be of type 'str': 'str'.
		"""
		if dynamic_tags:
			m = CounterWithDynamicTags(init_values=init_values)
		else:
			m = Counter(init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m

	def create_eps_counter(self, metric_name: str, tags: dict = None, init_values: dict = None, reset: bool = True, help: str = None, unit: str = None):
		"""
		The function creates an EPSCounter object, and returns the object.

		Args:
			metric_name (str): The name of the metric you want to create.
			tags (dict): Dictionary where the keys represent the tag names and the values represent the tag values. It allows you
				to categorize and filter metrics based on different dimensions or attributes.
			init_values (dict): The `init_values` parameter is used to set the initial value of the
				metric. Provide pairs of value names and their initial values. If not provided, the
				metric will be initialized with a value of 0.
			reset (bool): The "reset" parameter is a boolean value that determines whether the counter should
				be reset to initial values every 60 seconds. Defaults to True
			help (str): The "help" parameter is used to provide a description or explanation of the metric. It
				can be used to provide additional information about what the metric measures or how it should be
				interpreted.
			unit (str): The "unit" parameter is used to specify the unit of measurement for the metric. It
				helps provide context and understanding for the metric being measured. For example, if the metric is
				measuring the temperature, the unit could be "degrees Celsius".

		Returns:
			an instance of the `EPSCounter` class.

		Raises:
			AssertionError: `tags` dictionary has to be of type 'str': 'str'.
		"""
		m = EPSCounter(init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m

	def create_duty_cycle(self, metric_name: str, tags: dict = None, init_values: dict = None, help: str = None, unit: str = None):
		"""
		The function creates a duty cycle metric and returns the object.

		Args:
			metric_name (str): The name of the metric you want to create.
			tags (dict): Dictionary where the keys represent the tag names and the values represent the tag values. It allows you
				to categorize and filter metrics based on different dimensions or attributes.
			init_values (dict): The `init_values` parameter is used to set the initial value of the
				metric. Provide pairs of value names and their initial values. If not provided, the
				metric will be initialized with a value of 0.
			help (str): The "help" parameter is used to provide a description or explanation of the metric. It
				can be used to provide additional information about what the metric measures or how it should be
				interpreted.
			unit (str): The "unit" parameter is used to specify the unit of measurement for the metric. It
				helps provide context and understanding for the metric being measured. For example, if the metric is
				measuring the temperature, the unit could be "degrees Celsius".

		Returns:
			an instance of the DutyCycle class.

		Raises:
			AssertionError: `tags` dictionary has to be of type 'str': 'str'.
		"""
		m = DutyCycle(self.App, init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, help=help, unit=unit)
		return m

	def create_aggregation_counter(self, metric_name, tags=None, init_values=None, reset: bool = True, aggregator=max, help=None, unit=None, dynamic_tags=False):
		"""
		The function creates a counter metric with optional dynamic tags and adds it to a metric collection.

		Args:
			metric_name (str): The name of the metric you want to create.
			tags (dict): Dictionary where the keys represent the tag names and the values represent the tag values. It allows you
				to categorize and filter metrics based on different dimensions or attributes.
			init_values (dict): The `init_values` parameter is used to set the initial value of the
				metric. Provide pairs of value names and their initial values. If not provided, the
				metric will be initialized with a value of 0.
			reset (bool): The "reset" parameter is a boolean value that determines whether the counter should
				be reset to initial values every 60 seconds. Defaults to True
			help (str): The "help" parameter is used to provide a description or explanation of the metric. It
				can be used to provide additional information about what the metric measures or how it should be
				interpreted.
			unit (str): The "unit" parameter is used to specify the unit of measurement for the metric. It
				helps provide context and understanding for the metric being measured. For example, if the metric is
				measuring the temperature, the unit could be "degrees Celsius".
			dynamic_tags: Boolean flag. If set to True, the counter will be an instance of the
				"AggregationCounterWithDynamicTags" class, which allows tags to be added or removed dynamically. Defaults to False

		Returns:
			the created counter object.

		Raises:
			AssertionError: `tags` dictionary has to be of type 'str': 'str'.
		"""
		if dynamic_tags:
			m = AggregationCounterWithDynamicTags(init_values=init_values, aggregator=aggregator)
		else:
			m = AggregationCounter(init_values=init_values, aggregator=aggregator)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m

	def create_histogram(self, metric_name, buckets: list, tags=None, init_values=None, reset: bool = True, help=None, unit=None, dynamic_tags=False):
		"""
		The function creates a histogram metric.

		Args:
			metric_name (str): The name of the metric you want to create.
			buckets (list): The "buckets" parameter is a list that specifies the boundaries for the histogram
			buckets. Each element in the list represents the upper bound of a bucket. For example, if the list
			is [10, 20, 30], it means that the histogram will have three buckets: one for values less than 10, second for values less than 20, third for values less than 30
			tags (dict): Dictionary where the keys represent the tag names and the values represent the tag values. It allows you
				to categorize and filter metrics based on different dimensions or attributes.
			init_values (dict): The `init_values` parameter is used to set the initial value of the
				metric. Provide pairs of value names and their initial values. If not provided, the
				metric will be initialized with a value of 0.
			reset (bool): The "reset" parameter is a boolean value that determines whether the histogram should
				be reset to initial values every 60 seconds. Defaults to True
			help (str): The "help" parameter is used to provide a description or explanation of the metric. It
				can be used to provide additional information about what the metric measures or how it should be
				interpreted.
			unit (str): The "unit" parameter is used to specify the unit of measurement for the metric. It
				helps provide context and understanding for the metric being measured. For example, if the metric is
				measuring the temperature, the unit could be "degrees Celsius".
			dynamic_tags: Boolean flag. If set to True, the counter will be an instance of the
				"AggregationCounterWithDynamicTags" class, which allows tags to be added or removed dynamically. Defaults to False

		Returns:
			a histogram object

		Raises:
			AssertionError: `tags` dictionary has to be of type 'str': 'str'.
		"""
		if dynamic_tags:
			m = HistogramWithDynamicTags(buckets=buckets, init_values=init_values)
		else:
			m = Histogram(buckets=buckets, init_values=init_values)
		self._add_metric(m, metric_name, tags=tags, reset=reset, help=help, unit=unit)
		return m
