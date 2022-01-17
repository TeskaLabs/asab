import asab

		# lines = []
		# lines.append('# TYPE asab_response summary')
		# lines.append('# UNIT asab_response seconds')	

		# for mname, metrics in metrics_service.Metrics.items():
		# 	lines.append(metrics.build_openmetrics_line())

		# lines.append('# EOF')

		# text = '\n'.join(lines)
		# print(request)
		# return aiohttp.web.Response(text=text, content_type='text/plain')

def counter_to_om(counter):
    counter_lines = []
    type = "counter"
    
    m_name = counter.get("Name")
    tags = counter.get("Tags")
    
    labels = {}
    for tag in tags.keys():
        if tag == "host" or tag == "unit" or tag == "help":
            continue
        else:
            labels[tag] = tags.get(tag)
    labels_str = "{"
    for l_name, label in labels.items():
        labels_str += '{}="{}",'.format(l_name, label)
    labels_str = labels_str.rstrip(",")
    labels_str += "}"
    
    for v_name, value in counter.get("Values").items():
        name = "_".join([m_name, v_name])
        # If a unit is specified it MUST be provided in a UNIT metadata line. In addition, an underscore and the unit MUST be the suffix of the MetricFamily name.
        if tags.get("unit"):
            unit = tags.get("unit")
            name += "_{}".format(unit)
            counter_lines.append("# TYPE {} {}".format(name, type))
            counter_lines.append("# UNIT {} {}".format(name, unit))
        else:
            unit = None
            counter_lines.append("# TYPE {} {}".format(name, type))

        if tags.get("help"):
            help = tags.get("help")
            counter_lines.append("# HELP {} {}".format(name, help))

        if labels == {}:
            counter_lines.append("{}_total {}".format(name, value))
        else:
            counter_lines.append("{}_total{} {}".format(name, labels_str, value))
    counter_text = '\n'.join(counter_lines)
    return counter_text


def to_openmetrics(metrics_service):
    lines = []
    for mname, metrics in metrics_service.Metrics.items():
        if isinstance(metrics, asab.metrics.metrics.Counter):
            print("counter!")
            counter_info = metrics.rest_get()
            counter_text = counter_to_om(counter_info)
            lines.append(counter_text)

    lines.append("# EOF\n")
    text = '\n'.join(lines)
    return text