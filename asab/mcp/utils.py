
def rpccall_ping(*args, **kwargs):
	"""
	MCP ping method - health check endpoint.
	Returns an empty result to confirm the server is alive and responsive.

	https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/ping
	"""
	return {}


def prune_nulls(value):
	"""
	Recursively remove keys with value None, list items that are None,
	and any empty dicts/lists that become empty as a result.
	"""
	if isinstance(value, dict):
		pruned = {}
		for key, item in value.items():
			if item is None:
				continue
			if key.startswith("_"):
				continue
			cleaned = prune_nulls(item)
			if cleaned is None:
				continue
			if isinstance(cleaned, (dict, list)) and len(cleaned) == 0:
				continue
			pruned[key] = cleaned
		return pruned

	if isinstance(value, list):
		pruned_items = []
		for item in value:
			if item is None:
				continue
			cleaned = prune_nulls(item)
			if cleaned is None:
				continue
			if isinstance(cleaned, (dict, list)) and len(cleaned) == 0:
				continue
			pruned_items.append(cleaned)
		return pruned_items

	return value
