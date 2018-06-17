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
			'heartbeat_timeout': 75, # miliseconds, needs to be significantly lower than election_timeout_min
			'election_timeout_min': 150, # miliseconds
			'election_timeout_max': 300, # miliseconds
			'server_id': '', # If empty, construct name from hostname and a port
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = RaftService(app, "asab.RaftService")
