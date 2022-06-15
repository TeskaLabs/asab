import abc
import copy
import time


class Metric(abc.ABC):

	def __init__(self, init_values=None):
		self.Init = init_values
		self.Storage = None
		self.StaticTags = dict()

	def _initialize_storage(self, storage: dict):
		storage.update({
			'type': self.__class__.__name__,
		})
		self.Storage = storage

		if self.Init is not None:
			self.add_field(self.StaticTags.copy())


	def add_field(self, tags, values):
		raise NotImplementedError(":-(")


	def locate_field(self, tags):
		fieldset = self.Storage['fieldset']

		if tags is None:
			if len(fieldset) == 1:
				# This is the most typical flow
				return fieldset[0]

			tags = self.StaticTags
		else:
			tags = tags.copy()
			tags.update(self.StaticTags)

		# Seek for field in the fieldset using tags
		for field in self.Storage['fieldset']:
			if field['tags'] == tags:
				return field

		# Field not found, create a new one
		field = self.add_field(tags)

		return field


	def flush(self, now):
		pass


class Gauge(Metric):

	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": self.Init.copy() if self.Init is not None else dict(),
		}
		self.Storage['fieldset'].append(field)
		return field


	def set(self, name: str, value, tags=None):
		field = self.locate_field(tags)
		field['values'][name] = value


class Counter(Metric):


	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": self.Init.copy() if self.Init is not None else dict(),
			"actuals": self.Init.copy() if self.Init is not None else dict(),
		}
		self.Storage['fieldset'].append(field)
		return field


	def add(self, name, value, tags=None):
		"""
		:param name: name of the counter
		:param value: value to be added to the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)

		Adds to the counter specified by `name` the `value`.
		If name is not in Counter Values, it will be added to Values.

		"""

		field = self.locate_field(tags)
		actuals = field['actuals']
		try:
			actuals[name] += value
		except KeyError:
			actuals[name] = value


	def sub(self, name, value, tags=None):
		"""
		:param name: name of the counter
		:param value: value to be subtracted from the counter
		:param init_value: init value, when the counter `name` is not yet set up (f. e. by init_values in the constructor)

		Subtracts to the counter specified by `name` the `value`.
		If name is not in Counter Values, it will be added to Values.

		"""

		field = self.locate_field(tags)
		actuals = field['actuals']
		try:
			actuals[name] -= value
		except KeyError:
			actuals[name] = -value


	def flush(self, now):
		if self.Storage.get("reset") is True:
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals']
				if self.Init is not None:
					field['actuals'] = self.Init.copy()
				else:
					field['actuals'] = dict()
		else:
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals'].copy()


class EPSCounter(Counter):
	"""
	Event per Second Counter
	Divides all values by delta time
	"""

	def __init__(self, init_values=None):
		super().__init__(init_values=init_values)
		self.LastTime = time.time()


	def flush(self, now):
		delta = now - self.LastTime
		if delta <= 0.0:
			return

		reset = self.Storage.get("reset")

		for field in self.Storage['fieldset']:
			field['values'] = {
				k: v / delta
				for k, v in field['actuals'].items()
			}

			if reset is True:
				if self.Init is not None:
					field['actuals'] = self.Init.copy()
				else:
					field['actuals'] = dict()

				self.LastTime = now


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


	def flush(self, now):
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
		self.Storage["values"] = ret


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

	def set(self, name, value, tags=None):
		field = self.locate_field(tags)
		actuals = field['actuals']
		try:
			actuals[name] = self.Aggregator(value, actuals[name])
		except KeyError:
			actuals[name] = value

	def add(self, name, value, tags=None):
		raise NotImplementedError("Do not use add() method with AggregationCounter. Use set() instead.")

	def sub(self, name, value, tags=None):
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

		self.InitBuckets = {b: dict() for b in _buckets}
		self.Buckets = copy.deepcopy(self.InitBuckets)
		self.Count = 0
		self.Sum = 0.0
		self.Init = {
			"buckets": self.InitBuckets,
			"sum": 0.0,
			"count": 0
		}

	def add_field(self, tags):
		field = {
			"tags": tags,
			"values": copy.deepcopy(self.Init),
			"actuals": copy.deepcopy(self.Init),
		}
		self.Storage['fieldset'].append(field)
		return field

	def flush(self, now):
		if self.Storage.get("reset") is True:
			for field in self.Storage['fieldset']:
				field['values'] = field['actuals']
				if self.Init is not None:
					field['actuals'] = copy.deepcopy(self.Init)
		else:
			for field in self.Storage['fieldset']:
				field['values'] = copy.deepcopy(field['actuals'])

	def set(self, value_name, value, tags=None):
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
