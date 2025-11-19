from .datacls import MCPToolInfo, MCPResourceTemplateInfo


def mcp_tool(name, title, description, inputSchema=None, outputSchema=None):
	def decorator(func):
		func._mcp_tool_info = MCPToolInfo(
			name=name.strip(),
			title=title.strip(),
			description=description.strip(),
			inputSchema=inputSchema,
			outputSchema=outputSchema,
		)
		return func
	return decorator


def mcp_resource_template(uri_prefix: str, uri_template: str, name: str, title: str, description: str, mimeType: str):
	def decorator(func):
		func._mcp_resource_template_info = MCPResourceTemplateInfo(
			uriTemplate=uri_template,
			_uriPrefix=uri_prefix,
			name=name.strip(),
			title=title.strip(),
			description=description.strip(),
			mimeType=mimeType,
		)
		return func
	return decorator
