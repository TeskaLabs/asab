from ...config import Config

Config.add_defaults({
	"authz": {
		"rbac_url": "http://localhost:8081/rbac",
	},
})


from .decorator import required
from .middleware import authz_middleware_factory
from .service import AuthzService

__all__ = (
	"required",
	"authz_middleware_factory",
	"AuthzService"
)
