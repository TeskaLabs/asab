import asab

def get_labels(tags):
    labels_str = "{"
    for tag in tags.keys():
        if tag == "host" or tag == "unit" or tag == "help":
            continue
        else:
            labels_str += '{}="{}",'.format(tag, tags.get(tag))
    labels_str = labels_str.rstrip(",")
    labels_str += "}"
    if labels_str == "{}":
        return None
    else:
        return labels_str



def counter_to_om(counter):
    counter_lines = []
    type = "counter"
    m_name = counter.get("Name")
    tags = counter.get("Tags")
    labels_str = get_labels(tags)
    
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

        if labels_str:
            counter_lines.append("{}_total{} {}".format(name, labels_str, value))
        else:
            counter_lines.append("{}_total {}".format(name, value))
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