import collections
import copy
import abc
import time


class Metric(abc.ABC):
	def __init__(self):
		self.Storage = None

	def _initialize_storage(self, storage: dict):
		storage.update({
			'type': self.__class__.__name__,
		})
		self.Storage = storage

	def flush(self) -> dict:
		pass



class Gauge(Metric):
	def __init__(self, init_values=None):
		super().__init__()
		self.Init = init_values if init_values is not None else dict()
		self.Values = self.Init.copy()

	def _initialize_storage(self, storage: dict):
		super()._initialize_storage(storage)
		self.Storage["values"] = self.Values

	def set(self, name: str, value):
		self.Values[name] = value


class Counter(Metric):

	def __init__(self, init_values=None):
		super().__init__()
		self.Init = init_values if init_values is not None else dict()

	def _initialize_storage(self, storage: dict):
		super()._initialize_storage(storage)
		self.Storage['values'] = self.Init.copy()
		self.Storage['actuals'] = self.Init.copy()

	def add(self, name, value, init_value=None):
		"""
		:param name: name of the counter
		:param value: value to be added to the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)

		Adds to the counter specified by `name` the `value`.
		If name is not in Counter Values, it will be added to Values.

		"""

		actuals = self.Storage['actuals']
		try:
			actuals[name] += value
		except KeyError as e:
			if init_value is None:
				raise e
			actuals[name] = init_value + value

	def sub(self, name, value, init_value=None):
		"""
		:param name: name of the counter
		:param value: value to be subtracted from the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)

		Subtracts to the counter specified by `name` the `value`.
		If name is not in Counter Values, it will be added to Values.

		"""

		actuals = self.Storage['actuals']
		try:
			actuals[name] -= value
		except KeyError as e:
			if init_value is None:
				raise e
			actuals[name] = init_value - value

	def flush(self):
		if self.Storage["reset"]:
			self.Storage['values'] = self.Storage['actuals'] 
			self.Storage['actuals'] = self.Init.copy()
		else:
			self.Storage['values'] = self.Storage['actuals'].copy()


class EPSCounter(Counter):
	"""
	Event per Second Counter
	Divides all values by delta time
	"""

	def __init__(self, init_values=None, reset: bool = True):
		super().__init__(init_values=init_values)

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
		self.LastCalculatedValues = eps_values
		return eps_values

	def flush(self) -> dict:
		self.Storage["values"] = self._calculate_eps()
		if self.Storage["reset"]:
			self.Values = self.Init.copy()


class DutyCycle(Metric):
	'''
	https://en.wikipedia.org/wiki/Duty_cycle

		now = self.Loop.time()
		d = now - self.LastReadyStateSwitch
		self.LastReadyStateSwitch = now
	'''


	def __init__(self, loop, init_values=None):
		super().__init__()
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
		self.Storage["Values"] = ret


class AggregationCounter(Counter):
	'''
	Sets value aggregated with the last one.
	Takes a function object as the agg argument.
	The aggregation function can take two arguments only.
	Maximum is used as a default aggregation function.
	'''
	def __init__(self, init_values=None, reset: bool = True, agg=max):
		super().__init__(init_values=init_values)
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
	def __init__(self, buckets: list):
		super().__init__()
		_buckets = [float(b) for b in buckets]

		if _buckets != sorted(buckets):
			raise ValueError("Buckets not in sorted order")

		if _buckets and _buckets[-1] != float("inf"):
			_buckets.append(float("inf"))

		if len(_buckets) < 2:
			raise ValueError("Must have at least two buckets")

		self.InitBuckets = collections.OrderedDict((b, dict()) for b in _buckets)
		self.Buckets = copy.deepcopy(self.InitBuckets)
		self.Count = 0
		self.Sum = 0.0

	def flush(self):
		self.Storage["values"] = {
			"buckets": {str(k): v for k, v in self.Buckets.copy().items()},
			"sum": self.Sum,
			"count": self.Count
		}

		if self.Storage["reset"]:
			self.Buckets = copy.deepcopy(self.InitBuckets)
			self.Count = 0
			self.Sum = 0.0

	def set(self, value_name, value):
		for upper_bound in self.Buckets:
			if value <= upper_bound:
				if self.Buckets[upper_bound].get(value_name) is None:
					self.Buckets[upper_bound][value_name] = 1
				else:
					self.Buckets[upper_bound][value_name] += 1
		self.Sum += value
		self.Count += 1
