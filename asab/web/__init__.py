import logging
import asab

from .service import WebService
from .websocket import WebSocketFactory

#

L = logging.getLogger(__name__)

#

asab.Config.add_defaults(
	{
		'asab:web': {
			'listen': '0.0.0.0 8080', # Can be multiline
			'rootdir': '',
			'servertokens': 'full' # Controls whether 'Server' response header field is included ('full') or faked 'prod' ()
		}
	}
)


class Module(asab.Module):

	def __init__(self, app):
		super().__init__(app)
		self.service = WebService(app, "asab.WebService")
