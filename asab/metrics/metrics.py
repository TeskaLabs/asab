import abc
import time
from .openmetric import metric_to_text


class Metric(abc.ABC):
	def __init__(self, name: str, tags: dict):
		assert(name is not None)
		assert(tags is not None)
		self.Name = name
		self.Tags = tags

	@abc.abstractmethod
	def flush(self) -> dict:
		pass

	@abc.abstractmethod
	def get_open_metric(self) -> str:
		pass

	def rest_get(self):
		return {
			'Name': self.Name,
			'Tags': self.Tags,
		}


class Gauge(Metric):
	def __init__(self, name: str, tags: dict, init_values=None):
		super().__init__(name=name, tags=tags)
		self.Init = init_values
		self.Values = self.Init.copy()

	def set(self, name, value):
		self.Values[name] = value

	def flush(self) -> dict:
		return self.Values.copy()

	def rest_get(self):
		rest = super().rest_get()
		rest["Values"] = self.Values
		return rest

	def get_open_metric(self, **kwargs):
		return metric_to_text(self.rest_get(), "gauge")


class Counter(Metric):
	def __init__(self, name, tags, init_values=None, reset: bool = True):
		super().__init__(name=name, tags=tags)
		self.Init = init_values if init_values is not None else dict()
		self.Values = self.Init.copy()
		self.Reset = reset

	def add(self, name, value, init_value=None):
		"""
		Adds to the counter specified by `name` the `value`.
		:param name: name of the counter
		:param value: value to be added to the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)
		If None, KeyError will be raised.
		:return:
		"""

		try:
			self.Values[name] += value
		except KeyError as e:
			if init_value is None:
				raise e
			self.Values[name] = init_value + value

	def sub(self, name, value, init_value=None):
		"""
		Subtracts to the counter specified by `name` the `value`.
		:param name: name of the counter
		:param value: value to be subtracted from the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)
		If None, KeyError will be raised.
		:return:
		"""

		try:
			self.Values[name] -= value
		except KeyError as e:
			if init_value is None:
				raise e
			self.Values[name] = init_value - value

	def flush(self) -> dict:
		ret = self.Values
		if self.Reset:
			self.Values = self.Init.copy()
		return ret

	def rest_get(self):
		rest = super().rest_get()
		rest["Values"] = self.Values
		return rest

	def get_open_metric(self, **kwargs):
		if self.Reset is True:
			return metric_to_text(self.rest_get(), "gauge", kwargs["values"])
		else:
			return metric_to_text(self.rest_get(), "counter")


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

	def _calculate_eps(self):
		eps_values = dict()
		current_time = int(time.time())
		time_difference = max(current_time - self.LastTime, 1)

		for name, value in self.Values.items():
			eps_values[name] = int(value / time_difference)

		self.LastTime = current_time
		return eps_values

	def flush(self) -> dict:
		ret = self._calculate_eps()
		if self.Reset:
			self.Values = self.Init.copy()
		return ret


class DutyCycle(Metric):
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


class ExtremeCounter(Counter):
	# TODO komentář
	def __init__(self, name, tags, init_values=None, reset: bool = True, extreme: str = "max"):
		super().__init__(name=name, tags=tags, init_values=init_values, reset=reset)
		if extreme not in ["max", "min"]:
			raise ValueError("Error during {} ExtremeCounter initialization. Argument 'extreme' must be 'max' or 'min'.".format(name))
		else:
			self.extreme = extreme

	def set(self, name, value, init_value=None):
		try:
			if self.extreme == "max" and value > self.Values[name]:
				self.Values[name] = value
			if self.extreme == "min" and value < self.Values[name]:
				self.Values[name] = value
		except KeyError as e:
			if init_value is None:
				raise e
			self.Values[name] = value

	def add(self, name, value, init_value=None):
		raise NotImplementedError("Do not use add() method with ExtremeCounter. Use set() instead.")

	def sub(self, name, value, init_value=None):
		raise NotImplementedError("Do not use sub() method with ExtremeCounter. Use set() instead.")
