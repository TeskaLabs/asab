import abc


class ABCOAuthMethod(abc.ABC):

	@abc.abstractmethod
	def get_oauth_server_id(self):
		pass

	@abc.abstractmethod
	def get_oauth_userinfo_url(self):
		pass

	@abc.abstractmethod
	def get_identity_from_oauth_user_info(self, oauth_user_info):
		pass


class GitHubOAuthMethod(ABCOAuthMethod):

	def get_oauth_server_id(self):
		return "github.com"

	def get_oauth_userinfo_url(self):
		return 'https://api.github.com/user'

	def get_identity_from_oauth_user_info(self, oauth_user_info):
		return oauth_user_info["email"]


class OpenIDConnectMethod(ABCOAuthMethod):

	def __init__(self, oauth_server_id, oauth_userinfo_url):
		super().__init__()
		self.OAuthServerId = oauth_server_id
		self.OAuthUserInfoUrl = oauth_userinfo_url

	def get_oauth_server_id(self):
		return self.OAuthServerId

	def get_oauth_userinfo_url(self):
		return self.OAuthUserInfoUrl

	def get_identity_from_oauth_user_info(self, oauth_user_info):
		return str(oauth_user_info["sub"])
