import logging
import aiohttp
import urllib
import http.client

import asab

#

L = logging.getLogger(__name__)


#


class InfluxDBTarget(asab.ConfigObject):
	"""
InfluxDB 2.0 API parameters:
	url - [required] url string of your influxDB
	bucket - [required] the destination bucket for writes
	org - [required] the parameter value specifies the destination organization for writes
	orgid - [optional] the parameter value specifies the ID of the destination organization for writes
	NOTE: If both orgID and org are specified, org takes precedence
	token - [required] API token to authenticate to the InfluxDB
	Example:
	[asab:metrics:influxdb]
	url=http://localhost:8086
	bucket=test
	org=test
	orgid=test
	token=your_token

InfluxDB <1.8 API parameters:
	url - [required] url string of your influxDB
	username - [required] name of influxDB user
	password - [required] password of influxDB user
	Example:
	[asab:metrics:influxdb]
	url=http://localhost:8086
	username=test
	password=testtest
	db=test
	"""

	ConfigDefaults = {
		'url': 'http://localhost:8086/',
		'db': 'mydb',
		'username': '',
		'password': '',
		'proactor': True,  # Use ProactorService to send metrics on thread
	}


	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name=config_section_name, config=config)
		self.Headers = {}
		self.BaseURL = self.Config.get('url').rstrip('/')
		self.WriteRequest = '/write?db={}'.format(self.Config.get('db'))

		username = self.Config.get('username')
		if username is not None and len(username) > 0:
			self.WriteRequest += '&u={}'.format(urllib.parse.quote(username, safe=''))

		password = self.Config.get('password')
		if password is not None and len(password) > 0:
			self.WriteRequest += '&p={}'.format(urllib.parse.quote(password, safe=''))

		# If org is specified we are buildig write request for InfluxDB 2.0 API
		org = self.Config.get('org')
		if org is not None:
			self.WriteRequest = '/api/v2/write?org={}'.format(org)

		bucket = self.Config.get('bucket')
		if bucket is not None:
			self.WriteRequest += '&bucket={}'.format(bucket)

		orgid = self.Config.get('orgid')
		if orgid is not None:
			self.WriteRequest += '&orgID={}'.format(orgid)

		token = self.Config.get('token')
		if token is not None:
			self.Headers = {'Authorization': 'Token {}'.format(token)}

		self.WriteURL = "{}{}".format(self.BaseURL, self.WriteRequest)

		# Proactor service is used for alternative delivery of the metrics into the InfluxDB
		# It is handly when a main loop can become very busy

		if self.Config.getboolean('proactor'):
			try:
				from ..proactor import Module

				svc.App.add_module(Module)

				self.ProactorService = svc.App.get_service('asab.ProactorService')

			except KeyError:
				self.ProactorService = None
		else:
			self.ProactorService = None


	async def process(self, m_tree, now):
		rb = influxdb_format(m_tree, now)

		if self.ProactorService is not None:
			await self.ProactorService.execute(self._worker_upload, m_tree, rb)

		else:
			try:
				async with aiohttp.ClientSession(headers=self.Headers) as session:
					async with session.post(self.WriteURL, data=rb) as resp:
						response = await resp.text()
						if resp.status != 204:
							L.warning("Error when sending metrics to Influx: {}\n{}".format(resp.status, response))
			except aiohttp.client_exceptions.ClientConnectorError:
				L.error("Failed to connect to InfluxDB at {}".format(self.BaseURL))


	def _worker_upload(self, m_tree, rb):
		if self.BaseURL.startswith("https://"):
			conn = http.client.HTTPSConnection(self.BaseURL.replace("https://", ""))
		else:
			conn = http.client.HTTPConnection(self.BaseURL.replace("http://", ""))

		try:
			conn.request("POST", self.WriteRequest, rb, self.Headers)
		except ConnectionRefusedError:
			L.error("Failed to connect to InfluxDB at {}".format(self.BaseURL))
			return

		response = conn.getresponse()
		if response.status != 204:
			L.warning("Error when sending metrics to Influx: {}\n{}".format(
				response.status, response.read().decode("utf-8"))
			)


def get_field(fk, fv):
	if isinstance(fv, bool):
		field = "{}={}".format(fk, 't' if fv else 'f')
	elif isinstance(fv, int):
		field = "{}={}i".format(fk, fv)
	elif isinstance(fv, float):
		field = "{}={}".format(fk, fv)
	elif isinstance(fv, str):
		# Escapes the Field Values and Field Keys if the value is a string
		field = '{}="{}"'.format(fk.replace(" ", r"\ ").replace(",", r"\,").replace("=", r"\="), fv.replace("\\", "\\\\").replace('"', "\\\""))
	else:
		raise RuntimeError("Unknown/invalid type of the metrics field: {} {}".format(type(fv), fk))

	return field


def combine_tags_and_field(tags, values):
	# First escape tags and values
	tags = escape_tags(tags)
	values = escape_values(values)
	# Then combine the tags and then values
	tags_string = ",".join(["{}={}".format(tk, tv) for tk, tv in tags.items()])
	field_set = ",".join([get_field(value_name, value) for value_name, value in values.items()])
	return tags_string + " " + field_set


def build_metric_line(tags, values, upperbound=None):
	if upperbound is not None:
		tags["le"] = upperbound
	return combine_tags_and_field(tags, values)


def metric_to_influxdb(metric_record, now):
	if metric_record.get("@timestamp") is None:
		timestamp = now
	else:
		timestamp = metric_record.get("@timestamp")
	name = escape_name(metric_record.get("name"))
	fieldset = metric_record.get("fieldset")
	metric_type = metric_record.get("type")
	values_lines = []

	if metric_type in ["Histogram", "HistogramWithDynamicTags"]:
		for field in fieldset:
			# SKIP empty fields
			if all([bucket == {} for bucket in field.get("values").get("buckets").values()]):
				continue
			for upperbound, bucket in field.get("values").get("buckets").items():
				upperbound = str(upperbound)
				if bucket == {}:
					continue
				values_lines.append(build_metric_line(field.get("tags").copy(), bucket, upperbound))
			values_lines.append(build_metric_line(field.get("tags").copy(), {"sum": field.get("values").get("sum")}))
			values_lines.append(build_metric_line(field.get("tags").copy(), {"count": field.get("values").get("count")}))

	else:
		for field in fieldset:
			# SKIP empty fields
			if not field.get("values") or field.get("values") == {}:
				continue
			values_lines.append(build_metric_line(field.get("tags"), (field.get("values"))))

	return ["{},{} {}\n".format(name, line, int(timestamp * 1e9)) for line in values_lines]


def escape_name(name: str):
	return name.replace(" ", "\\ ").replace(",", "\\,")


def escape_tags(tags: dict):
	"""
	Escapes special characters in inputted tags to comply with InfluxDB's rules

	https://docs.influxdata.com/influxdb/v2.3/reference/syntax/line-protocol/#special-characters
	"""
	clean: dict = {}
	for k, v in tags.items():
		clean[k.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")] = v.replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")
	return clean


def escape_values(values: dict):
	"""
	Escapes special characters in inputted values to comply with InfluxDB's rules

	https://docs.influxdata.com/influxdb/v2.3/reference/syntax/line-protocol/#special-characters
	"""
	clean: dict = {}
	for k, v in values.items():
		# Escapes the Field Keys
		clean[k.replace(" ", r"\ ").replace(",", r"\,").replace("=", r"\=")] = v
	return clean


def influxdb_format(m_tree, now):
	rb = []
	for metric_record in m_tree:
		influx_records = metric_to_influxdb(metric_record, now)
		rb.extend(influx_records)
	return ''.join(rb)
