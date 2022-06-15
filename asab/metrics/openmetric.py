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
	# TODO: resetable counter is gauge - but how do I recognize counter that is not resetable?
	if m.get("type") == "Histogram":
		metric_type = "histogram"
	elif m.get("type") in ["AggregationCounter", "EPScounter"]:
		metric_type = "gauge"
	elif m.get("type") == "Counter" and m.get("reset") is False:
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
		for upperbound, values in metric_record.get("values").get("buckets").items():
			for v_name, value in values.items():
				histogram_labels = labels_dict.copy()
				histogram_labels.update({"le": str(upperbound)})
				if validate_value(value) is False:
					continue
				metric_lines.append(translate_value(name, v_name, value, metric_type, histogram_labels))
		metric_lines.append(translate_value(name + "_count", None, metric_record.get("values").get("count"), metric_type, labels_dict))
		metric_lines.append(translate_value(name + "_sum", None, metric_record.get("values").get("sum"), metric_type, labels_dict))

	else:
		for field in fieldset:
			labels_dict = {validate_format(k): v for k, v in field.get("tags").items()}
			for v_name, value in field.get("values"):
				if validate_value(value) is False:
					continue
				metric_lines.append(translate_value(name, v_name, value, metric_type, labels_dict))

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
	return isinstance(value, (int, float))


def translate_value(name, v_name, value, metric_type, labels_dict):
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
