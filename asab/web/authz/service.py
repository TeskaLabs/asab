import asab


class AuthzService(asab.Service):

	def __init__(self, app, service_name="asab.AuthzService"):
		super().__init__(app, service_name)

		self.RequiredDecoratorCache = {}
		app.PubSub.subscribe("Application.tick/60!", self._evaluate_expiration_in_cache)

	async def _evaluate_expiration_in_cache(self, event_name):
		cache_keys_to_delete = list()

		for cache_key, cache_value in self.RequiredDecoratorCache.items():
			authorized, expiration = cache_value
			if self.App.time() >= expiration:
				cache_keys_to_delete.append(cache_key)

		for cache_key in cache_keys_to_delete:
			del self.RequiredDecoratorCache[cache_key]

	def get_from_required_decorator_cache(self, cache_key):
		cache_value = self.RequiredDecoratorCache.get(cache_key)
		if cache_value is None:
			return None

		return cache_value[0]

	def set_to_required_decorator_cache(self, cache_key, authorized):
		self.RequiredDecoratorCache[cache_key] = (authorized, self.App.time() + 300)
