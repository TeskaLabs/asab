import dataclasses
import typing


@dataclasses.dataclass
class LibraryItem:
    """
    The data class that contains the info about a specific item in the library.

    Attributes:
        name (str): The absolute path of the Item. It can be directly fed into `LibraryService.read(...)`.
        type (str): Can be either `dir` if the Item is a directory or `item` if Item is of any other type.
        layers (list[str]): Identifiers of layers in which this item was found.
        Examples only as strings, e.g. "0", "1", "0:global", "0:tenant", "0:personal".
        providers (list): List of `LibraryProvider` objects containing this Item.
        disabled (bool): `True` if the Item is disabled, `False` otherwise. If the Item is disabled, `LibraryService.read(...)` will return `None`.
        favorite (bool): True if the Item is marked as a favorite.
        override (int): If `True`, this item is marked as an override for the providers with the same Item name.
    """
    name: str
    type: str
    layers: typing.List[str]
    providers: list
    disabled: bool = False
    favorite: bool = False
    override: int = 0
    size: typing.Optional[int] = None  # Size is None by default, absent for directories
