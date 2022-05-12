from .openmetric import metric_to_text
from .watch import watch_table


class MetricsDataStorage(object):

	def __init__(self):
		self.Tree = dict()


	def get_metric(self, dimension: str):
		data = self.Tree.get(dimension)
		if data is not None:
			return data

	def add_metric(self, dimension, data=dict()):
		self.Tree[dimension] = data


	def get_all(self):
		return [i for i in self.Tree.values()]


	def get_all_in_openmetric(self):
		lines = []
		for data in self.Tree.values():
			if len(data) > 0:
				lines.append(metric_to_text(data))
		lines.append("# EOF\n")
		return "\n".join(lines)


	def get_all_as_table(self, filter):
		metric_records = self.Tree.values()
		return watch_table(metric_records, filter)
