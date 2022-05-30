from .openmetric import metric_to_text
from .watch import watch_table


class MetricsDataStorage(object):

	def __init__(self):
		self.Tree = dict()


	def create_metric_storage(self, dimension: str):
		if dimension in self.Tree:
			raise RuntimeError("Metrics dimension already exists in the data storage")

		data = dict()
		self.Tree[dimension] = data
		return data


	def get_all(self):
		return self.Tree.values()


	def get_all_in_openmetric(self):
		lines = []
		for data in self.Tree.values():
			line = metric_to_text(data)
			if line is not None:
				lines.append(line)
		if lines:
			lines.append("# EOF\n")
			return "\n".join(lines)


	def get_all_as_table(self, filter):
		metric_records = self.Tree.values()
		return watch_table(metric_records, filter)
