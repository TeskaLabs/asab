import asab
import re
import logging


L = logging.getLogger(__name__)


def validate_format(name):
	regex = r"[a-zA-Z:][a-zA-Z0-9_:]*"
	match = re.fullmatch(regex, name)
	if match is None:
		L.warning("Invalid Prometheus format. {} must match the regex [a-zA-Z:][a-zA-Z0-9_:]*".format(name))
		regex_sub = r"[^a-zA-Z0-9_:]"
		name = re.sub(regex_sub, "_", name)
		name = name.lstrip("_0123456789")
		if name.endswith(("total", "created")):
			L.warning("Invalid OpenMetrics format. Name MUST NOT end with total or created.")
	return name


def validate_value(value):
	return isinstance(value, (int, float))


def get_labels(tags):
	labels_str = "{"
	for tag in tags.keys():
		if tag in {"host", "unit", "help"}:
			continue
		else:
			label_name = validate_format(tag)
			label_value = validate_format(tags.get(tag))
			labels_str += '{}="{}",'.format(label_name, label_value)
	labels_str = labels_str.rstrip(",")
	labels_str += "}"
	if len(labels_str) <= 2:
		return None
	else:
		return labels_str


def get_full_name(m_name, v_name, unit):
	name = "_".join([m_name, v_name])
	name = validate_format(name)
	if unit:
		name += "_{}".format(unit)
	return name


def translate_metadata(name, type, unit, help):
	meta_lines = []
	# If a unit is specified it MUST be provided in a UNIT metadata line. In addition, an underscore and the unit MUST be the suffix of the MetricFamily name.
	meta_lines.append("# TYPE {} {}".format(name, type))
	if unit:
		meta_lines.append("# UNIT {} {}".format(name, unit))
	else:
		L.warning("Invalid OpenMetrics format. Please, add 'unit' in 'Tags'.")

	if help:
		meta_lines.append("# HELP {} {}".format(name, help))
	else:
		L.warning("Invalid OpenMetrics format. Please, add 'help' in 'Tags'.")
	metadata = '\n'.join(meta_lines)
	return metadata


def translate_counter(name, labels_str, value, created):
	if labels_str:
		total_line = ("{}{}{} {}".format(name, "_total", labels_str, value))
		created_line = ("{}{}{} {}".format(name, "_created", labels_str, created))
	else:
		total_line = ("{}{} {}".format(name, "_total", value))
		created_line = ("{}{} {}".format(name, "_created", created))
	return '\n'.join([total_line, created_line])


def translate_gauge(name, labels_str, value):
	if labels_str:
		line = ("{}{} {}".format(name, labels_str, value))
	else:
		line = ("{} {}".format(name, value))
	return line


def metric_to_text(metric, type, values=None, created=None):
	metric_lines = []
	m_name = metric.get("Name")
	tags = metric.get("Tags")
	unit = tags.get("unit")
	if unit:
		unit = validate_format(unit)
	help = tags.get("help")
	labels_str = get_labels(tags)
	if type == "counter":
		values_items = values.items()
	if type == "gauge":
		values_items = metric.get("Values").items()
	for v_name, value in values_items:
		if validate_value(value) is False:
			L.warning("Invalid OpenMetrics format. Value must be float or integer. {} omitted.".format(m_name))
			continue
		else:
			name = get_full_name(m_name, v_name, unit)
			metric_lines.append(translate_metadata(name, type, unit, help))
			if type == "counter":
				metric_lines.append(translate_counter(name, labels_str, value, created))
			if type == "gauge":
				metric_lines.append(translate_gauge(name, labels_str, value))

	metric_text = '\n'.join(metric_lines)
	return metric_text


def gauge_to_openmetrics(metrics_service):
	lines = []
	for metrics in metrics_service.Metrics.values():
		if isinstance(metrics, asab.metrics.metrics.Gauge):
			gauge_text = metric_to_text(metrics.rest_get(), "gauge")
			lines.append(gauge_text)
	text = '\n'.join(lines)
	return text


class PrometheusTarget(asab.ConfigObject):

	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name, config)
		self.countertext = ""
		self.MetricsService = svc

	async def process(self, now, mlist):
		counter_lines = []
		for metric, values in mlist:
			if isinstance(metric, asab.metrics.metrics.Counter):
				counter_lines.append(metric_to_text(metric.rest_get(), "counter", values, now))
		self.countertext = '\n'.join(counter_lines)

	def rest_get(self):
		gauge_text = gauge_to_openmetrics(self.MetricsService)
		counter_text = self.countertext
		end = "# EOF\n"
		return '\n'.join([counter_text, gauge_text, end])


# HOW TO FULLFIL OPEMETRICS STANDARD

# ONLY Gauge and Counters are translated into Prometheus. Other Metrics are omitted.
# Metrics MUST have "unit" and "help" Tags
# Help is a string and SHOULD be non-empty. It is used to give a brief description of the MetricFamily for human consumption and SHOULD be short enough to be used as a tooltip.
# Metrics MUST have Lables - also added as items in Tags
# Values MUST be float or integer. Boolean values MUST follow 1==true, 0==false.
# Colons in MetricFamily names are RESERVED to signal that the MetricFamily is the result of a calculation or aggregation of a general purpose monitoring system. MetricFamily names beginning with underscores are RESERVED and MUST NOT be used unless specified by OpenMetric standard. - Anything that is not A-Z, a-z or digit is transformed into "_" and leading "_" is stripped.
# NaN is a number like any other in OpenMetrics, usually resulting from a division by zero such as for a summary quantile if there have been no observations recently. NaN does not have any special meaning in OpenMetrics, and in particular MUST NOT be used as a marker for missing or otherwise bad data.

# Feel free to read more about OpenMetrics standard here: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md
