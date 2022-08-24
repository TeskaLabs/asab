import json
import logging
import uuid
import datetime
import aiohttp.web
import fastjsonschema

from ... import exceptions

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
			if o.tzinfo == datetime.timezone.utc:
				# isoformat ends with "+00:00", replace it with "Z"
				return o.isoformat()[:-6] + "Z"
			elif o.tzinfo is not None:
				# The datetime object is timezone-aware but not UTC
				# NOT WANTED, using non-UTC timestamps is not recommended
				return o.isoformat()
			else:
				# The datetime object is timezone-naive -> interpret it as UTC
				return o.isoformat() + "Z"

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
		if ex.status == 401:
			result = "NOT-AUTHORIZED"
		elif ex.status == 404:
			result = "NOT-FOUND"
		else:
			result = "ERROR"

		respdict = {
			'result': result,
			'message': ex.text,
		}
		if ex.status >= 400:
			euuid = uuid.uuid4()
			respdict["uuid"] = str(euuid)
			struct_data = {
				"uuid": str(euuid),
				"path": request.path,
				"status": ex.status,
				**request.headers
			}
			Lex.error(ex, struct_data=struct_data)

		ex.content_type = 'application/json'
		ex.text = json.dumps(respdict)
		raise ex

	# KeyError translates to 404
	except KeyError as e:
		euuid = uuid.uuid4()
		struct_data = {
			"uuid": str(euuid),
			"path": request.path,
			"status": 404,
			**request.headers
		}
		Lex.warning("KeyError when handling web request", exc_info=True, struct_data=struct_data)

		if len(e.args) > 1:
			message = e.args[0].format(*e.args[1:])
		elif len(e.args) == 1 and e.args[0] is not None:
			message = e.args[0]
		else:
			message = "KeyError"

		return json_response(
			request,
			data={
				"result": "NOT-FOUND",
				"message": message,
				"uuid": str(euuid),
			},
			status=404,
		)

	# ValidationError translates to 400
	except exceptions.ValidationError as e:
		euuid = uuid.uuid4()
		struct_data = {
			"uuid": str(euuid),
			"path": request.path,
			"status": 400,
			**request.headers
		}
		Lex.warning("ValidationError when handling web request", exc_info=True, struct_data=struct_data)

		if len(e.args) > 1:
			message = e.args[0].format(*e.args[1:])
		elif len(e.args) == 1 and e.args[0] is not None:
			message = e.args[0]
		else:
			message = "ValidationError"
		return json_response(
			request,
			data={
				"result": "VALIDATION-ERROR",
				"message": message,
				"uuid": str(euuid),
			},
			status=400,
		)

	# Conflict translates to 409
	except exceptions.Conflict as e:
		euuid = uuid.uuid4()
		struct_data = {
			"uuid": str(euuid),
			"path": request.path,
			"status": 409,
			**request.headers
		}
		Lex.warning("Conflict when handling web request", exc_info=True, struct_data=struct_data)

		if len(e.args) > 1:
			message = e.args[0].format(*e.args[1:])
		elif len(e.args) == 1 and e.args[0] is not None:
			message = e.args[0]
		else:
			message = "Conflict"

		return json_response(
			request,
			data={
				"result": "CONFLICT",
				"message": message,
				"uuid": str(euuid),
			},
			status=409,
		)

	# Other errors to JSON
	except Exception:
		euuid = uuid.uuid4()
		struct_data = {
			"uuid": str(euuid),
			"path": request.path,
			"status": 500,
			**request.headers
		}
		Lex.exception("Exception when handling web request", exc_info=True, struct_data=struct_data)
		return json_response(
			request,
			data={
				"result": "ERROR",
				"message": "Internal Server Error",
				"uuid": str(euuid),
			},
			status=500,
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
				try:
					data = await request.json()
				except json.decoder.JSONDecodeError:
					raise aiohttp.web.HTTPBadRequest(reason="Failed to parse JSON request")
			elif request.content_type in form_content_types:
				multi_dict = await request.post()
				data = {k: v for k, v in multi_dict.items()}
			else:
				raise aiohttp.web.HTTPBadRequest(reason="Unsupported content-type {}".format(request.content_type))
			# Checking the validation on JSON data set
			try:
				validate(data)
				kwargs['json_data'] = data
			except fastjsonschema.exceptions.JsonSchemaException as e:
				raise aiohttp.web.HTTPBadRequest(reason=str(e))
			except Exception as e:
				Lex.error("JSON validation error. Reason: {}".format(e), struct_data={"path": request.path, "method": request.method})
				raise e

			return await func(*args, **kwargs)

		# This is here for Swagger documentation
		setattr(validator, 'json_schema', json_schema)
		setattr(validator, 'func', func)

		return validator

	return decorator
