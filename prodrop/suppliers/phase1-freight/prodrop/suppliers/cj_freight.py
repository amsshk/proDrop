"""CJ freight quote helper. Builds the request and reads the response; no network code here.

Endpoint: /logistic/freightCalculateTip (uses weight, so more accurate than the simple quote).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FreightQuote:
	shipping_usd: float
	method: str
	delivery_days: str
	quoted_at: str  # ISO timestamp the quote was taken


def build_tip_request(vid: str, weight_g: float, dest_country: str, quantity: int = 1,
                      src_country: str = "CN", product_prop: str = "ORDINARY_PRODUCT") -> dict:
	"""Payload for freightCalculateTip. Weight must be above zero or CJ returns 1600300."""
	if weight_g <= 0:
		raise ValueError("weight must be greater than 0")
	if not vid or not dest_country:
		raise ValueError("vid and destination country are required")
	return {
		"reqDTOS": [
			{
				"srcAreaCode": src_country,
				"destAreaCode": dest_country,
				"productProp": product_prop,
				"weight": weight_g,
				"products": [{"vid": vid, "quantity": quantity}],
			}
		]
	}


def pick_cheapest(options: list[dict]) -> FreightQuote | None:
	"""Choose the cheapest usable shipping option. Skips entries without a price."""
	usable = [o for o in options if o.get("price") not in (None, "", 0)]
	if not usable:
		return None
	best = min(usable, key=lambda o: float(o["price"]))
	return FreightQuote(
		shipping_usd=round(float(best["price"]), 2),
		method=best.get("logisticName", ""),
		delivery_days=str(best.get("logisticAging", "")),
		quoted_at=best.get("quoted_at", ""),
	)
