import logging

import aiohttp.abc

from ..log import LOG_NOTICE

class AccessLogger(aiohttp.abc.AbstractAccessLogger):

	def log(self, request, response, time):
		struct_data={
			'I': request.remote,
			'al.m': request.method,
			'al.p': request.path,
			'al.c': response.status,
			'D': time,
		}

		if request.content_length is not None:
			struct_data['al.B'] = request.content_length

		if response.content_length is not None:
			struct_data['al.b'] = response.content_length

		agent = request.headers.get('User-Agent')
		if agent is not None:
			struct_data['al.A'] = agent

		self.logger.log(LOG_NOTICE, '', struct_data=struct_data)
