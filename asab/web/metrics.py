
class WebRequestsMetrics(object):
	
	def __init__(self, metrics_svc):
		self.MetricsService = metrics_svc

		self.RequestCounter = self.MetricsService.create_counter(
			"web_requests",
			unit="epm",
			help="Counts requests to asab endpoints as events per minute.",
		)
		self.MaxDurationCounter = self.MetricsService.create_aggregation_counter(
			"web_requests_duration_max",
			help="Counts maximum request duration to asab endpoints per minute.",
			unit="seconds",
			aggregator=max,
		)
		self.MinDurationCounter = self.MetricsService.create_aggregation_counter(
			"web_requests_duration_min",
			help="Counts minimal request duration to asab endpoints per minute.",
			unit="seconds",
			aggregator=min
		)
		self.DurationCounter = self.MetricsService.create_counter(
			"web_requests_duration",
			unit="seconds",
			help="Counts total requests duration to asab endpoints per minute.",
		)
		self.DurationHistogram = self.MetricsService.create_histogram(
			"web_requests_duration_hist",
			buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 1, 5, 10, 50],
			unit="seconds",
			help="Categorizes requests based on their duration.",
		)

	def set_metrics(self, value_name, duration):
		# max
		self.MaxDurationCounter.set(value_name, duration, init_value=0)
		# min
		self.MinDurationCounter.set(value_name, duration, init_value=1000)
		# count
		self.RequestCounter.add(value_name, 1, init_value=0)
		# total duration
		self.DurationCounter.add(value_name, duration, init_value=0)
		# counts in buckets
		self.DurationHistogram.set(value_name, duration)
