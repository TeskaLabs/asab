import logging
import asab

from .service import RaftService

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:raft': {
			'listen': '0.0.0.0 1711',  # Can be multiline
			'max_rpc_payload_size': 65507, # The maximum size of the RCP packet payload, the default is maximum UDP packet size
			'secret_key': 'mysixteenbytekey', # AES key must be either 16 (AES-128), 24 (AES-192), or 32 (AES-256) bytes long
			'server': False,
			'server_id': '', # If empty, construct name from hostname and a port
			'discovery': '', # Can be multiline
			'heartbeat_timeout': 750, # miliseconds, needs to be lower than election_timeout_min (aka half)
			'election_timeout_min': 1500, # miliseconds
			'election_timeout_max': 3000, # miliseconds
			'webapi': False,
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = RaftService(app, "asab.RaftService")
