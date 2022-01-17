import asab
import re
import logging


L = logging.getLogger(__name__)


def validate_format(name):
    name = name.lower()
    regex = r"[\WÁ-ž]+"
    subst = "_"
    result = re.sub(regex, subst, name)
    result = result.lstrip("_")
    if result.endswith("total") or result.endswith("created"):
        L.warning("Invalid OpenMetrics format. Name MUST NOT end with total or created.")
        result = result.rstrip("total")
        result = result.rstrip("created")
    return result


def validate_value(value):
    return isinstance(value, [int, float])


def get_labels(tags):
    labels_str = "{"
    for tag in tags.keys():
        if tag == "host" or tag == "unit" or tag == "help":
            continue
        else:
            if tag.startswith("_"):
                tag = tag.lstrip("_")
            labels_str += '{}="{}",'.format(tag, tags.get(tag))
    labels_str = labels_str.rstrip(",")
    labels_str += "}"
    if labels_str == "{}":
        return None
    else:
        return labels_str


def metric_to_text(metric, type):
    metric_lines = []
    m_name = metric.get("Name")
    tags = metric.get("Tags")
    labels_str = get_labels(tags)

    for v_name, value in metric.get("Values").items():
        if validate_value is False:
            L.warning("Invalid OpenMetrics format. Value must be float or integer.")
            continue
        else:
            name = "_".join([m_name, v_name])
            name = validate_format(name)
            # If a unit is specified it MUST be provided in a UNIT metadata line. In addition, an underscore and the unit MUST be the suffix of the MetricFamily name.
            if tags.get("unit"):
                unit = tags.get("unit")
                unit = validate_format(unit)
                name += "_{}".format(unit)
                metric_lines.append("# TYPE {} {}".format(name, type))
                metric_lines.append("# UNIT {} {}".format(name, unit))
            else:
                unit = None
                metric_lines.append("# TYPE {} {}".format(name, type))
                L.warning("Invalid OpenMetrics format. Please, add 'unit' in 'Tags'.")

            if tags.get("help"):
                help = tags.get("help")
                metric_lines.append("# HELP {} {}".format(name, help))
            else:
                L.warning("Invalid OpenMetrics format. Please, add 'help' in 'Tags'.")

            if type == "counter":
                metricpoint = "_total"
            if type == "gauge":
                metricpoint = ""
            if labels_str:
                metric_lines.append("{}{}{} {}".format(name, metricpoint, labels_str, value))
            else:
                metric_lines.append("{}{} {}".format(name, metricpoint, value))
    metric_text = '\n'.join(metric_lines)
    return metric_text


def to_openmetrics(metrics_service):
    lines = []
    for mname, metrics in metrics_service.Metrics.items():
        if isinstance(metrics, asab.metrics.metrics.Counter):
            counter_text = metric_to_text(metrics.rest_get(), type="counter")
            lines.append(counter_text)

        if isinstance(metrics, asab.metrics.metrics.Gauge):
            gauge_text = metric_to_text(metrics.rest_get(), type="gauge")
            lines.append(gauge_text)

    lines.append("# EOF\n")
    text = '\n'.join(lines)
    return text


# HOW TO FULLFIL OPEMETRICS STANDARD

# ONLY Gauge and Counter translated into Prometheus. Other Metrics are omitted.
# Metrics MUST have "unit" and "help" Tags
# Help is a string and SHOULD be non-empty. It is used to give a brief description of the MetricFamily for human consumption and SHOULD be short enough to be used as a tooltip.
# Metrics MUST have Lables - also added as items in Tags
# Values MUST be float or integer. Boolean values MUST follow 1==true, 0==false.
# Label names beginning with underscores are RESERVED and MUST NOT be used.
# Colons in MetricFamily names are RESERVED to signal that the MetricFamily is the result of a calculation or aggregation of a general purpose monitoring system. MetricFamily names beginning with underscores are RESERVED and MUST NOT be used unless specified by this standard. - Basically - anything that is not A-Z, a-z or digit is transformed into "_" and leading "_" is stripped.

# Feel free to learn more about OpenMetrics standard from here: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md
