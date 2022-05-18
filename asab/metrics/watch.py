def watch_table(metric_records: list(), filter):
	"""
	Endpoint to list ASAB metrics in the command line.
	Example commands:
	watch curl localhost:8080/asab/v1/metrics_watch
	watch curl localhost:8080/asab/v1/metrics_watch?name=web_requests_duration_max
	"""
	lines = []
	m_name_len = max([len(i.get("Name")) for i in metric_records])
	v_name_len = max(
		[
			len(str(value.get("value_name")))
			for i in metric_records
			for value in i.get("Values")
		]
	)

	separator = "-" * (m_name_len + v_name_len + 30 + 2)
	lines.append(separator)
	lines.append(
		"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
			"Metric name",
			"Value name",
			"Value",
			v_name_len=v_name_len,
			m_name_len=m_name_len,
		)
	)
	lines.append(separator)

	for metric_record in metric_records:
		name = metric_record.get("Name")
		if filter is not None and not name.startswith(filter):
			continue
		for i in metric_record.get("Values"):
			lines.append(
				"{:<{m_name_len}} | {:<{v_name_len}} | {:<30}".format(
					str(name),
					str(i.get("value_name")),
					str(i.get("value")),
					v_name_len=v_name_len,
					m_name_len=m_name_len,
				)
			)

	text = "\n".join(lines)
	return text
