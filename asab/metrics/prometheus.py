import asab
import re
import logging


L = logging.getLogger(__name__)


class PrometheusTarget(asab.ConfigObject):

	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name, config)
		self.mlist = None

	async def process(self, now, mlist):
		self.now = now
		self.mlist = mlist

	def get_open_metric(self):
		if self.mlist:
			lines = []
			for metric, values in self.mlist:
				kwargs = {"values": values}
				record = metric.get_open_metric(**kwargs)
				if record:
					lines.append(record)
			lines.append("# EOF\n")
			text = '\n'.join(lines)
			return text


class OpenMetric:
	def __init__(self):
		self.Metric = None


	def validate_format(self, name):
		name = str(name)
		regex = r"[a-zA-Z:][a-zA-Z0-9_:]*"
		match = re.fullmatch(regex, name)
		if match is None:
			regex_sub = r"[^a-zA-Z0-9_:]"
			name = re.sub(regex_sub, "_", name)
			name = name.lstrip("_0123456789")
		if name.endswith(("total", "created")):
			pass
			# L.warning("Invalid OpenMetrics format in {}. Name MUST NOT end with total or created.".format(self.Metric.get("Name")))
		return name


	def validate_value(self, value):
		return isinstance(value, (int, float))


	def get_tags_labels(self, tags):
		labels_dict = {}
		for tag, tag_v in tags.items():
			if tag in {"host", "unit", "help"}:
				continue
			else:
				labels_dict[self.validate_format(tag)] = tag_v
		return labels_dict


	def get_value_labels(self, labels_dict, v_name):
		labels_str = "{"
		if labels_dict != {}:
			for k, v in labels_dict.items():
					labels_str += '{}="{}",'.format(k, v)
		regex = r"(\w+=['\"][\w\/]+['\"])"
		capturing_groups = re.findall(regex, v_name)
		if capturing_groups != []:
			for group in capturing_groups:
				label_lst = group.split("=")
				k = self.validate_format(label_lst[0])
				v = label_lst[1].strip("'")
				v = v.strip('"')
				labels_str += '{}="{}",'.format(k, v)
		else:
			labels_str += 'value_name="{}",'.format(v_name)

		labels_str = labels_str.rstrip(",")
		labels_str += "}"
		if len(labels_str) <= 2:
			return None
		else:
			return labels_str


	def get_full_name(self, m_name, unit):
		name = self.validate_format(m_name)
		if unit:
			name += "_{}".format(unit)
		return name


	def translate_metadata(self, name, type, unit, help):
		meta_lines = []
		meta_lines.append("# TYPE {} {}".format(name, type))
		if unit:
			meta_lines.append("# UNIT {} {}".format(name, unit))
		else:
			# L.warning("Invalid OpenMetrics format in {} {}. Please, add 'unit' in 'Tags'.".format(name, type))

		if help:
			meta_lines.append("# HELP {} {}".format(name, help))
		else:
			# L.warning("Invalid OpenMetrics format in {} {}. Please, add 'help' in 'Tags'.".format(name, type))
		metadata = '\n'.join(meta_lines)
		return metadata


	def translate_metric(self, type, name, labels_str, value):
		if type == "counter":
			line = ("{}{}{} {}".format(name, "_total", labels_str, value))
		if type == "gauge":
			line = ("{}{} {}".format(name, labels_str, value))
		return line


	def metric_to_text(self, metric, type, values=None):
		self.Metric = metric
		metric_lines = []
		m_name = metric.get("Name")
		tags = metric.get("Tags")
		unit = tags.get("unit")
		if unit:
			unit = self.validate_format(unit)
		name = self.get_full_name(m_name, unit)
		help = tags.get("help")
		labels_dict = self.get_tags_labels(tags)
		if values:
			values_items = values.items()
		else:
			values_items = metric.get("Values").items()
		metric_lines.append(self.translate_metadata(name, type, unit, help))
		for v_name, value in values_items:
			if self.validate_value(value) is False:
				# L.warning("Invalid OpenMetrics format in {} {}. Value must be float or integer. {} omitted.".format(m_name, type, v_name))
				continue
			else:
				labels_str = self.get_value_labels(labels_dict, str(v_name))
				metric_lines.append(self.translate_metric(type, name, labels_str, value))

		metric_text = '\n'.join(metric_lines)
		return metric_text


# HOW TO FULLFIL OPEMETRICS STANDARD

# ONLY Gauge and Counters are translated into Prometheus. Other Metrics are omitted.
# Metrics MUST have "unit" and "help" Tags
# Help is a string and SHOULD be non-empty. It is used to give a brief description of the MetricFamily for human consumption and SHOULD be short enough to be used as a tooltip.
# Values MUST be float or integer. Boolean values MUST follow 1==true, 0==false.
# Colons in MetricFamily names are RESERVED to signal that the MetricFamily is the result of a calculation or aggregation of a general purpose monitoring system. MetricFamily names beginning with underscores are RESERVED and MUST NOT be used unless specified by OpenMetric standard. - Anything that is not A-Z, a-z or digit is transformed into "_" and leading "_" is stripped.
# NaN is a number like any other in OpenMetrics, usually resulting from a division by zero such as for a summary quantile if there have been no observations recently. NaN does not have any special meaning in OpenMetrics, and in particular MUST NOT be used as a marker for missing or otherwise bad data.

# Feel free to read more about OpenMetrics standard here: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md
