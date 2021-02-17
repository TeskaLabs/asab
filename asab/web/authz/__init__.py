from ...config import Config

Config.add_defaults({
	"authz": {
		"rbac_url": "http://localhost:8081/rbac",
	},
})


from .decorator import required

__all__ = (
	"required",
)
