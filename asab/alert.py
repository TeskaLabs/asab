import re
import abc
import socket
import logging
import asyncio

import aiohttp
import asab

#

L = logging.getLogger(__name__)

#


class AlertProviderABC(asab.ConfigObject, abc.ABC):

	ConfigDefaults = {
	}


	def __init__(self, config_section_name):
		super().__init__(config_section_name=config_section_name)


	async def initialize(self, app):
		pass


	async def finalize(self, app):
		pass


	@abc.abstractmethod
	def trigger(self, tenant_id, alert_cls, alert_id, title, detail):
		pass


class AlertHTTPProviderABC(AlertProviderABC):

	ConfigDefaults = {
		'url': '',
	}


	def __init__(self, config_section_name):
		super().__init__(config_section_name=config_section_name)
		self.Queue = asyncio.Queue()
		self.MainTask = None

		self.URL = self.Config['url']


	async def initialize(self, app):
		self._start_main_task()


	async def finalize(self, app):
		if self.MainTask is not None:
			mt = self.MainTask
			self.MainTask = None
			mt.cancel()


	def trigger(self, tenant_id, alert_cls, alert_id, title, detail):
		self.Queue.put_nowait((tenant_id, alert_cls, alert_id, title, detail))


	def _start_main_task(self):
		assert(self.MainTask is None)
		self.MainTask = asyncio.ensure_future(self._main())
		self.MainTask.add_done_callback(self._main_done)


	def _main_done(self, x):
		if self.MainTask is None:
			return

		try:
			self.MainTask.result()
		except Exception:
			L.exception("Exception in AlertService main task")

		self.MainTask = None
		self._start_main_task()


	@abc.abstractmethod
	async def _main(self):
		pass


class OpsGenieAlertProvider(AlertHTTPProviderABC):

	ConfigDefaults = {
		# US: https://api.opsgenie.com
		# EU: https://api.eu.opsgenie.com
		'url': 'https://api.eu.opsgenie.com',

		# See https://docs.opsgenie.com/docs/authentication
		# E.g. `eb243592-faa2-4ba2-a551q-1afdf565c889`
		'api_key': '',

		# Coma separated tags to be added to the request
		'tags': '',
	}


	def __init__(self, config_section_name):
		super().__init__(config_section_name=config_section_name)
		self.APIKey = self.Config['api_key']
		self.Tags = re.split(r"[,\s]+", self.Config['tags'], re.MULTILINE)
		self.Hostname = socket.gethostname()


	async def _main(self):
		while True:
			tenant_id, alert_cls, alert_id, title, detail = await self.Queue.get()

			headers = {
				'Authorization': 'GenieKey {}'.format(self.APIKey)
			}

			create_alert = {
				'message': title,
				'note': detail,
				'alias': '{}:{}:{}'.format(tenant_id, alert_cls, alert_id),
				'tags': self.Tags,
				'details': {
					'tenant_id': tenant_id,
					'class': alert_cls,
					'id': alert_id,
				},
				'entity': tenant_id,
				'source': self.Hostname,
			}

			async with aiohttp.ClientSession(headers=headers) as session:
				async with session.post(self.URL + "/v2/alerts", json=create_alert) as resp:
					if resp.status != 202:
						text = await resp.text()
						L.warning("Failed to create the alert: {}".format(text))
					else:
						await resp.text()


class PagerDutyAlertProvider(AlertHTTPProviderABC):

	ConfigDefaults = {
		'url': 'https://events.pagerduty.com',

		# From API Access
		'api_key': 'w_8PcNuhHa-y3xYdmc1x',

		# Integration key (or routing_key) from a Service directory
		# Choose "Use our API directly" and "Events API v2"
		'integration_key': 'f'
	}


	def __init__(self, config_section_name):
		super().__init__(config_section_name=config_section_name)
		self.APIKey = self.Config['api_key']
		self.IntegrationKey = self.Config['integration_key']


	async def _main(self):
		while True:
			tenant_id, alert_cls, alert_id, title, detail = await self.Queue.get()

			headers = {
				'Authorization': 'Token token={}'.format(self.APIKey)
			}

			create_alert = {
				'event_action': 'trigger',
				"routing_key": self.IntegrationKey,
				'dedup_key': '{}:{}:{}'.format(tenant_id, alert_cls, alert_id),

				"client": "Asab Alert Service",

				'payload': {
					'summary': title,
					'severity': 'warning',
					'source': tenant_id,  # TODO: Hostname etc.
					'group': alert_cls,
					"custom_details": {
						'tenant_id': tenant_id,
						'class': alert_cls,
						'id': alert_id,
					},
				},
			}

			async with aiohttp.ClientSession(headers=headers) as session:
				async with session.post(self.URL + "/v2/enqueue", json=create_alert) as resp:
					if resp.status != 202:
						text = await resp.text()
						L.warning("Failed to create the alert ({}):\n{}".format(resp.status, text))
					else:
						await resp.text()


class AlertService(asab.Service):


	def __init__(self, app, service_name="seacatpki.AlertService"):
		super().__init__(app, service_name)
		self.Providers = []

		for section in asab.Config.sections():
			if not section.startswith("asab:alert:"):
				continue

			provider_cls = {
				'asab:alert:opsgenie': OpsGenieAlertProvider,
				'asab:alert:pagerduty': PagerDutyAlertProvider
			}.get(section)
			if provider_cls is None:
				L.warning("Unknwn alert provider: {}".format(section))
				continue

			self.Providers.append(provider_cls(config_section_name=section))


	async def initialize(self, app):
		await asyncio.gather(*[
			p.initialize(app) for p in self.Providers
		])


	async def finalize(self, app):
		await asyncio.gather(*[
			p.finalize(app) for p in self.Providers
		])


	def trigger(self, tenant_id, alert_cls, alert_id, title, detail=''):
		for p in self.Providers:
			p.trigger(tenant_id, alert_cls, alert_id, title, detail)
