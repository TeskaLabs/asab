import logging
import json

from .. import Service


L = logging.getLogger(__name__)


class ServiceDiscoveryService(Service):

	def __init__(self, app, zkc, service_name="asab.ServiceDiscoveryService"):
		super().__init__(app, service_name)
		self.ZooKeeperContainer = zkc


	async def locate(self, instance_id: str = None, appclass: str = None) -> list:
		if instance_id is None and appclass is None:
			L.warning("Please provide instance_id or appclass to locate the service(s).")
			return

		instances = await self.get_advertised_instances()
		if len(instances) == 0:
			L.warning("No instances available.")
			return
		urls = []
		for instance in instances:
			if appclass is not None:
				if appclass != instance.get("appclass"):
					continue
			if instance_id is not None:
				if instance_id != instance.get("instance_id"):
					continue

			web = instance.get("web")
			servername = instance.get("servername")
			if web is None or servername is None:
				continue
			for i in web:
				try:
					# ip = i[0]
					port = i[1]
				except KeyError:
					L.error("Unexpected format of 'web' section in advertised data: '{}'".format(web))
					return
				urls.append("http://{}:{}".format(servername, port))
		return urls


	async def get_advertised_instances(self):
		advertised = []
		async for item, item_data in self._iter_zk_items("/run"):
			data_dict = json.loads(item_data)
			data_dict['zookeeper_id'] = item
			advertised.append(data_dict)

		return advertised


	async def _iter_zk_items(self, path):
		base_path = self.ZooKeeperContainer.Path + path
		items = await self.ZooKeeperContainer.ZooKeeper.get_children(base_path)
		if items is None:
			L.error("Missing '/run' folder in ZooKeeper basepath '{}'".format(self.ZooKeeperContainer.Path))
			return

		for item in items:
			item_data = await self.ZooKeeperContainer.ZooKeeper.get_data(base_path + '/' + item)
			yield item, item_data
