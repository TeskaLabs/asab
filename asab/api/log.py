import asyncio
import logging
import datetime

import aiohttp

from ..web.rest.json import json_response
from ..log import LOG_NOTICE

##

L = logging.getLogger(__name__)

##


class WebApiLoggingHandler(logging.Handler):


	def __init__(self, app, level=logging.NOTSET, buffer_size: int = 10):
		super().__init__(level=level)

		self.Buffer = []
		self._buffer_size = buffer_size
		self.WebSockets = set()

		app.PubSub.subscribe("Application.stop!", self._on_stop)


	async def _on_stop(self, _on_stop, x):
		for ws in list(self.WebSockets):
			await ws.send_json({
				"t": datetime.datetime.utcnow().isoformat() + 'Z',  # This is OK, no tzinfo needed
				"C": "asab.web",
				"M": "Closed.",
				"l": logging.INFO,
			})
			await ws.close()


	def emit(self, record):
		if logging.DEBUG < record.levelno <= logging.INFO:
			severity = 6  # Informational
		elif record.levelno <= LOG_NOTICE:
			severity = 5  # Notice
		elif record.levelno <= logging.WARNING:
			severity = 4  # Warning
		elif record.levelno <= logging.ERROR:
			severity = 3  # Error
		elif record.levelno <= logging.CRITICAL:
			severity = 2  # Critical
		else:
			severity = 1  # Alert

		log_entry = {
			"t": datetime.datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
			"C": record.name,
			"s": "{}:{}".format(record.funcName, record.lineno),
			"p": record.process,
			"Th": record.thread,
			"l": severity,
		}

		message = record.getMessage()
		if record.exc_text is not None:
			message += '\n' + record.exc_text
		if record.stack_info is not None:
			message += '\n' + record.stack_info
		if len(message) > 0:
			log_entry['M'] = message

		sd = record.__dict__.get("_struct_data")
		if sd is not None:
			log_entry['sd'] = sd

		if len(self.Buffer) > self._buffer_size:
			del self.Buffer[0]
			self.Buffer.append(log_entry)

		else:
			self.Buffer.append(log_entry)

		if len(self.WebSockets) > 0:
			asyncio.ensure_future(self._send_ws(log_entry))


	async def get_logs(self, request):
		'''
		Get logs.
		---
		tags: ['asab.log']
		'''

		return json_response(request, self.Buffer)


	async def ws(self, request):
		'''
		# Live feed of logs over websocket

		Usable with e.g. with React Lazylog

		```
		<LazyLog
			url={this.AsabLogWsURL}
			follow
			websocket
			websocketOptions={{
				formatMessage: e => log_message_format(e),
			}}
		/>

		function log_message_format(e) {
			e = JSON.parse(e)
			var msg = e.t;
			if (e.l != undefined) msg += " " + e.l;
			if (e.sd != undefined) msg += ` ${JSON.stringify(e.sd)}`;
			if (e.M != undefined) msg += " " + e.M;
			if (e.C != undefined) msg += ` [${e.C}]`
			return msg;
		}
		```

		---
		tags: ['asab.log']
		externalDocs:
			description: React Lazylog
			url: https://github.com/mozilla-frontend-infra/react-lazylog#readme
		'''

		ws = aiohttp.web.WebSocketResponse()
		await ws.prepare(request)

		await ws.send_json({
			"t": datetime.datetime.utcnow().isoformat() + 'Z',  # This is OK, no tzinfo needed
			"C": "asab.web",
			"M": "Connected.",
			"l": logging.INFO,
		})

		# Send historical logs
		for log_entry in self.Buffer:
			await ws.send_json(log_entry)

		self.WebSockets.add(ws)
		try:

			async for msg in ws:
				if msg.type == aiohttp.WSMsgType.ERROR:
					break

		finally:
			self.WebSockets.remove(ws)

		return ws


	async def _send_ws(self, log_entry):
		for ws in self.WebSockets:
			await ws.send_json(log_entry)
