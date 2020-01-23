import json
import logging
import uuid
import datetime
import aiohttp.web
import fastjsonschema

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
	When appending ?pretty to any request made, the JSON returned will be pretty formatted (use it for debugging only!).
	'''
	assert issubclass(dumps, JSONDumper)
	pretty = request.query.get('pretty', 'no').lower() in frozenset(['true', '1', 't', 'y', 'yes', '']) or pretty

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
			'message': ex.text[5:]
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


def json_schema_handler(json_schema, *_args, **_kwargs):

	"""
	The json schema handler implements validation of JSON documents by JSON schema.
	The library of fastjsonschema implements JSON schema drafts 04, 06 and 07
	https://horejsek.github.io/python-fastjsonschema/

	Examples of use:

	@asab.web.rest.json_schema_handler({
	'type': 'object',
	'properties': {
		'key1': {'type': 'string'},
		'key2': {'type': 'number'},
	}})
	async def login(self, request, *, json_data):
		...

	or by specifying json as file

	@asab.web.rest.json_schema_handler('./data/sample_json_schema.json')
	async def login(self, request, *, json_data):
		...

	Works for `application/json`, `application/x-www-form-urlencoded` and `multipart/form-data` post requests
	"""

	def decorator(func):
		# Initializing fastjsonschema.compile method and generating
		# the validation function for validating JSON schema

		# JSON schema set as a dict
		if isinstance(json_schema, dict):
			validate = fastjsonschema.compile(json_schema)

		# JSON schema set in a file
		elif isinstance(json_schema, str):
			with open(json_schema) as f:
				schema = json.load(f)
				validate = fastjsonschema.compile(schema)
		else:
			raise ValueError(
				"JSON schema input must be type <class 'dict'> or type <class 'str'>, "
				"not type {}.".format(type(json_schema)))

		form_content_types = frozenset(['', 'application/x-www-form-urlencoded', 'multipart/form-data'])

		async def validator(*args, **kwargs):
			# Initializing fastjsonschema.compile method and generating
			# the validation function for validating JSON schema
			request = args[-1]
			if request.content_type == 'application/json':
				data = await request.json()
			elif request.content_type in form_content_types:
				multi_dict = await request.post()
				data = {k: v for k, v in multi_dict.items()}
			else:
				Lex.warning(f"Unsupported content-type {request.content_type} for request {request}")
				raise aiohttp.web.HTTPBadRequest(reason=f"Unsupported content-type {request.content_type}")
			# Checking the validation on JSON data set
			try:
				validate(data)
				kwargs['json_data'] = data
			except fastjsonschema.exceptions.JsonSchemaException as e:
				Lex.warning(f"Can not validate request {request}. Reason: {e}")
				raise aiohttp.web.HTTPBadRequest(reason=str(e))
			except Exception as e:
				Lex.error(f"Unknown validation error for request {request}. Reason: {e}")
				raise e

			return await func(*args, **kwargs)

		return validator

	return decorator
