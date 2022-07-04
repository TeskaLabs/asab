import logging

from ..config import Config
from .service import LibraryService

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'library': {
			'path': 'zk:///library'
		}
	}
)

__all__ = [
	"LibraryService",
]
