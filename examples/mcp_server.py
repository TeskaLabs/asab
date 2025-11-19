#!/usr/bin/env python3
import asab
import asab.web
import asab.mcp


class MyMCPServerApplication(asab.Application):

	def __init__(self):
		super().__init__()

		# Create the Web server
		web = asab.web.create_web_server(self, api=True)

		# Add the MCP service, it will be used to register tools and resources
		self.MCPService = asab.mcp.MCPService(self, web)

		# Add the hello world tool
		self.MCPService.add_tool(self.tool_hello_world)


	@asab.mcp.mcp_tool(
		name="hello_world",
		title="Hello world",
		description="""
			Says hello to the given name.

			Args:
				name: The name to greet

			Returns:
				A string with the greeting
		""",
		inputSchema={
			"type": "object",
			"properties": {
				"name": {"type": "string"}
			}
		}
	)
	async def tool_hello_world(self, name: str):
		'''
		Hello world tool, this method is exposed to the MCP client.

		Args:
			name: The name to greet

		Returns:
			A string with the greeting
		'''
		return "Hello, {}!".format(name)


if __name__ == '__main__':
	app = MyMCPServerApplication()
	app.run()
