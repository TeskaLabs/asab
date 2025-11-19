import logging
import dataclasses

import asab

import aiohttp_rpc

from .utils import rpc_ping, prune_nulls
from .datacls import MCPToolResultTextContent, MCPToolResultResourceLink


L = logging.getLogger(__name__)


class MCPService(asab.Service):

	def __init__(self, app, web, service_name="asab.MCPService"):
		super().__init__(app, service_name)

		self.Tools = {}
		self.ResourceTemplates = {}
		self.ResourceLists = {}

		self.RPCServer = aiohttp_rpc.JsonRpcServer(middlewares=[logging_middleware])
		web.add_post(r'/{tenant}/mcp', self._handle_http_request)

		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(self._rpc_mcp_initialize, name="initialize"))
		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(self._rpc_notifications_initialized, name="notifications/initialized"))
		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(rpc_ping, name="ping"))

		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(self._rcp_tools_list, name="tools/list"))
		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(self._rpc_tools_call, name="tools/call"))

		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(self._rpc_resources_list, name="resources/list"))
		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(self._rpc_resources_read, name="resources/read"))

		self.RPCServer.add_method(aiohttp_rpc.JsonRpcMethod(self._rpc_resource_templates_list, name="resources/templates/list"))


	def add_tool(self, tool_function, mcp_tool_info=None):
		if mcp_tool_info is None and hasattr(tool_function, '_mcp_tool_info'):
			mcp_tool_info = tool_function._mcp_tool_info

		if mcp_tool_info is None:
			raise ValueError("MCP tool info is required")

		self.Tools[mcp_tool_info.name] = (tool_function, mcp_tool_info)


	def add_resource_template(self, resource_template_function, mcp_resource_template_info=None):
		if mcp_resource_template_info is None and hasattr(resource_template_function, '_mcp_resource_template_info'):
			mcp_resource_template_info = resource_template_function._mcp_resource_template_info

		if mcp_resource_template_info is None:
			raise ValueError("MCP resource template info is required")

		self.ResourceTemplates[mcp_resource_template_info.name] = (resource_template_function, mcp_resource_template_info)


	def add_resource_list(self, resource_uri_prefix, resource_list_function):
		self.ResourceLists[resource_uri_prefix] = resource_list_function


	async def _handle_http_request(self, request):
		# TODO: Handle tenant and authorization
		return await self.RPCServer.handle_http_request(request)


	async def _rpc_mcp_initialize(self, capabilities=None, clientInfo=None, *args, **kwargs):
		capabilities = capabilities or {}
		clientInfo = clientInfo or {}

		L.log(asab.LOG_NOTICE, "MCP Client initializing", struct_data={
			"name": clientInfo.get('name', 'unknown'),
			"version": clientInfo.get('version', 'unknown'),

		})

		capabilities = {}
		if len(self.Tools) > 0:
			capabilities['tools'] = {
				'listChanged': True,
			}

		if len(self.ResourceTemplates) > 0 or len(self.ResourceLists) > 0:
			capabilities['resources'] = {
				'listChanged': True,
			}

		return {
			"protocolVersion": "2024-11-05",
			"serverInfo": {
				"name": "asab-mcp",
				"version": "25.11.0",
			},
			"instructions": (
				"ASAB MCP server is ready."
			),
			"capabilities": capabilities,
		}


	async def _rcp_tools_list(self, *args, **kwargs):
		'''
		To discover available tools, clients send a tools/list request.

		https://modelcontextprotocol.io/specification/2025-06-18/server/tools#listing-tools
		'''
		# TODO: Pagination ...
		return {
			"tools": [
				prune_nulls(dataclasses.asdict(mcp_tool_info))
				for _, mcp_tool_info in self.Tools.values()
			],
		}


	async def _rpc_tools_call(self, name, arguments, *args, **kwargs):
		'''
		To invoke a tool, clients send a tools/call request.

		https://modelcontextprotocol.io/specification/2025-06-18/server/tools#invoking-tools
		'''

		x = self.Tools.get(name)
		if x is None:
			L.warning("Tool not found", struct_data={"name": name})
			raise KeyError(f"Tool {name} not found")

		tool_function, _ = x

		try:
			result = await tool_function(**arguments)
		except Exception as e:
			L.exception("Tool failed", struct_data={"name": name, "error": str(e)})
			return {
				"content": [{
					"type": "text",
					"text": "General error occurred."
				}],
				"isError": True,
			}

		if not isinstance(result, list):
			result = [result]

		transformed_result = []
		for item in result:
			if isinstance(item, MCPToolResultTextContent):
				transformed_result.append({
					"type": "text",
					"text": item.text,
				})
			elif isinstance(item, str):
				# A shortcut for Text content.
				transformed_result.append({
					"type": "text",
					"text": item,
				})
			elif isinstance(item, MCPToolResultResourceLink):
				transformed_result.append({
					"type": "resource_link",
					"uri": item.uri,
					"name": item.name,
					"description": item.description,
					"mimeType": item.mimeType,
				})
			else:
				raise ValueError(f"Unsupported result type: {type(item)}")

		return {
			"content": transformed_result,
			"isError": False,
		}


	async def _rpc_resources_list(self, *args, **kwargs):
		'''
		To list resources, clients send a resources/list request.

		https://modelcontextprotocol.io/specification/2025-06-18/server/resources#listing-resources
		'''
		resources = []

		for _, resource_list_function in self.ResourceLists.items():
			resources.extend(await resource_list_function())

		transformed_resources = []
		for resource in resources:
			if isinstance(resource, MCPToolResultResourceLink):
				transformed_resources.append(prune_nulls({
					"uri": resource.uri,
					"name": resource.name,
					"title": resource.title,
					"description": resource.description,
					"mimeType": resource.mimeType,
				}))
			else:
				raise ValueError(f"Unsupported resource type: {type(resource)}")

		return {
			"resources": transformed_resources,
		}


	async def _rpc_resources_read(self, uri, *args, **kwargs):
		'''
		To read a resource, clients send a resources/read request.

		https://modelcontextprotocol.io/specification/2025-06-18/server/resources#reading-resources
		'''
		fnct = None

		# TODO: Check the "direct"

		# Find the resource template function that matches the URI
		if fnct is None:
			for resource_template_function, mcp_resource_template_info in self.ResourceTemplates.values():
				if uri.startswith(mcp_resource_template_info._uriPrefix):
					fnct = resource_template_function
					break

		if fnct is None:
			# TODO: Find a more compliant way to handle this, but for now we'll just raise an error.
			raise KeyError(f"Resource template {uri} not found")

		result = await fnct(uri)
		if result is None:
			return {
				"contents": [],
			}

		if not isinstance(result, list):
			result = [result]

		return {
			"contents": result,
		}


	async def _rpc_resource_templates_list(self, *args, **kwargs):
		'''
		To discover available resource templates, clients send a resources/templates/list request.

		https://modelcontextprotocol.io/specification/2025-06-18/server/resources#resource-templates
		'''
		# TODO: Pagination ...
		return {
			"resourceTemplates": [
				prune_nulls(dataclasses.asdict(mcp_resource_template_info))
				for _, mcp_resource_template_info in self.ResourceTemplates.values()
			],
		}


	async def _rpc_notifications_initialized(self, *args, **kwargs):
		"""
		This notification is sent from the client to the server after initialization has finished.

		https://modelcontextprotocol.io/specification/2025-06-18/schema#notifications%2Finitialized
		"""
		L.log(asab.LOG_NOTICE, "MCP Client initialized")
		return {}


async def logging_middleware(request, handler):
	response = await handler(request)
	if response.error is None:
		L.log(asab.LOG_NOTICE, "JSON-RPC request completed", struct_data={"method": request.method_name})
	else:
		L.warning("JSON-RPC request failed", struct_data={
			"method": request.method_name,
			"error": response.error.message,
		})
	return response
