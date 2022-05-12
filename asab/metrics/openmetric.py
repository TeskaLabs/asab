import re


def metric_to_text(metric_record):
	metric_lines = []
	m_name = metric_record.get("Name")
	tags = metric_record.get("Tags")
	unit = tags.get("unit")
	if unit:
		unit = validate_format(unit)
	name = get_full_name(m_name, unit)
	help = tags.get("help")
	labels_dict = get_tags_labels(tags)

	metric_lines.append(translate_metadata(name, metric_record.get("Type"), unit, help))

	for i in metric_record.get("Values"):
		metric_type = metric_record.get("Type")
		v_name = i.get("value_name")
		value = i.get("value")
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
		if metric_type == "histogram" and v_name in ("Count", "Sum"):
			labels_str = get_value_labels(labels_dict, None)
			if v_name == "Count":
				name = name + "_count"
			elif v_name == "Sum":
				name = name + "_sum"
		else:
			labels_str = get_value_labels(labels_dict, v_name)

		if metric_type == "counter":
			name = name + "_total"

		return "{}{} {}".format(name, labels_str, value)


def get_value_labels(labels_dict, v_name):
	labels_str = "{"
	if labels_dict != {}:
		for k, v in labels_dict.items():
			labels_str += '{}="{}",'.format(k, v)
	if isinstance(v_name, str):
		labels_str += '{}="{}",'.format("value_name", v_name)
	elif isinstance(v_name, dict):
		for k, v in v_name.items():
			labels_str += '{}="{}",'.format(k, v)
	elif isinstance(v_name, (tuple, list)):
		for i, item in enumerate(v_name):
			labels_str += '{}="{}",'.format("label" + str(i), item)
	labels_str = labels_str.rstrip(",")
	labels_str += "}"
	if len(labels_str) <= 2:
		return None
	return labels_str


# HOW TO FULLFIL OPEMETRICS STANDARD

# Metrics SHOULD have "unit" and "help" Tags
# Help is a string and SHOULD be non-empty. It is used to give a brief description of the MetricFamily for human consumption and SHOULD be short enough to be used as a tooltip.
# Values MUST be float or integer. Boolean values MUST follow 1==true, 0==false.
# Colons in MetricFamily names are RESERVED to signal that the MetricFamily is the result of a calculation or aggregation of a general purpose monitoring system. MetricFamily names beginning with underscores are RESERVED and MUST NOT be used unless specified by OpenMetric standard. - Anything that is not A-Z, a-z or digit is transformed into "_" and leading "_" is stripped.
# NaN is a number like any other in OpenMetrics, usually resulting from a division by zero such as for a summary quantile if there have been no observations recently. NaN does not have any special meaning in OpenMetrics, and in particular MUST NOT be used as a marker for missing or otherwise bad data.

# Feel free to read more about OpenMetrics standard here: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md
