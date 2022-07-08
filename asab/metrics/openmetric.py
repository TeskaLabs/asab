import re

# HOW TO FULLFIL OPEMETRICS STANDARD

# Metrics SHOULD have "unit" and "help" Tags
# Help is a string and SHOULD be non-empty. It is used to give a brief description of the MetricFamily for human consumption and SHOULD be short enough to be used as a tooltip.
# Values MUST be float or integer. Boolean values MUST follow 1==true, 0==false.
# Colons in MetricFamily names are RESERVED to signal that the MetricFamily is the result of a calculation or aggregation of a general purpose monitoring system. MetricFamily names beginning with underscores are RESERVED and MUST NOT be used unless specified by OpenMetric standard. - Anything that is not A-Z, a-z or digit is transformed into "_" and leading "_" is stripped.
# NaN is a number like any other in OpenMetrics, usually resulting from a division by zero such as for a summary quantile if there have been no observations recently. NaN does not have any special meaning in OpenMetrics, and in particular MUST NOT be used as a marker for missing or otherwise bad data.

# Feel free to read more about OpenMetrics standard here: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md


def metric_to_openmetric(m):
	metric_lines = []
	if m.get("type") in ["Histogram", "HistogramWithDynamicTags"]:
		metric_type = "histogram"
	elif m.get("type") in ["Counter", "CounterWithDynamicTags", "AggregationCounterWithDynamicTags"] and m.get("reset") is False:
		metric_type = "counter"
	else:
		metric_type = "gauge"
	m_name = m.get("name")
	unit = m.get("unit")
	if unit:
		unit = validate_format(unit)
	name = get_full_name(m_name, unit)
	help = m.get("help")
	fieldset = m.get("fieldset")

	metric_lines.append(translate_metadata(name, metric_type, unit, help))

	if metric_type == "histogram":
		for field in fieldset:
			if m.get("reset") is False:
				values = field.get("actuals")
			else:
				values = field.get("values")

			# SKIP empty fields
			if all([bucket == {} for bucket in values.get("buckets").values()]):
				continue

			for upperbound, bucket in values.get("buckets").items():
				if bucket == {}:
					continue
				for v_name, value in bucket.items():
					histogram_labels = field.get("tags").copy()
					histogram_labels.update({"le": str(upperbound)})
					if validate_value(value) is False:
						continue
					metric_lines.append(translate_value(name, v_name, value, metric_type, histogram_labels))
			metric_lines.append(translate_value(name + "_count", None, values.get("count"), metric_type, field.get("tags")))
			metric_lines.append(translate_value(name + "_sum", None, values.get("sum"), metric_type, field.get("tags")))

	else:
		for field in fieldset:
			if metric_type == "counter":
				values = field.get("actuals")
			elif m.get("type") == "AggregationCounter" and m.get("reset") is False:
				values = field.get("actuals")
			else:
				values = field.get("values")
			for v_name, value in values.items():
				if validate_value(value) is False:
					continue
				metric_lines.append(translate_value(name, v_name, value, metric_type, field.get("tags")))

	metric_text = "\n".join(metric_lines)
	return metric_text


def validate_format(name):
	name = str(name)
	regex = r"[a-zA-Z:][a-zA-Z0-9_:]*"
	match = re.fullmatch(regex, name)
	if match is None:
		regex_sub = r"[^a-zA-Z0-9_:]"
		name = re.sub(regex_sub, "_", name)
		name = name.lstrip("_0123456789")
	return name


def get_full_name(m_name, unit):
	name = validate_format(m_name)
	if unit:
		name += "_{}".format(unit)
	return name


def get_tags_labels(tags):
	labels_dict = {}
	for tag, tag_v in tags.items():
		if tag in {"unit", "help"}:
			continue
		else:
			labels_dict[validate_format(tag)] = tag_v
	return labels_dict


def translate_metadata(name, type, unit, help):
	meta_lines = []
	meta_lines.append("# TYPE {} {}".format(name, type))
	if unit:
		meta_lines.append("# UNIT {} {}".format(name, unit))
	if help:
		meta_lines.append("# HELP {} {}".format(name, help))
	metadata = "\n".join(meta_lines)
	return metadata


def validate_value(value):
	f = isinstance(value, (int, float))
	# isinstance(True, int) => True -> bool is instance of int
	if type(value) is bool:
		f = False
	return f


def translate_value(name, v_name, value, metric_type, labels_dict):
	labels_dict = {validate_format(k): v for k, v in labels_dict.items()}
	labels_str = get_value_labels(v_name, labels_dict)

	if metric_type == "counter":
		name = name + "_total"

	return "{}{} {}".format(name, labels_str, value)


def get_value_labels(v_name, labels_dict):
	if v_name is not None:
		labels_dict.update({"name": v_name})

	labels_str = "{"
	if labels_dict != {}:
		labels_str += ",".join(['{}="{}"'.format(k, v) for k, v in labels_dict.items()])
	labels_str += "}"
	if len(labels_str) <= 2:
		return None
	return labels_str
