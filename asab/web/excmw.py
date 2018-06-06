import json
import logging
import uuid
import aiohttp.web

#

L = logging.getLogger(__name__)

#

@aiohttp.web.middleware
async def except_json_middleware(request, handler):

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
			L.error(ex, struct_data=struct_data)
		ex.content_type='application/json'
		ex.text=json.dumps(respdict, indent=4)
		raise ex

	# Other errors to JSON
	except Exception as e:
		euuid = uuid.uuid4()
		L.exception("Exception when handling web request".format(euuid), struct_data={'uuid':str(euuid)})
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
