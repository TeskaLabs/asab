import enum


class ASABConfigException(Exception):

	def __init__(self, error_code, error_dict=None, tech_message=None, error_i18n_key=None):
		super().__init__()
		self.ErrorCode = error_code
		if error_dict is None:
			self.ErrorDict = {}
		else:
			self.ErrorDict = error_dict
		self.TechMessage = tech_message
		# Adds a prefix to an error key (internationalization)
		if error_i18n_key is not None:
			self.Errori18nKey = "ConfigError|" + error_i18n_key
		else:
			self.Errori18nKey = "ConfigError|"


class ErrorCode(enum.Enum):
	GENERAL = 0  # This should not be actually used, if yes, then replace by existing/new error code
	CONFIGS_MISSING = 1
	CONFIG_MISSING = 2
	INVALID_JSON = 3
	INVALID_CONFIG = 4
	ZOOKEEPER_LOST = 5
	CONFIG_TYPE_MISSING = 6
	RESTORE_FAILED = 7
	INVALID_LINK = 8
	EXPIRED_LINK = 9
