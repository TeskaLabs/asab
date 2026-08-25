import logging

from ..config import Config
from .service import LibraryService
from ..utils import get_source_id

#

L = logging.getLogger(__name__)

#

Config.add_defaults(
	{
		'library': {
			'providers': './library'
		}
	}
)

__all__ = [
	"LibraryService",
	"get_source_id",
]
