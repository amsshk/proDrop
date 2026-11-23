"""CJ Dropshipping connector (stub).

Not implemented yet: wire each method to CJ's official API documentation,
then test against a sandbox account before enabling the scheduler jobs.
"""


class CJClient:
	def __init__(self, api_key: str):
		self.api_key = api_key

	def search_products(self, keyword: str) -> list[dict]:
		raise NotImplementedError

	def get_stock(self, sku: str) -> int:
		raise NotImplementedError

	def place_order(self, order: dict) -> str:
		"""Place a supplier order and return the supplier's order id."""
		raise NotImplementedError
