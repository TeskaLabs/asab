from .static import StaticTenantProvider
from .web import WebTenantProvider
from .zookeeper import ZookeeperTenantProvider

__all__ = [
	"StaticTenantProvider",
	"WebTenantProvider",
	"ZookeeperTenantProvider"
]
