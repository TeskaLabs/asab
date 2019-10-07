import abc

from ....config import ConfigObject


class ABCOAuthMethod(abc.ABC, ConfigObject):

	ConfigDefaults = {
		"oauth_server_id": "teskalabs.com",
		"token_url": "http://localhost:8080/token_endpoint/token_request",  # POST -> to receive access token and refresh token
		"identity_url": "http://localhost:8080/identity_provider/identity",  # GET -> UserInfo identity
		"invalidate_url": "",  # POST -> Invalidate a token
		"forgot_url": "",  # POST -> Send request for a forgot password or other identity credentials
	}

	def __init__(self, config_section_name=None, config=None):
		config_section_name = config_section_name if config_section_name is not None else self.__class__.__name__
		super().__init__(config_section_name=config_section_name, config=config)

	@abc.abstractmethod
	def extract_identity(self, oauth_user_info):
		pass


class GitHubOAuthMethod(ABCOAuthMethod):

	def __init__(self, config_section_name=None):
		super().__init__(config_section_name, {
			"oauth_server_id": "github.com",
			"token_url": "https://github.com/login/oauth/access_token",
			"identity_url": "https://api.github.com/user",
		})

	def extract_identity(self, oauth_user_info):
		return oauth_user_info["email"]


class OpenIDConnectMethod(ABCOAuthMethod):

	def extract_identity(self, oauth_user_info):
		return str(oauth_user_info["sub"])
