import json
import logging
import uuid
import datetime
import aiohttp.web

#

L = logging.getLogger(__name__)
Lex = logging.getLogger("asab.web")


#

class JSONDumper(object):

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

		if isinstance(o, datetime.datetime):
			return o.isoformat()

		elif isinstance(o, bytes):
			return o.hex()

		try:
			return json.JSONEncoder.default(self, o)
		except TypeError:
			return "{}".format(o)


def json_response(request, data, pretty=None, dumps=JSONDumper, **kwargs):
	'''
	argument `dumps` allows to specify custom JSON dumper for a serialization.
	The default is `JSONDumper` class.
	
	## Pretty Result
	When appending ?pretty=true to any request made, the JSON returned will be pretty formatted (use it for debugging only!).
	'''
	assert issubclass(dumps, JSONDumper)
	pretty = request.query.get('pretty', 'no').lower() in frozenset(['true', '1', 't', 'y', 'yes']) or pretty

	return aiohttp.web.json_response(
		data,
		dumps=dumps(pretty),
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
			struct_data = {'uuid': str(euuid)}
			respdict['uuid'] = str(euuid)
			struct_data.update(request.headers)
			struct_data['path'] = request.path
			struct_data['status'] = ex.status
			Lex.error(ex, struct_data=struct_data)

		ex.content_type = 'application/json'
		ex.text = json.dumps(respdict, indent=4)
		raise ex

	# KeyError translates to 404
	except KeyError as e:
		euuid = uuid.uuid4()
		Lex.warning("KeyError when handling web request", exc_info=e, struct_data={'uuid': str(euuid)})

		if len(e.args) > 1:
			message = e.args[0] % e.args[1:]
		elif e.args[0] is None:
			message = "KeyError"
		else:
			message = e.args[0]

		return aiohttp.web.Response(
			text=json.dumps({
				"status": 404,
				"message": message,
				"uuid": str(euuid),
			}, indent=4),
			status=404,
			content_type='application/json'
		)

	# Other errors to JSON
	except Exception as e:
		euuid = uuid.uuid4()
		Lex.exception("Exception when handling web request", exc_info=e, struct_data={'uuid': str(euuid)})
		return aiohttp.web.Response(
			text=json.dumps({
				"status": 500,
				"message": "Internal Server Error",
				"uuid": str(euuid),
			}, indent=4),
			status=500,
			content_type='application/json'
		)
