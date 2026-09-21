from .static import StaticTenantProvider
from .system import SystemTenantProvider
from .web import WebTenantProvider
from .zookeeper import ZookeeperTenantProvider

__all__ = [
	"StaticTenantProvider",
	"SystemTenantProvider",
	"WebTenantProvider",
	"ZookeeperTenantProvider"
]
