import abc


class Metric(abc.ABC):

	def __init__(self, name: str, tags: dict):
		assert(name is not None)
		assert(tags is not None)
		self.Name = name
		self.Tags = tags


	@abc.abstractmethod
	def flush(self) -> dict:
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
		rest['Values'] = self.Values
		return rest


class Counter(Metric):


	def __init__(self, name, tags, init_values=None, reset: bool = True):
		super().__init__(name=name, tags=tags)
		self.Init = init_values
		self.Values = self.Init.copy()
		self.Reset = reset


	def add(self, name, value):
		self.Values[name] += value


	def sub(self, name, value):
		self.Values[name] -= value


	def flush(self) -> dict:
		ret = self.Values
		if self.Reset:
			self.Values = self.Init.copy()
		return ret

	def rest_get(self):
		rest = super().rest_get()
		rest['Values'] = self.Values
		return rest


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
		rest['Values'] = self.Values
		return rest
