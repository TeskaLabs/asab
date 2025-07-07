import re
import typing
import logging

from .static import StaticTenantProvider

L = logging.getLogger(__name__)


class SystemTenantProvider(StaticTenantProvider):

	Type = "system"


	def __init__(self, app, tenant_service, config):
		super().__init__(app, tenant_service, config)
		self.Tenants: typing.Set[str] = {"system"}
