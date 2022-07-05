import dataclasses


@dataclasses.dataclass
class LibraryItem:
	name: str
	type: str
	providers: list
	disabled: bool = False
