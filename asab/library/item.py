import dataclasses
import typing


@dataclasses.dataclass
class LibraryItem:
	"""
	The data class that contains the info about a specific item in the library.

	Attributes:
		name (str): The absolute path of the Item. It can be directly fed into `LibraryService.read(...)`.
		type (str): Can be either `dir` if the Item is a directory or `item` if Item is of any other type.
		layer (int): The number of highest layer in which this Item is found. The higher the number, the lower the layer is.
		providers (list): List of `LibraryProvider` objects containing this Item.
		disabled (bool): `True` if the Item is disabled, `False` otherwise. If the Item is disabled, `LibraryService.read(...)` will return `None`.
		override (int): If `True`, this item is marked as an override for the providers with the same Item name.
	"""

	name: str
	type: str
	layer: int
	providers: list
	disabled: bool = False
	override: int = 0  # Default value for override is False
	version: typing.Optional[int] = None  # New version field
