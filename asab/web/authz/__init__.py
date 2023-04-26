"""
OBSOLETE MODULE, to be deleted after January 2024

Use 'asab.web.auth' instead

"""

from .decorator import required, userinfo_handler
from .middleware import authz_middleware_factory
from .service import AuthzService

__all__ = (
	"required",
	"userinfo_handler",
	"authz_middleware_factory",
	"AuthzService"
)
