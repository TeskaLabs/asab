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
			'peers': '', # Can be multiline
			'discovery': '', # Can be multiline
			'heartbeat_timeout': 500, # miliseconds, needs to be significantly lower than election_timeout_min
			'election_timeout_min': 1800, # miliseconds
			'election_timeout_max': 2200, # miliseconds
			'server_id': '', # If empty, construct name from hostname and a port
			'webapi': False,
			'max_rpc_payload_size': 65507, # The maximum size of the RCP packet payload, the default is maximum UDP packet size
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = RaftService(app, "asab.RaftService")
