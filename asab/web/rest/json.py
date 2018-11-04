import json
import logging
import uuid
import aiohttp.web
#

L = logging.getLogger(__name__)
Lex = logging.getLogger("asab.web")

#

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


def json_response(request, data, pretty=None, **kwargs):
	'''
	## Pretty Result
	When appending ?pretty=true to any request made, the JSON returned will be pretty formatted (use it for debugging only!).
	'''
	pretty = request.query.get('pretty', 'no').lower() in frozenset(['true', '1', 't', 'y', 'yes']) or pretty

	return aiohttp.web.json_response(
		data,
		dumps=_Dumper(pretty),
		**kwargs
	)


@aiohttp.web.middleware
async def JsonExceptionMiddleware(request, handler):

	'''
	Installation of the handler to a web service:
		
	websvc.WebApp.middlewares.append(asab.web.rest.JsonExceptionMiddleware)
	'''

	try:
		response = await handler(request)
		return response

	# HTTP errors to JSON
	except aiohttp.web.HTTPError as ex:
		respdict = {
			'status': ex.status,
			'mesage': ex.text[5:]
		}
		if ex.status >= 400:
			euuid = uuid.uuid4()
			struct_data = {'uuid':str(euuid)}
			respdict['uuid'] = str(euuid)
			struct_data.update(request.headers)
			struct_data['path']=request.path
			struct_data['status'] = ex.status
			Lex.error(ex, struct_data=struct_data)

		ex.content_type='application/json'
		ex.text=json.dumps(respdict, indent=4)
		raise ex

	# Other errors to JSON
	except Exception as e:
		euuid = uuid.uuid4()
		Lex.exception("Exception when handling web request".format(euuid), struct_data={'uuid':str(euuid)})
		return aiohttp.web.Response(
			text=json.dumps({
				"status": 500,
				"message": "Internal Server Error",
				"uuid": str(euuid),
			},
			indent=4),
			status=500,
			content_type='application/json'
		)
