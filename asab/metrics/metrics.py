import abc

class Metric(abc.ABC):

	def __init__(self, name:str, tags:dict):
		assert(name is not None)
		assert(tags is not None)
		self.Name = name
		self.Tags = tags

	@abc.abstractmethod
	def flush(self) -> dict:
		pass


class Gauge(Metric):


	def __init__(self, name:str, tags:dict, init_values=None):
		super().__init__(name=name, tags=tags)
		self.Init= init_values
		self.Values = self.Init.copy()


	def set(self, name, value):
		self.Values[name] = value


	def flush(self) -> dict:
		return self.Values.copy()


class Counter(Metric):


	def __init__(self, name, tags, init_values=None, reset:bool=True):
		super().__init__(name=name, tags=tags)
		self.Init= init_values
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
