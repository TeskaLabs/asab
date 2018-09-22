import logging
import aiohttp

import asab

#

L = logging.getLogger(__name__)

#

class MetricsInfluxDB(asab.ConfigObject):


	ConfigDefaults = {
		'url': 'http://localhost:8086/',
		'db': 'mydb',
	}


	def __init__(self, svc, config_section_name, config=None):
		super().__init__(config_section_name=config_section_name, config=config)

		self.WriteURL = '{}/write?db={}'.format(self.Config.get('url').rstrip('/'), self.Config.get('db'))


	async def process(self, now, mlist):
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

		async with aiohttp.ClientSession() as session:
			async with session.post(self.WriteURL, data=rb) as resp:
				response = await resp.text()
				if resp.status != 204:
					L.warning("Error when sending metrics to Influx: {}\n{}".format(resp.status, response))

