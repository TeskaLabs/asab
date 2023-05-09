import dataclasses


@dataclasses.dataclass
class LibraryItem:
    '''
    The data class that contains the info about specific item in the library.

    * `name` is full name and path of the item.
    It MUST start with `/` and contains the whole absolute path.
    The `name` can be directly fed into `LibraryService.read(...)`.

    * `type` is `item` or `dir`

    * `providers` is a list of providers that provide this item.
    `dir` LibaryItems can be provided by more than one provider.

    * `disabled` if True, then this item is disabled. `LibraryService.read(...)` will return `None`.

    * `override` if True, then this item is marked as override for the providers with the same item name.
    '''

    name: str
    type: str
    layer: int
    providers: list
    disabled: bool = False
    override: bool = False  # Default value for override is False

    def __post_init__(self):
        if self.layer == 0:
            self.override = True

