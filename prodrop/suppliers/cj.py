"""CJ Dropshipping connector.

Endpoints and auth follow CJ's API 2.0 docs (developers.cjdropshipping.com).
Check field names on your first live call; CJ changes them from time to time.
"""

import time

import requests

BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"
TIMEOUT = 30


class CJError(Exception):
	pass


class CJClient:
	def __init__(self, api_key: str, platform_token: str | None = None):
		self.api_key = api_key
		self.platform_token = platform_token
		self._token = None
		self._token_expires = 0.0

	def _access_token(self) -> str:
		if self._token and time.time() < self._token_expires:
			return self._token
		data = self._request("POST", "/authentication/getAccessToken", json={"apiKey": self.api_key}, auth=False)
		token = (data or {}).get("accessToken")
		if not token:
			raise CJError("CJ did not return an access token")
		self._token = token
		self._token_expires = time.time() + 23 * 3600  # CJ tokens last 24 hours
		return token

	def _request(self, method: str, path: str, params=None, json=None, auth: bool = True):
		headers = {}
		if auth:
			headers["CJ-Access-Token"] = self._access_token()
			if self.platform_token:
				headers["platformToken"] = self.platform_token
		response = requests.request(
			method, BASE_URL + path, params=params, json=json, headers=headers, timeout=TIMEOUT
		)
		response.raise_for_status()
		body = response.json()
		if body.get("code") != 200 or not body.get("result", True):
			raise CJError(body.get("message") or "CJ request failed")
		return body.get("data")

	def list_products(self, page: int = 1, category_id: str | None = None, sku: str | None = None):
		"""Browse CJ products (20 per page). Filters: category id or product SKU."""
		params = {"pageNum": page}
		if category_id:
			params["categoryId"] = category_id
		if sku:
			params["productSku"] = sku
		return self._request("GET", "/product/list", params=params)

	def get_stock(self, vid: str):
		"""Stock for one CJ variant id. Returns CJ's raw data."""
		return self._request("GET", "/product/stock/queryByVid", params={"vid": vid})

	def place_order(self, order: dict) -> str:
		"""Create a CJ order (Create Order V2) and return its CJ order id.

		`order` is sent as-is. Build it from CJ's Create Order V2 docs: customer
		name and address, fromCountryCode, logistics, and products [{vid, quantity}].
		The order is created unpaid: CJ still needs payment before it ships.
		"""
		data = self._request("POST", "/shopping/order/createOrderV2", json=order)
		return (data or {}).get("orderId")

	def get_order(self, order_id: str):
		"""Order details, including orderStatus (CREATED, UNPAID, UNSHIPPED, SHIPPED...)."""
		return self._request("GET", "/shopping/order/getOrderDetail", params={"orderId": order_id})
