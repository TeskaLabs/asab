import abc
import copy
import time
from .. import Config


class Metric(abc.ABC):

	def __init__(self, init_values=None):
		self.Init = init_values
		self.Storage = None
		self.StaticTags = dict()

		# Expiration is relevant only to WithDynamicTagsMixIn metrics
		self.Expiration = float(Config.get("asab:metrics", "expiration"))

	def _initialize_storage(self, storage: dict):
		assert storage['type'] is None
		storage['type'] = self.__class__.__name__

		self.Storage = storage
		self.add_field(self.StaticTags)

	def add_field(self, tags):
		raise NotImplementedError(":-(")

	def flush(self, now):
		pass


class Gauge(Metric):

	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": self.Init.copy() if self.Init is not None else dict(),
			"measured_at": self.App.time()
		}
		self.Storage['fieldset'].append(field)
		self._field = field
		return field

	def set(self, name: str, value):
		"""
		The function sets a value for a given value name and updates the 'measured_at' field with
		the current time.

		Args:
			name (str): The name of the value to be set.
			value: The value that you want to set for the given name in the field.
		"""
		self._field['values'][name] = value
		self._field['measured_at'] = self.App.time()


class Counter(Metric):

	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": self.Init.copy() if self.Init is not None else dict(),
			"actuals": self.Init.copy() if self.Init is not None else dict(),
			"measured_at": self.App.time()
		}
		self.Storage['fieldset'].append(field)
		self._actuals = field['actuals']
		self._field = field
		return field

	def add(self, name: str, value, init_value: dict = None):
		"""
		The `add` function adds a specified value to a counter, and if the counter does not exist, it
		creates it and initializes it with an optional initial value.
		
		Args:
			name (str): Value name to which the `value` will be added.
			value: Value that needs to be added to the counter. It is the amount by which the counter will be incremented.
			init_value (dict): The `init_value` parameter is an optional parameter that specifies the initial value
				of the counter if it doesn't already exist in the counter values. If `init_value` is provided, it
				will be added to the `value` parameter and the result will be assigned as the value of the counter.
		"""
		try:
			self._actuals[name] += value
		except KeyError:
			if init_value is not None:
				self._actuals[name] = init_value + value
			else:
				self._actuals[name] = value
		if not self.Storage.get("reset"):
			self._field['measured_at'] = self.App.time()

	def sub(self, name: str, value, init_value: dict = None):
		"""
		The function subtracts a value from a variable and updates the 'measured_at' field.

		Args:
			name (str): The name of the variable or field that you want to subtract the value from.
			value: Value that needs to be added to the counter. It is the	amount by which the counter will be incremented.
			init_value (dict): The `init_value` parameter is an optional parameter that specifies the initial value
				of the counter if it doesn't already exist in the counter values. If `init_value` is provided, it
				will be added to the `value` parameter and the result will be assigned as the value of the counter.
		"""

		try:
			self._actuals[name] -= value
		except KeyError:
			if init_value is not None:
				self._actuals[name] = init_value - value
			else:
				self._actuals[name] = -value
		if not self.Storage.get("reset"):
			self._field['measured_at'] = self.App.time()

	def flush(self, now):
		if self.Storage.get("reset") is True:
			self._field['measured_at'] = now
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals']
				if self.Init is not None:
					field['actuals'] = self.Init.copy()
				else:
					field['actuals'] = dict()
				self._actuals = field['actuals']
		else:
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals'].copy()


class EPSCounter(Counter):
	"""
	Event per Second Counter
	Divides the count of event by a time difference between measurements.
	It effectively produces the EPS metric.
	The type of the metric is an integer (int).
	"""

	def __init__(self, init_values=None):
		if init_values is not None:
			init_values = {k: int(v) for k, v in init_values.items()}
		super().__init__(init_values=init_values)
		self.LastTime = time.time()

	def flush(self, now):
		self._field['measured_at'] = now

		delta = now - self.LastTime
		if delta <= 0.0:
			return

		reset = self.Storage.get("reset")

		for field in self.Storage['fieldset']:
			field['values'] = {
				k: int(v / delta)
				for k, v in self._actuals.items()
			}

			if reset is True:
				if self.Init is not None:
					field['actuals'] = self.Init.copy()
				else:
					field['actuals'] = dict()
				self._actuals = field["actuals"]

				self.LastTime = now


class DutyCycle(Metric):
	'''
	https://en.wikipedia.org/wiki/Duty_cycle
	'''


	def __init__(self, app, init_values=None):
		super().__init__()
		self.App = app
		now = self.App.time()
		self.EmptyValue = {
			"on_off": None,
			"timestamp": now,
			"off_cycle": 0.0,
			"on_cycle": 0.0
		}

		self.Init = dict()

		if init_values is not None:
			for k, v in init_values.items():
				value = self.EmptyValue.copy()
				value["on_off"] = v
				self.Init[k] = value

	def add_field(self, tags):
		field = {
			"tags": tags,
			"actuals": self.Init.copy(),
			"values": dict(),
			"measured_at": self.App.time()
		}
		self.Storage['fieldset'].append(field)
		self._field = field
		return field


	def set(self, name: str, on_off: bool):
		"""
		The function `set` updates the state of a variable, tracking the duration of on and off cycles.

		Args:
			name (str): Name of the value that you want to set.
			on_off (bool): The `on_off` parameter is a boolean value that represents whether something is
			turned on. It is used to set the state of a particular item or feature.

		"""
		now = self.App.time()
		values = self._field["actuals"].get(name)
		if values is None:
			value = self.EmptyValue.copy()
			value["on_off"] = on_off
			value["timestamp"] = now
			self._field["actuals"][name] = value
			return

		if values.get("on_off") == on_off:
			return  # No change

		d = now - values.get("timestamp")
		off_cycle = values.get("off_cycle")
		on_cycle = values.get("on_cycle")
		if on_off:
			# From off to on
			off_cycle += d
		else:
			# From on to off
			on_cycle += d

		values["on_off"] = on_off
		values["timestamp"] = now
		values["off_cycle"] = off_cycle
		values["on_cycle"] = on_cycle


	def flush(self, now):
		self._field['measured_at'] = now
		for field in self.Storage["fieldset"]:
			actuals = field.get("actuals")
			for v_name, values in actuals.items():
				d = now - values.get("timestamp")
				off_cycle = values.get("off_cycle")
				on_cycle = values.get("on_cycle")
				if values.get("on_off"):
					on_cycle += d
				else:
					off_cycle += d

			full_cycle = on_cycle + off_cycle
			if full_cycle > 0.0:
				field["values"][v_name] = on_cycle / full_cycle

			new_value = self.EmptyValue.copy()
			new_value["on_off"] = values.get("on_off")
			new_value["timestamp"] = now

			field["actuals"][v_name] = new_value


class AggregationCounter(Counter):
	'''
	Sets value aggregated with the last one.
	Takes a function object as the `aggregator` argument.
	The aggregation function can take two arguments only.
	Maximum is used as a default aggregation function.
	'''
	def __init__(self, init_values=None, aggregator=max):
		super().__init__(init_values=init_values)
		self.Aggregator = aggregator

	def set(self, name, value):
		"""
		The function sets a value in a dictionary, updating it if the key already exists, and also updates a
		'measured_at' field if a certain condition is met.

		Args:
			name: Name of the value being set.
			value: Value that you want to set for the given name.
		"""
		if not self.Storage.get("reset"):
			self._field['measured_at'] = self.App.time()
		try:
			self._actuals[name] = self.Aggregator(value, self._actuals[name])
		except KeyError:
			self._actuals[name] = value

	def add(self, name, value):
		raise NotImplementedError("Do not use add() method with AggregationCounter. Use set() instead.")

	def sub(self, name, value):
		raise NotImplementedError("Do not use sub() method with AggregationCounter. Use set() instead.")


class Histogram(Metric):
	"""
	Creates cumulative histograms.
	"""
	def __init__(self, buckets: list, init_values=None):
		super().__init__(init_values)
		_buckets = [float(b) for b in buckets]

		if _buckets != sorted(buckets):
			raise ValueError("Buckets not in sorted order")

		if _buckets and _buckets[-1] != float("inf"):
			_buckets.append(float("inf"))

		if len(_buckets) < 2:
			raise ValueError("Must have at least two buckets")

		self.InitBuckets = {b: dict() for b in _buckets}
		self.Count = 0
		self.Sum = 0.0
		self.InitHistogram = {
			"buckets": self.InitBuckets,
			"sum": 0.0,
			"count": 0
		}

		if self.Init:
			for value_name, value in self.Init.items():
				for upper_bound in self.InitHistogram["buckets"]:
					if value <= upper_bound:
						self.InitHistogram["buckets"][upper_bound][value_name] = 1
				self.InitHistogram["sum"] += value
				self.InitHistogram["count"] += 1

	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": copy.deepcopy(self.InitHistogram),
			"actuals": copy.deepcopy(self.InitHistogram),
			"measured_at": self.App.time()
		}
		self.Storage['fieldset'].append(field)
		self._actuals = field['actuals']
		self._field = field
		return field

	def flush(self, now):
		if self.Storage.get("reset") is True:
			self._field['measured_at'] = now
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals']
				field['actuals'] = copy.deepcopy(self.InitHistogram)
				self._actuals = field['actuals']
		else:
			for field in self.Storage['fieldset']:
				field['values'] = copy.deepcopy(field['actuals'])

	def set(self, value_name, value):
		"""
		The function updates the values of the histogram based on the input value and value name.

		Args:
			value_name: String that represents the name of the value being set.
			value: Value that needs to be set.
		"""
		if not self.Storage.get("reset"):
			self._field['measured_at'] = self.App.time()
		buckets = self._actuals["buckets"]
		summary = self._actuals["sum"]
		count = self._actuals["count"]
		for upper_bound in buckets:
			if value <= upper_bound:
				if buckets[upper_bound].get(value_name) is None:
					buckets[upper_bound][value_name] = 1
				else:
					buckets[upper_bound][value_name] += 1
		self._actuals["sum"] = summary + value
		self._actuals["count"] = count + 1

###


class MetricWithDynamicTags(Metric):


	def _initialize_storage(self, storage: dict):
		storage.update({
			'type': self.__class__.__name__,
		})
		self.Storage = storage
		if self.Init is not None:
			self.add_field(self.StaticTags.copy())


	def locate_field(self, tags):
		fieldset = self.Storage['fieldset']

		tags = tags.copy()
		tags.update(self.StaticTags)

		# Seek for field in the fieldset using tags
		for field in fieldset:
			if field['tags'] == tags:
				return field

		# Field not found, create a new one
		field = self.add_field(tags)
		return field



class CounterWithDynamicTags(MetricWithDynamicTags):


	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": self.Init.copy() if self.Init is not None else dict(),
			"actuals": self.Init.copy() if self.Init is not None else dict(),
			"expires_at": self.App.time() + self.Expiration,
			"measured_at": self.App.time()
		}
		self.Storage['fieldset'].append(field)
		return field

	def add(self, name, value, tags):
		"""
		The `add` function adds a specified value to a counter, and if the counter does not exist, it
		creates it and initializes it with an optional initial value.

		Args:
			name (str): Value name to which the `value` will be added.
			value: Value that needs to be added to the counter. It is the amount by which the counter will be incremented.
			init_value (dict): The `init_value` parameter is an optional parameter that specifies the initial value
				of the counter if it doesn't already exist in the counter values. If `init_value` is provided, it
				will be added to the `value` parameter and the result will be assigned as the value of the counter.
			tags (dict): Dynamic tags appliying to this value.
		"""

		field = self.locate_field(tags)
		actuals = field['actuals']
		try:
			actuals[name] += value
		except KeyError:
			actuals[name] = value

		if self.Storage.get("reset") is False:
			field['measured_at'] = self.App.time()

		field["expires_at"] = self.App.time() + self.Expiration

	def sub(self, name, value, tags):
		"""
		The function subtracts a value from a variable and updates the 'measured_at' field.

		Args:
			name (str): The name of the variable or field that you want to subtract the value from.
			value: Value that needs to be added to the counter. It is the	amount by which the counter will be incremented.
			init_value (dict): The `init_value` parameter is an optional parameter that specifies the initial value
				of the counter if it doesn't already exist in the counter values. If `init_value` is provided, it
				will be added to the `value` parameter and the result will be assigned as the value of the counter.
			tags (dict): Dynamic tags appliying to this value.
		"""

		field = self.locate_field(tags)
		actuals = field['actuals']
		try:
			actuals[name] -= value
		except KeyError:
			actuals[name] = -value

		if self.Storage.get("reset") is False:
			field['measured_at'] = self.App.time()

		field["expires_at"] = self.App.time() + self.Expiration

	def flush(self, now):
		# Filter expired fields
		for field in self.Storage["fieldset"][::-1]:
			if field["expires_at"] < now:
				self.Storage["fieldset"].remove(field)

		if self.Storage.get("reset") is True:
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals']
				if self.Init is not None:
					field['actuals'] = self.Init.copy()
				else:
					field['actuals'] = dict()
				field['measured_at'] = self.App.time()
		else:
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals'].copy()


class AggregationCounterWithDynamicTags(CounterWithDynamicTags):


	def __init__(self, init_values=None, aggregator=max):
		super().__init__(init_values=init_values)
		self.Aggregator = aggregator

	def set(self, name, value, tags):
		"""
		The function sets a value for a given name and tags in a field, updates the measured_at and
		expires_at timestamps, and handles resetting the field if necessary.

		Args:
			name (str): String that represents the name of the value being set.
			value: Value that you want to set for a specific field.
			tags (dict): Dictionary of tags that are used to locate a specific field.
		"""
		field = self.locate_field(tags)
		actuals = field['actuals']
		try:
			actuals[name] = self.Aggregator(value, actuals[name])
		except KeyError:
			actuals[name] = value

		if self.Storage.get("reset") is False:
			field['measured_at'] = self.App.time()

		field["expires_at"] = self.App.time() + self.Expiration

	def add(self, name, value, tags):
		raise NotImplementedError("Do not use add() method with AggregationCounter. Use set() instead.")

	def sub(self, name, value, tags):
		raise NotImplementedError("Do not use sub() method with AggregationCounter. Use set() instead.")


class HistogramWithDynamicTags(MetricWithDynamicTags):
	"""
	Creates cumulative histograms with dynamic tags
	"""

	def __init__(self, buckets: list, init_values=None):
		super().__init__(init_values)
		_buckets = [float(b) for b in buckets]

		if _buckets != sorted(buckets):
			raise ValueError("Buckets not in sorted order")

		if _buckets and _buckets[-1] != float("inf"):
			_buckets.append(float("inf"))

		if len(_buckets) < 2:
			raise ValueError("Must have at least two buckets")

		self.InitBuckets = {b: dict() for b in _buckets}
		self.Count = 0
		self.Sum = 0.0
		self.InitHistogram = {
			"buckets": self.InitBuckets,
			"sum": 0.0,
			"count": 0
		}

		if self.Init:
			for value_name, value in self.Init.items():
				for upper_bound in self.InitHistogram["buckets"]:
					if value <= upper_bound:
						self.InitHistogram["buckets"][upper_bound][value_name] = 1
				self.InitHistogram["sum"] += value
				self.InitHistogram["count"] += 1

	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": copy.deepcopy(self.InitHistogram),
			"actuals": copy.deepcopy(self.InitHistogram),
			"expires_at": self.App.time() + self.Expiration,
			"measured_at": self.App.time()
		}
		self.Storage['fieldset'].append(field)
		return field

	def flush(self, now):
		# Filter expired fields
		for field in self.Storage["fieldset"][::-1]:
			if field["expires_at"] < now:
				self.Storage["fieldset"].remove(field)

		if self.Storage.get("reset") is True:
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals']
				field['actuals'] = copy.deepcopy(self.InitHistogram)
				field['measured_at'] = self.App.time()
		else:
			for field in self.Storage['fieldset']:
				field['values'] = copy.deepcopy(field['actuals'])

	def set(self, value_name, value, tags: dict):
		"""
		The function updates the values of the histogram based on the input value and value name.

		Args:
			value_name (str): String that represents the name of the value being set.
			value: Value that needs to be set.
			tags (dict): Dynamic tags appliying to this value.
		"""
		field = self.locate_field(tags)
		buckets = field.get("actuals").get("buckets")
		summary = field.get("actuals").get("sum")
		count = field.get("actuals").get("count")
		for upper_bound in buckets:
			if value <= upper_bound:
				if buckets[upper_bound].get(value_name) is None:
					buckets[upper_bound][value_name] = 1
				else:
					buckets[upper_bound][value_name] += 1
		field.get("actuals")["sum"] = summary + value
		field.get("actuals")["count"] = count + 1

		if self.Storage.get("reset") is False:
			field['measured_at'] = self.App.time()

		field["expires_at"] = self.App.time() + self.Expiration
