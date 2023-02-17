from .doc_web_handler_class import TestDocWebHandler
from .swagger_template import SWAGGER_TEMPLATE


class TestSwagger(TestDocWebHandler):

	def test_base_keys(self):
		"""Documentation should contain these keys:
'openapi', 'info', 'servers', 'paths', 'components'
		"""
		documentation: dict = self.handlerObject.build_swagger_documentation()
		keys = ["openapi", "info", "servers", "paths", "components"]
		self.assertTrue(check_keys(documentation, keys))

	def test_document_structure_keys(self):
		documentation: dict = self.handlerObject.build_swagger_documentation()
		self.assertTrue(compare_keys(documentation, SWAGGER_TEMPLATE))


def check_keys(dictionary: dict, keys: list) -> bool:
	return set(keys) == set(dictionary.keys())


def compare_keys(dict1, dict2):
	"Check if both dicts contain the same keys (recursively)"
	if set(dict1.keys()) != set(dict2.keys()):
		return False

	# Recursively check the keys of nested dictionaries
	for key in dict1.keys():
		if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
			if not compare_keys(dict1[key], dict2[key]):
				return False

	return True
