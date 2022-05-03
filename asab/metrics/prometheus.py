from .openmetric import metric_to_text


class PrometheusTarget(object):
	def __init__(self, svc):
		super().__init__()
		self.MetricsService = svc

	def get_open_metric(self):
		records = []
		for metric_name, metric in self.MetricsService.Metrics.items():
			try:
				if metric.LastRecord is not dict():
					records.append(metric_to_text(metric.LastRecord))
			except AttributeError:
				records.append(metric_to_text(metric.rest_get()))
		records.append("# EOF\n")
		text = "\n".join(records)
		return text
