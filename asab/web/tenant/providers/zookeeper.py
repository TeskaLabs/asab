import typing
import logging

from .abc import TenantProviderABC
from ....zookeeper import ZooKeeperContainer


L = logging.getLogger(__name__)


class ZookeeperTenantProvider(TenantProviderABC):
	def __init__(self, app, tenant_service, config):
		super().__init__(app, tenant_service, config)
		self.Tenants: typing.Set[str] = set()

		# Initialize ZooKeeper Client
		self.ZooKeeperService = self.App.get_service("asab.ZooKeeperService")
		self.ZKPath = self.Config.get("zk_path")
		self.ZookeeperContainer = ZooKeeperContainer(
			self.ZooKeeperService,
			config_section_name="zookeeper",
			z_path=self.ZKPath
		)
		self.ZookeeperClient = self.ZookeeperContainer.ZooKeeper


	async def get_tenants(self) -> typing.Set[str]:
		return self.Tenants


	async def is_tenant_known(self, tenant: str) -> bool:
		return tenant in self.Tenants


	async def update(self):
		try:
			zk_node_exists = await self.ZookeeperClient.exists(self.ZKPath)

			if zk_node_exists:
				external_tenants = await self.ZookeeperClient.get_children(self.ZKPath)
				self._set_ready(True)  # Provider was checked => True

			elif zk_node_exists is None:
				L.warning(
					"Failed to load tenants: zk node doesn't exist",
					struct_data={"path": self.ZKPath}
				)
				self._set_ready(True)  # Provider was checked (no data in ZK) => True
				return

		except Exception as e:
			self._set_ready(False)  # Failed to check the provider
			L.exception(
				"Failed to load tenants",
				struct_data={
					"class": e.__class__.__name__.__str__(),
					"reason": str(e),
					"path": self.ZKPath
				}
			)
			return

		new_tenants = set(external_tenants)
		if self.Tenants != new_tenants:
			L.debug("Tenants from Zookeeper updated", struct_data={"path": self.ZKPath})
			self.Tenants = new_tenants
			self.App.PubSub.publish("Tenants.change!")

		if not self._IsReady:
			self._set_ready(True)
