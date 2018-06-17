import json
import itertools
import functools
import socket
import pprint
import logging

import asab

#

L = logging.getLogger(__name__)

#

class RPC(object):
	'''
	The simplistic implementation of JSON RPC
	http://www.jsonrpc.org/specification
	'''

	MAX_DGRAM_LENGTH = 1024

	def __init__(self, app):
		self.Loop = app.Loop
		self.IdSeq = itertools.count(start=1, step=1)
		self.RPCMethods = {}
		self.RPCResults = {}

		self.Sockets = {}
		self.PrimarySocket = None

		# Parse listen address(es), can be multiline configuration item
		ls = asab.Config["asab:raft"]["listen"]
		for l in ls.split('\n'):
			l = l.strip()
			if len(l) == 0: continue
			addr, port = l.split(' ', 1)
			port = int(port)

			s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
			s.setblocking(0)
			s.bind((addr,port))

			self.Loop.add_reader(s, functools.partial(self.on_recv, s))
			self.Sockets[s.fileno()] = s

			if self.PrimarySocket is None:
				self.PrimarySocket = s

		assert(self.PrimarySocket is not None)


	def bind(self, obj):
		'''
		Resolve all @RPCMethod and @RPCResult decorators in the object and bind them
		'''
		for attr_name in dir(obj):
			attr = getattr(obj, attr_name)
			if hasattr(attr, '_RCPMethod'):
				if attr._RCPMethod in self.RPCMethods:
					L.error("RCP method '{}' is already bound".format(attr._RCPMethod))
				else:
					self.RPCMethods[attr._RCPMethod] = attr
			if hasattr(attr, '_RCPResult'):
				if attr._RCPResult in self.RPCResults:
					L.error("RCP result '{}' is already bound".format(attr._RCPResult))
				else:
					self.RPCResults[attr._RCPResult] = attr

	#

	def _encrypt(self, peer, dgram):
		#TODO: This ...
		return dgram


	def _decrypt(self, peer, dgram):
		#TODO: This ...
		return dgram

	#

	def on_recv(self, s):
		while True:
			result = None
			propagate_error = False

			try:
				request_cgram, peer_address = s.recvfrom(self.MAX_DGRAM_LENGTH)
			except BlockingIOError:
				return

			request_dgram = self._decrypt(peer_address, request_cgram)

			try:
				request_obj = json.loads(request_dgram.decode('utf-8'))
				if request_obj.get('jsonrpc', '?') != "2.0":
					L.error("Incorrect RPC message received (not JSON-RPC 2.0): '{}'".format(request_dgram))
					return

				# rpc call 
				method = request_obj.get('method')
				if method is not None:
					propagate_error = True
					result = self.rpc_dispatch_method(method, request_obj.get('params'))

				else:
					# rpc call result
					result_id = request_obj.get('id')
					result = request_obj.get('result')
					if result is not None:
						self.rpc_dispatch_result(peer_address, result_id, result)
						continue # No reply to results

					else:
						# rcp call error
						error = request_obj.get('error')
						if error is not None:
							self.rpc_dispatch_error(error)
							continue # No reply to results

			except RPCError as e:	
				if propagate_error:
					error_obj = {
						"id": request_obj.get('id'),
						"jsonrpc": "2.0",
						"error": e.obj,
					}
					error_dgram = json.dumps(error_obj).encode('utf-8')
					error_cgram = self._encrypt(peer_address, error_dgram)
					s.sendto(error_cgram, peer_address)
				continue

			except Exception as e:				
				L.exception("Exception during RPC request from '{}'".format(peer_address))
				if propagate_error:
					error_obj = {
						"id": request_obj.get('id'),
						"jsonrpc": "2.0",
						"error": {
							"code": -32603,
							"message": "{}:{}".format(e.__class__.__name__, e),
						},
					}
					error_dgram = json.dumps(error_obj).encode('utf-8')
					error_cgram = self._encrypt(peer_address, error_dgram)
					s.sendto(error_cgram, peer_address)
				continue

			# Handle result
			if result is not None:
				result_obj = {
					"id": request_obj.get('id'),
					"jsonrpc": "2.0",
					"result": result,
				}
				result_dgram = json.dumps(result_obj).encode('utf-8')
				result_cgram = self._encrypt(peer_address, result_dgram)
				s.sendto(result_cgram, peer_address)

	#

	def call(self, peer_address, method, params = None):
		request_id = next(self.IdSeq)
		request_obj = {
			"id": "{}:{}".format(method, request_id),
			"jsonrpc": "2.0",
			"method": method,
			"params": params,
		}
		request_dgram = json.dumps(request_obj).encode('utf-8')
		request_cgram = self._encrypt(peer_address, request_dgram)
		self.PrimarySocket.sendto(request_cgram, peer_address)

	#

	def rpc_dispatch_method(self, method, params):
		'''
		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": 19, "id": 1}

		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": -19, "id": 2}
		'''
		if method == "ping":
			if params is None:
				return "pong"
			else:
				return params

		m = self.RPCMethods.get(method)
		if m is not None:
			return m(params)

		raise RPCError(-32601, "Method not found", data=method)


	def rpc_dispatch_result(self, peer_address, result_id, result):
		'''
		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": 19, "id": 1}

		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": -19, "id": 2}
		'''
		result_method, _ = result_id.split(":", 1)

		m = self.RPCResults.get(result_method)
		if m is not None:
			return m(peer_address, result)

		L.error("Received result for unknown method '{}'".format(result_id))


	def rpc_dispatch_error(self, error):
		'''
		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "foobar", "id": "1"}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "1"}
		'''
		print("!!! rpc_dispatch_error", error)

#

class RPCMethod(object):

	def __init__(self, method):
		self.Method = method

	def __call__(self, f):
		f._RCPMethod = self.Method
		return f

#

class RPCResult(object):

	def __init__(self, method):
		self.Method = method

	def __call__(self, f):
		f._RCPResult = self.Method
		return f

#

class RPCError(Exception):

	def __init__(self, code, message, data=None):
		super().__init__("{}: {}".format(code, message))

		self.obj = {
			"code": code,
			"message": message
		}

		if data is not None:
			self.obj['data'] = data

