import json
import itertools
import logging

#

L = logging.getLogger(__name__)

#

class RPC(object):
	'''
	The simplistic implementation of JSON RPC
	http://www.jsonrpc.org/specification
	'''

	MAX_DGRAM_LENGTH = 1024

	def __init__(self, raft_service):
		self.RaftService = raft_service
		self.IdSeq = itertools.count(start=1, step=1)

		self.RPCMethods = {}
		for attr_name in dir(raft_service):
			attr = getattr(raft_service, attr_name)
			if not hasattr(attr, '_RCPMethod'): continue
			self.RPCMethods[attr._RCPMethod] = attr

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
				request_cgram, peer = s.recvfrom(self.MAX_DGRAM_LENGTH)
			except BlockingIOError:
				return

			request_dgram = self._decrypt(peer, request_cgram)

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
					result = request_obj.get('result')
					if result is not None:
						self.rpc_dispatch_result(result)
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
					error_cgram = self._encrypt(peer, error_dgram)
					s.sendto(error_cgram, peer)
				continue

			except Exception as e:				
				L.exception("Exception during RPC request from '{}'".format(peer))
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
					error_cgram = self._encrypt(peer, error_dgram)
					s.sendto(error_cgram, peer)
				continue

			# Handle result
			if result is not None:
				result_obj = {
					"id": request_obj.get('id'),
					"jsonrpc": "2.0",
					"result": result,
				}
				result_dgram = json.dumps(result_obj).encode('utf-8')
				result_cgram = self._encrypt(peer, result_dgram)
				s.sendto(result_cgram, peer)

	#

	def call(self, peer, method, params = None):
		request_id = next(self.IdSeq)
		request_obj = {
			"id": request_id,
			"jsonrpc": "2.0",
			"method": method,
			"params": params,
		}
		request_dgram = json.dumps(request_obj).encode('utf-8')
		request_cgram = self._encrypt(peer, request_dgram)
		self.RaftService.PrimarySocket.sendto(request_cgram, peer)

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


	def rpc_dispatch_result(self, result):
		'''
		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": 19, "id": 1}

		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": -19, "id": 2}
		'''
		print("!!! rpc_dispatch_result", result)


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

class RPCError(Exception):

	def __init__(self, code, message, data=None):
		super().__init__("{}: {}".format(code, message))

		self.obj = {
			"code": code,
			"message": message
		}

		if data is not None:
			self.obj['data'] = data

