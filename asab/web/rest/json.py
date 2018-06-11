import json
import aiohttp.web

class _Dumper(object):


	def __init__(self, pretty):
		self.pretty = pretty


	def __call__(self, obj):
		if self.pretty:
			return json.dumps(obj, indent=4, default=self.default) + '\n'	
		else:
			return json.dumps(obj, default=self.default)


	def default(self, o):
		m = getattr(o, 'rest_get', None)
		if m is not None:
			return m()

		return json.JSONEncoder.default(self, o)


def json_response(request, json_obj, **kwargs):
	'''
	## Pretty Result
	When appending ?pretty=true to any request made, the JSON returned will be pretty formatted (use it for debugging only!).
	'''
	pretty = request.query.get('pretty', 'no').lower() in frozenset(['true', '1', 't', 'y', 'yes'])

	return aiohttp.web.json_response(
		json_obj,
		dumps=_Dumper(pretty),
		**kwargs
	)

