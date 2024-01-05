from ..config import Config


class WebRequestsMetrics(object):

	def __init__(self, metrics_svc):
		self.MetricsService = metrics_svc
		# to customize duration histogram, provide bucket upper bound values separated by comma ","
		duration_histogram_buckets = Config.get("asab:metrics", "web_requests_duration_histogram_buckets", fallback=None)
		if duration_histogram_buckets is None:
			duration_histogram_buckets = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50]
		else:
			duration_histogram_buckets = [float(bucket.strip()) for bucket in duration_histogram_buckets.split(",")]

		self.MaxDurationCounter = self.MetricsService.create_aggregation_counter(
			"web_requests_duration_max",
			help="Counts maximum request duration to asab endpoints per minute.",
			unit="seconds",
			aggregator=max,
			dynamic_tags=True,
		)
		self.MinDurationCounter = self.MetricsService.create_aggregation_counter(
			"web_requests_duration_min",
			help="Counts minimal request duration to asab endpoints per minute.",
			unit="seconds",
			aggregator=min,
			dynamic_tags=True,
		)
		self.DurationCounter = self.MetricsService.create_counter(
			"web_requests_duration",
			unit="seconds",
			help="Counts total requests duration to asab endpoints per minute.",
			dynamic_tags=True,
		)
		self.RequestCounter = self.MetricsService.create_counter(
			"web_requests",
			unit="epm",
			help="Counts requests to asab endpoints as events per minute.",
			dynamic_tags=True,
		)
		self.DurationHistogram = self.MetricsService.create_histogram(
			"web_requests_duration_hist",
			buckets=duration_histogram_buckets,
			unit="seconds",
			help="Categorizes requests based on their duration.",
			dynamic_tags=True,
		)


	def set_metrics(self, duration, method, path, status):

		tags = {
			"method": method,
			"path": path,
			"status": str(status)
		}

		# max
		self.MaxDurationCounter.set("duration", duration, tags=tags)
		# min
		self.MinDurationCounter.set("duration", duration, tags=tags)
		# count
		self.RequestCounter.add("count", 1, tags=tags)
		# total duration
		self.DurationCounter.add("duration", duration, tags=tags)
		# counts in buckets
		self.DurationHistogram.set("duration", duration, tags=tags)
