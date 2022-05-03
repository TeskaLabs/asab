import logging
import aiohttp
import urllib

import http.client

import asab

#

L = logging.getLogger(__name__)

#



def get_field_set(fk, fv):
	if isinstance(fv, bool):
		field = "{}={}".format(fk, 't' if fv else 'f')
	elif isinstance(fv, int):
		field = "{}={}i".format(fk, fv)
	elif isinstance(fv, float):
		field = "{}={}".format(fk, fv)
	elif isinstance(fv, str):
		field = '{}="{}"'.format(fk, fv.replace('"', r'\"'))
	else:
		raise RuntimeError("Unknown/invalid type of the metrics field: {} {}".format(type(fv), fk))

	return field


def metric_to_influxdb(metric_record):
	timestamp = metric_record.get("@timestamp")
	name = metric_record.get("Name")
	values = metric_record.get("Values")
	tags = metric_record.get("Tags")

	if all([isinstance(i["value_name"], (str, int, float)) for i in values]):
		field_set = []
		for i in values:
			fk = i["value_name"]
			fv = i["value"]
			field_set.append(get_field_set(fk, fv))
		for tk, tv in tags.items():
			name += ',{}={}'.format(tk.replace(" ", "_"), tv.replace(" ", "_"))

		influxdb_format = "{} {} {}\n".format(name, ', '.join(field_set), int(timestamp * 1e9))

	else:
		values_lines = []
		for i in values:
			fk = i["value_name"]
			fv = i["value"]
			dynamic_tags = tags.copy()
			if isinstance(fk, dict):
				dynamic_tags.update(fk)
			elif isinstance(fk, (tuple, list)):
				dynamic_tags.update({"label" + str(i): value_name for i, value_name in enumerate(fk)})
			elif isinstance(fk, str):
				dynamic_tags.update({"value_name": fk})

			tags_string = ",".join(['{}={}'.format(tk.replace(" ", "_"), tv.replace(" ", "_")) for tk, tv in dynamic_tags.items()])
			field_set = get_field_set(name, fv)
			values_lines.append(tags_string + " " + field_set)
		if len(values_lines) != 0:
			influxdb_format = "".join(["{},{} {}\n".format(name, line, int(timestamp * 1e9)) for line in values_lines])

	return influxdb_format


def influxdb_format(mlist):
	# CAREFUL: This function is used also in asab.logman.metrics
	rb = ""
	for metric_record in mlist:
		rb += metric_to_influxdb(metric_record)
	return rb


class MetricsInfluxDB(asab.ConfigObject):
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


	async def process(self, mlist):

		# When ProActor is enabled

		if self.ProactorService is not None:
			await self.ProactorService.execute(self._worker_upload, mlist)
			return

		# When ProActor is disabled

		rb = influxdb_format(mlist)

		async with aiohttp.ClientSession(headers=self.Headers) as session:
			async with session.post(self.WriteURL, data=rb) as resp:
				response = await resp.text()
				if resp.status != 204:
					L.warning("Error when sending metrics to Influx: {}\n{}".format(resp.status, response))


	def _worker_upload(self, mlist):

		rb = influxdb_format(mlist)

		if self.BaseURL.startswith("https://"):
			conn = http.client.HTTPSConnection(self.BaseURL.replace("https://", ""))
		else:
			conn = http.client.HTTPConnection(self.BaseURL.replace("http://", ""))

		conn.request("POST", self.WriteRequest, rb, self.Headers)

		response = conn.getresponse()
		if response.status != 204:
			L.warning("Error when sending metrics to Influx: {}\n{}".format(
				response.status, response.read().decode("utf-8"))
			)
