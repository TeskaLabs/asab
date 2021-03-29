import logging
import aiohttp
import urllib

import http.client

import asab

#

L = logging.getLogger(__name__)

#


def influxdb_format(now, mlist):
	# CAREFUL: This function is used also in asab.logman.metrics
	rb = ""
	for metric, values in mlist:
		name = metric.Name

		field_set = []
		for fk, fv in values.items():
			if isinstance(fv, int):
				field_set.append("{}={}i".format(fk, fv))
			elif isinstance(fv, float):
				field_set.append("{}={}".format(fk, fv))
			elif isinstance(fv, str):
				field_set.append('{}="{}"'.format(fk, fv.replace('"', r'\"')))
			elif isinstance(fv, bool):
				field_set.append("{}={}".format(fk, 't' if fv else 'f'))
			else:
				raise RuntimeError("Unknown/invalud type of the metrics field: {} {}".format(type(fv), fk))

		for tk, tv in metric.Tags.items():
			name += ',{}={}'.format(tk, tv)

		rb += "{} {} {}\n".format(name, ','.join(field_set), int(now * 1e9))

	return rb


class MetricsInfluxDB(asab.ConfigObject):


	ConfigDefaults = {
		'url': 'http://localhost:8086/',
		'db': 'mydb',
		'username': '',
		'password': '',
		'proactor': True,  # Use ProactorService to send metrics on thread
	}


	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name=config_section_name, config=config)

		self.BaseURL = self.Config.get('url').rstrip('/')
		self.WriteRequest = '/write?db={}'.format(self.Config.get('db'))

		username = self.Config.get('username')
		if username is not None and len(username) > 0:
			self.WriteRequest += '&u={}'.format(urllib.parse.quote(username, safe=''))

		password = self.Config.get('password')
		if password is not None and len(password) > 0:
			self.WriteRequest += '&p={}'.format(urllib.parse.quote(password, safe=''))

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


	async def process(self, now, mlist):

		# When ProActor is enabled

		if self.ProactorService is not None:
			await self.ProactorService.execute(self._worker_upload, now, mlist)
			return

		# When ProActor is disabled

		rb = influxdb_format(now, mlist)

		async with aiohttp.ClientSession() as session:
			async with session.post(self.WriteURL, data=rb) as resp:
				response = await resp.text()
				if resp.status != 204:
					L.warning("Error when sending metrics to Influx: {}\n{}".format(resp.status, response))


	def _worker_upload(self, now, mlist):

		rb = influxdb_format(now, mlist)

		if self.BaseURL.startswith("https://"):
			conn = http.client.HTTPSConnection(self.BaseURL.replace("https://", ""))
		else:
			conn = http.client.HTTPConnection(self.BaseURL.replace("http://", ""))

		conn.request("POST", self.WriteRequest, rb)

		response = conn.getresponse()
		if response.status != 204:
			L.warning("Error when sending metrics to Influx: {}\n{}".format(
				response.status, response.read().decode("utf-8"))
			)
