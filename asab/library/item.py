import dataclasses


@dataclasses.dataclass
class LibraryItem:
    '''
    The data class that contains the info about a specific item in the library.

    * `name` is the full name and path of the item.
      It MUST start with `/` and contain the whole absolute path.
      The `name` can be directly fed into `LibraryService.read(...)`.

    * `type` is `item` or `dir`.

    * `layer` is an integer indicating the level of the provider that provides this item.
      A higher number indicates a higher level of the provider in the library hierarchy.

    * `providers` is a list of providers that provide this item.
      `dir` LibraryItems can be provided by more than one provider.

    * `disabled` if True, then this item is disabled and `LibraryService.read(...)` will return `None`.

    * `override` if True, then this item is marked as an override for the providers with the same item name.
    '''


    name: str
    type: str
    layer: int
    providers: list
    disabled: bool = False
    override: bool = False  # Default value for override is False
