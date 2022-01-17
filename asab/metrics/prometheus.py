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


def counter_to_om(counter):
    counter_lines = []
    type = "counter"
    m_name = counter.get("Name")
    tags = counter.get("Tags")
    labels_str = get_labels(tags)

    for v_name, value in counter.get("Values").items():
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
                counter_lines.append("# TYPE {} {}".format(name, type))
                counter_lines.append("# UNIT {} {}".format(name, unit))
            else:
                unit = None
                counter_lines.append("# TYPE {} {}".format(name, type))
                L.warning("Invalid OpenMetrics format. Please, add 'unit' in 'Tags'.")

            if tags.get("help"):
                help = tags.get("help")
                counter_lines.append("# HELP {} {}".format(name, help))
            else:
                L.warning("Invalid OpenMetrics format. Please, add 'help' in 'Tags'.")

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


# HOW TO FULLFIL OPEMETRICS STANDARD

# ONLY Gauge and Counter are possible to translate into Prometheus. Other Metrics are omitted. 
# Metrics MUST have "unit" and "help" Tags
# Help is a string and SHOULD be non-empty. It is used to give a brief description of the MetricFamily for human consumption and SHOULD be short enough to be used as a tooltip.
# Metrics MUST have Lables - also added as items in Tags
# Values MUST be float or integer. Boolean values MUST follow 1==true, 0==false.
# Label names beginning with underscores are RESERVED and MUST NOT be used.
# Colons in MetricFamily names are RESERVED to signal that the MetricFamily is the result of a calculation or aggregation of a general purpose monitoring system. MetricFamily names beginning with underscores are RESERVED and MUST NOT be used unless specified by this standard. - Basically - anything that is not A-Z, a-z or digit is transformed into "_" and leading "_" is stripped.

# Feel free to learn more about OpenMetrics standard from here: https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md


# TO DO
# The combined length of the label names and values of an Exemplar's LabelSet MUST NOT exceed 128 UTF-8 characters. Other characters in the text rendering of an exemplar such as ",= are not included in this limit for implementation simplicity and for consistency between the text and proto formats.
# A MetricPoint in a Metric's Counter's Total MAY reset to 0. If present, the corresponding Created time MUST also be set to the timestamp of the reset.
# All exposers SHOULD be able to emit data secured with TLS 1.2 or later.
# UTF-8 MUST be used. Byte order markers (BOMs) MUST NOT be used. As an important reminder for implementers, byte 0 is valid UTF-8 while, for example, byte 255 is not.
# The content type MUST be: application/openmetrics-text; version=1.0.0; charset=utf-8
# NaN is a number like any other in OpenMetrics, usually resulting from a division by zero such as for a summary quantile if there have been no observations recently. NaN does not have any special meaning in OpenMetrics, and in particular MUST NOT be used as a marker for missing or otherwise bad data.
