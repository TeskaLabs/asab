import dataclasses


@dataclasses.dataclass
class MCPToolInfo:
	name: str
	title: str
	description: str
	inputSchema: dict
	outputSchema: dict


@dataclasses.dataclass
class MCPToolResult:
	pass


@dataclasses.dataclass
class MCPToolResultTextContent(MCPToolResult):
	'''
	https://modelcontextprotocol.io/specification/2025-06-18/server/tools#text-content
	'''
	text: str


@dataclasses.dataclass
class MCPToolResultResourceLink(MCPToolResult):
	'''
	https://modelcontextprotocol.io/specification/2025-06-18/server/tools#resource-links
	'''
	uri: str
	name: str
	description: str
	mimeType: str
	title: str = None  # For resource listing
	# TODO: Resource annotations


@dataclasses.dataclass
class MCPResourceTemplateInfo:
	_uriPrefix: str
	uriTemplate: str
	name: str
	title: str
	description: str
	mimeType: str
