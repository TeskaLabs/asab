from collections import OrderedDict
import copy
import abc
import time


class Metric(abc.ABC):
	def __init__(self, name: str, tags: dict):
		assert(name is not None)
		assert(tags is not None)
		self.Name = name
		self.Tags = tags
		self.Type = self.__class__.__name__
		self.Storage = None


	def _initialize_storage(self, storage: dict):
		storage.update({
			'Name': self.Name,
			'Tags': self.Tags,
			'Type': self.Type,
		})
		self.Storage = storage


	def flush(self) -> dict:
		pass

	def rest_get(self) -> dict:
		return {
			'Name': self.Name,
			'Tags': self.Tags,
			'Type': self.Type,
		}



class Gauge(Metric):
	def __init__(self, name: str, tags: dict, init_values=None):
		super().__init__(name=name, tags=tags)
		self.Init = init_values if init_values is not None else dict()
		self.Values = self.Init.copy()

	def _initialize_storage(self, storage: dict):
		storage.update({
			"Values": self.Values
		})
		super()._initialize_storage(storage)


	def set(self, name: str, value):
		self.Values[name] = value

	def rest_get(self):
		rest = super().rest_get()
		rest["Values"] = self.Values
		return rest


class Counter(Metric):
	def __init__(self, name, tags, init_values=None, reset: bool = True):
		super().__init__(name=name, tags=tags)
		self.Init = init_values if init_values is not None else dict()
		self.Values = self.Init.copy()
		self.Reset = reset


	def add(self, name, value, init_value=None):
		"""
		:param name: name of the counter
		:param value: value to be added to the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)

		Adds to the counter specified by `name` the `value`.
		If name is not in Counter Values, it will be added to Values.

		"""

		try:
			self.Values[name] += value
		except KeyError as e:
			if init_value is None:
				raise e
			self.Values[name] = init_value + value

	def sub(self, name, value, init_value=None):
		"""
		:param name: name of the counter
		:param value: value to be subtracted from the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)

		Subtracts to the counter specified by `name` the `value`.
		If name is not in Counter Values, it will be added to Values.

		"""

		try:
			self.Values[name] -= value
		except KeyError as e:
			if init_value is None:
				raise e
			self.Values[name] = init_value - value


	def flush(self):
		self.Storage.update({
			"Values": self.Values.copy()
		})
		if self.Reset:
			self.Values = self.Init.copy()


	def rest_get(self):
		rest = super().rest_get()
		rest["Values"] = self.Values.copy()
		return rest


class EPSCounter(Counter):
	"""
	Event per Second Counter
	Divides all values by delta time
	"""

	def __init__(self, name, tags, init_values=None, reset: bool = True):
		super().__init__(name=name, tags=tags, init_values=init_values, reset=reset)

		# Using time library to avoid delay due to long synchronous operations
		# which is important when calculating incoming events per second
		self.LastTime = int(time.time())  # must be in seconds
		self.LastCalculatedValues = dict()

	def _calculate_eps(self):
		eps_values = dict()
		current_time = int(time.time())
		time_difference = max(current_time - self.LastTime, 1)

		for name, value in self.Values.items():
			eps_values[name] = int(value / time_difference)

		self.LastTime = current_time
		return eps_values

	def flush(self) -> dict:
		self.LastCalculatedValues = self._calculate_eps()
		ret = self.rest_get()
		if self.Reset:
			self.Values = self.Init.copy()
		return ret

	def rest_get(self) -> dict:
		rest = {
			'Name': self.Name,
			'Tags': self.Tags,
			"Type": self.Type
		}
		values = list()
		for value_name, value in self.LastCalculatedValues.items():
			value_name = _transform_namedtuple_valuename_to_labelset_dict(value_name)
			values.append({
				"value_name": value_name,
				"value": value,
			})

		rest["Values"] = values

		return rest


class DutyCycle(Metric):
	# TODO: totally unsupported right now!!
	'''
	https://en.wikipedia.org/wiki/Duty_cycle

		now = self.Loop.time()
		d = now - self.LastReadyStateSwitch
		self.LastReadyStateSwitch = now
	'''


	def __init__(self, loop, name: str, tags: dict, init_values=None):
		super().__init__(name=name, tags=tags)
		self.Loop = loop

		now = self.Loop.time()
		self.Values = {k: (v, now, 0.0, 0.0) for k, v in init_values.items()}


	def set(self, name, on_off: bool):
		now = self.Loop.time()
		v = self.Values.get(name)
		if v is None:
			self.Values[name] = (on_off, now, 0.0, 0.0)
			return

		if v[0] == on_off:
			return  # No change

		d = now - v[1]
		off_cycle = v[2]
		on_cycle = v[3]
		if on_off:
			# From off to on
			off_cycle += d
		else:
			# From on to off
			on_cycle += d

		self.Values[name] = (on_off, now, off_cycle, on_cycle)


	def flush(self) -> dict:
		now = self.Loop.time()
		ret = {}
		new_values = {}
		for k, v in self.Values.items():
			d = now - v[1]
			off_cycle = v[2]
			on_cycle = v[3]
			if v[0]:
				on_cycle += d
			else:
				off_cycle += d

			full_cycle = on_cycle + off_cycle
			if full_cycle > 0.0:
				ret[k] = on_cycle / full_cycle

			new_values[k] = (v[0], now, 0.0, 0.0)

		self.Values = new_values
		return ret


	def rest_get(self):
		rest = super().rest_get()
		rest["Values"] = self.Values
		return rest

	def get_open_metric(self, **kwargs):
		return None

	def get_influxdb_format(self, values, now):
		return None


class AggregationCounter(Counter):
	'''
	Sets value aggregated with the last one.
	Takes a function object as the agg argument.
	The aggregation function can take two arguments only.
	Maximum is used as a default aggregation function.
	'''
	def __init__(self, name, tags, init_values=None, reset: bool = True, agg=max):
		super().__init__(name=name, tags=tags, init_values=init_values, reset=reset)
		self.Agg = agg

	def set(self, name, value, init_value=None):
		try:
			self.Values[name] = self.Agg(value, self.Values[name])
		except KeyError as e:
			if init_value is None:
				raise e
			self.Values[name] = self.Agg(value, init_value)

	def add(self, name, value, init_value=None):
		raise NotImplementedError("Do not use add() method with AggregationCounter. Use set() instead.")

	def sub(self, name, value, init_value=None):
		raise NotImplementedError("Do not use sub() method with AggregationCounter. Use set() instead.")


class Histogram(Metric):
	"""
	Creates cumulative histograms.
	"""
	def __init__(self, name, buckets: list, tags, reset=True):
		super().__init__(name=name, tags=tags)
		self.Reset = reset
		_buckets = [float(b) for b in buckets]

		if _buckets != sorted(buckets):
			raise ValueError("Buckets not in sorted order")

		if _buckets and _buckets[-1] != float("inf"):
			_buckets.append(float("inf"))

		if len(_buckets) < 2:
			raise ValueError("Must have at least two buckets")

		self.InitBuckets = OrderedDict((b, dict()) for b in _buckets)
		self.Buckets = copy.deepcopy(self.InitBuckets)
		self.Count = 0
		self.Sum = 0.0
		self.Type = "histogram"

	def flush(self):
		ret = self.rest_get()
		if self.Reset:
			self.Buckets = copy.deepcopy(self.InitBuckets)
			self.Count = 0
			self.Sum = 0.0
		return ret

	def rest_get(self):
		rest = {
			'Name': self.Name,
			'Tags': self.Tags,
			"Type": self.Type
		}
		values = list()
		for upper_bound, metric_point in self.Buckets.items():
			if metric_point == dict():
				continue
			for value_name, value in metric_point.items():
				value_name = self._transform_namedtuple_valuename_to_labelset_dict(value_name, upper_bound)
				values.append({
					"value_name": value_name,
					"value": value,
				})
		rest["Values"] = values
		rest["Values"].append({"value_name": "Sum", "value": self.Sum})
		rest["Values"].append({"value_name": "Count", "value": self.Count})
		rest["Type"] = "histogram"
		return rest

	def _transform_namedtuple_valuename_to_labelset_dict(self, value_name, upper_bound):
		"""
		Makes value names JSON serializable and adds bucket upperbound as "le" label.
		"""
		if isinstance(value_name, tuple):
			try:
				value_name = value_name._asdict()
				value_name["le"] = str(upper_bound)
				return value_name
			except AttributeError:
				pass
		return {"value_name": value_name, "le": str(upper_bound)}

	def set(self, value_name, value):
		for upper_bound in self.Buckets:
			if value <= upper_bound:
				if self.Buckets[upper_bound].get(value_name) is None:
					self.Buckets[upper_bound][value_name] = 1
				else:
					self.Buckets[upper_bound][value_name] += 1
		self.Sum += value
		self.Count += 1




def _transform_namedtuple_valuename_to_labelset_dict(value_name):
	"""
	Makes value names JSON serializable.
	"""
	if isinstance(value_name, tuple):
		try:
			value_name = value_name._asdict()
		except AttributeError:
			# "normal" tuple is JSON serializable as an array
			pass
	return value_name
