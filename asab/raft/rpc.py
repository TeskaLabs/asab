import json
import itertools
import functools
import asyncio
import socket
import pprint
import logging

import Crypto
import Crypto.Random
import Crypto.Cipher.AES
import Crypto.Hash.HMAC
import Crypto.Hash.SHA256

import asab

#

L = logging.getLogger(__name__)

#

class RPC(object):
	'''
	The simplistic implementation of JSON-RPC 2.0
	http://www.jsonrpc.org/specification
	'''

	def __init__(self, app):
		self.Loop = app.Loop
		self.PubSub = app.PubSub
		self.IdSeq = itertools.count(start=1, step=1)
		self.RPCMethods = {}
		self.ACallRegister = {} # Asynchronous call register
		self.MaxRPCPayloadSize = int(asab.Config.get('asab:raft', 'max_rpc_payload_size'))
		self.DelayedReplies = {}

		self.Sockets = {}
		self.PrimarySocket = None

		self.SecretKey = asab.Config.get('asab:raft', 'secret_key')
		self.SecretKeyBytes = self.SecretKey.encode('utf-8')
		self.CryptoRandom = Crypto.Random.new()

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

		app.PubSub.subscribe("Application.tick!", self._on_tick)


	async def finalize(self, app):
		for acall in self.ACallRegister.values():
			acall.cancel()


	def pop_delayed_reply(self, key):
		return self.DelayedReplies.pop(key, None)


	def _on_tick(self, message_type):
		# Find out acall (awaitable calls) that should be timeouted and timeout them
		now = self.Loop.time()

		filtered_acalls = [acall.RequestId for acall in self.ACallRegister.values() if acall.TimeoutAt <= now]
		for request_id in filtered_acalls:
			acall = self.ACallRegister.pop(request_id)
			acall.timeout()

		if len(self.ACallRegister) > 30:
			L.warn("Too high number ({}) of registred acalls!".format(len(self.ACallRegister)))

		# Remove timeouted deplayed replies
		to_remove = set()
		for delayed_reply in self.DelayedReplies.values():
			if delayed_reply.TimeoutAt <= now:
				delayed_reply.timeout()
				to_remove.add(delayed_reply.Key)
		for key in to_remove:
			del self.DelayedReplies[key]


	def bind(self, obj):
		'''
		Resolve all @RPCMethod decorators in the target `obj` and bind them
		'''
		for attr_name in dir(obj):
			attr = getattr(obj, attr_name)
			if hasattr(attr, '_RCPMethod'):
				if attr._RCPMethod in self.RPCMethods:
					L.error("RCP method '{}' is already bound".format(attr._RCPMethod))
				else:
					self.RPCMethods[attr._RCPMethod] = attr

	#

	def _encrypt(self, peer, dgram):
		'''
		AES CFB with HMAC (SHA-256) Encrypt-then-MAC (EtM)
		'''
		iv = self.CryptoRandom.read(Crypto.Cipher.AES.block_size)
		cipher = Crypto.Cipher.AES.new(self.SecretKey, Crypto.Cipher.AES.MODE_CFB, iv)
		cgram = iv + cipher.encrypt(dgram)

		h = Crypto.Hash.HMAC.new(self.SecretKeyBytes, digestmod=Crypto.Hash.SHA256)
		h.update(cgram)
		mac = h.digest()
		
		return cgram + mac


	def _decrypt(self, peer, cgram):
		h = Crypto.Hash.HMAC.new(self.SecretKeyBytes, digestmod=Crypto.Hash.SHA256)

		iv = cgram[:Crypto.Cipher.AES.block_size]
		msg = cgram[Crypto.Cipher.AES.block_size:-h.digest_size]
		mac = cgram[-h.digest_size:]

		h.update(cgram[:-h.digest_size])
		mac_verify = h.digest()
		if mac != mac_verify:
			L.error("Untrusted message received from '{}'".format(peer))
			return None

		cipher = Crypto.Cipher.AES.new(self.SecretKey, Crypto.Cipher.AES.MODE_CFB, iv)
		dgram = cipher.decrypt(msg)

		return dgram

	#

	def on_recv(self, s):
		while True:
			result = None
			propagate_error = False

			try:
				request_cgram, peer_address = s.recvfrom(self.MaxRPCPayloadSize)
			except BlockingIOError:
				return

			request_dgram = self._decrypt(peer_address, request_cgram)
			if request_dgram is None:
				return

			try:
				request_obj = json.loads(request_dgram.decode('utf-8'))
				if request_obj.get('jsonrpc', '?') != "2.0":
					L.error("Incorrect RPC message received (not JSON-RPC 2.0): '{}'".format(request_dgram))
					return

				# rpc call 
				method = request_obj.get('method')
				if method is not None:
					propagate_error = True
					result = self.rpc_dispatch_method(peer_address, method, request_obj.get('params'))

				else:
					# rpc call result
					result_id = request_obj.get('id')
					result = request_obj.get('result')
					if result is not None:
						self.rpc_dispatch_result(peer_address, result_id, result)
						continue # No reply to results

					else:
						# rcp call error
						result_id = request_obj.get('id')
						error = request_obj.get('error')
						if error is not None:
							self.rpc_dispatch_error(peer_address, result_id, error)
							continue # No reply to results

			except RPCDelayedReply as delayed_reply:
				delayed_reply._bind(self, s, peer_address, request_obj.get('id'))
				self.DelayedReplies[delayed_reply.Key] = delayed_reply
				return

			except RPCError as e:
				if propagate_error:
					error_obj = {
						"id": request_obj.get('id'),
						"jsonrpc": "2.0",
						"error": {
							"code": e.code,
							"message": e.message,
						}
					}
					if e.data is not None: error_obj['error']['data'] = e.data
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
			"id": request_id,
			"jsonrpc": "2.0",
			"method": method,
		}
		if params is not None:
			request_obj["params"] = params

		request_dgram = json.dumps(request_obj).encode('utf-8')
		request_cgram = self._encrypt(peer_address, request_dgram)
		x = self.PrimarySocket.sendto(request_cgram, peer_address)
		if x != len(request_cgram):
			L.error("Sent data are not complete ({} != {})".format(x, len(request_cgram)))
		return request_id


	async def acall(self, peer_address, method, params = None, *, timeout = None):
		'''
		This is awaitable call.
		'''

		class ACall(object):

			def __init__(self, rpc, peer_address, timeout):
				self.PeerAddress = peer_address
				self.RequestId = rpc.call(self.PeerAddress, method, params)
				self.ReplyEvent = asyncio.Event(loop=rpc.Loop)
				rpc.ACallRegister[self.RequestId] = self
				self.Result = None
				self.Error = None

				if timeout is None:
					# The default timeout is 3 seconds
					timeout = 3
				self.TimeoutAt = rpc.Loop.time() + timeout


			async def wait(self):
				await self.ReplyEvent.wait()
				if self.Error is not None:
					raise RPCError(
						code=self.Error.get('code'),
						message=self.Error.get('message'),
						data=self.Error.get('data')
					)
				if self.Result is asyncio.CancelledError:
					raise asyncio.CancelledError()
				if self.Result is asyncio.TimeoutError:
					raise asyncio.TimeoutError()
				return self.Result


			def result(self, peer_address, result):
				#assert(self.PeerAddress == peer_address)

				assert(self.Result is None)
				assert(self.Error is None)
				self.Result = result
				self.ReplyEvent.set()


			def error(self, peer_address, error):
				#assert(self.PeerAddress == peer_address)

				assert(self.Result is None)
				assert(self.Error is None)
				self.Error = error
				self.ReplyEvent.set()


			def cancel(self):
				if not self.ReplyEvent.is_set():
					self.Result = asyncio.CancelledError
					self.ReplyEvent.set()


			def timeout(self):
				if not self.ReplyEvent.is_set():
					self.Result = asyncio.TimeoutError
					self.ReplyEvent.set()				


		a = ACall(self, peer_address, timeout)
		return await a.wait()

	#

	def rpc_dispatch_method(self, peer_address, method, params):
		'''
		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": 19, "id": 1}

		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": -19, "id": 2}
		'''
		if method == "Ping":
			if params is None:
				return "Pong"
			else:
				return params

		m = self.RPCMethods.get(method)
		if m is not None:
			return m(peer_address, params)

		raise RPCError(-32601, "Method not found", data=method)


	def rpc_dispatch_result(self, peer_address, result_id, result):
		'''
		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": 19, "id": 1}

		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "subtract", "params": [23, 42], "id": 2}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "result": -19, "id": 2}
		'''

		acall = self.ACallRegister.pop(result_id, None)
		if acall is None:
			L.error("Received result for unknown method '{}'".format(result_id))
			return

		acall.result(peer_address, result)
		


	def rpc_dispatch_error(self, peer_address, result_id, error):
		'''
		rpc_dispatch_method --> {"jsonrpc": "2.0", "method": "foobar", "id": 1}
		rpc_dispatch_result <-- {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}
		'''

		acall = self.ACallRegister.pop(result_id, None)
		if acall is None:
			L.error("Received error '{}' for unknown method '{}'".format(error, result_id))
			return

		acall.error(peer_address, error)

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

		self.code = code
		self.message = message
		self.data = data

# 

class RPCDelayedReply(Exception):

	#TODO: Implement a timeout!

	def __init__(self, key):
		self.Key = key
		self.RPC = None
		self.Socket = None
		self.PeerAddress = None
		self.RequestId = None
		self.TimeoutAt = None


	def reply(self, *args, **kwargs):
		'''
		Overload this for an implementation of delayed reply
		'''
		return None


	def timeout(self):
		'''
		Called when timeout is reached
		'''
		L.warn("Timeout of the RCP deplayed reply '{}'".format(self.Key))


	def _bind(self, rpc, socket, peer_address, request_id, timeout=3.0):
		assert(self.RPC is None)
		assert(self.Socket is None)
		assert(self.PeerAddress is None)
		assert(self.RequestId is None)
		self.RPC = rpc
		self.Socket = socket
		self.PeerAddress = peer_address
		self.RequestId = request_id
		self.TimeoutAt = rpc.Loop.time() + timeout


	def execute(self, *args, **kwargs):
		result = self.reply(*args, **kwargs)
		if result is not None:
			result_obj = {
				"id": self.RequestId,
				"jsonrpc": "2.0",
				"result": result,
			}
			result_dgram = json.dumps(result_obj).encode('utf-8')
			result_cgram = self.RPC._encrypt(self.PeerAddress, result_dgram)
			self.Socket.sendto(result_cgram, self.PeerAddress)

