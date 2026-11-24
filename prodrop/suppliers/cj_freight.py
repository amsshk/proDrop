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
	"""Verified against the live API: productProp must be a list, items go in freightTrialSkuList."""
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
				"productProp": [product_prop],
				"weight": weight_g,
				"freightTrialSkuList": [{"vid": vid, "quantity": quantity}],
			}
		]
	}


def shipping_charge(option: dict) -> float | None:
	"""Total shipping charge in USD. totalPostageFee is the full amount; discountFee is the fallback."""
	if option.get("error"):
		return None
	for key in ("totalPostageFee", "discountFee"):
		value = option.get(key)
		if value not in (None, "", 0):
			return round(float(value), 2)
	return None


def pick_cheapest(options: list[dict]) -> FreightQuote | None:
	"""Cheapest usable option. Skips options with an error or no charge."""
	priced = [(shipping_charge(o), o) for o in options]
	priced = [(price, o) for price, o in priced if price is not None]
	if not priced:
		return None
	price, best = min(priced, key=lambda pair: pair[0])
	return FreightQuote(
		shipping_usd=price,
		method=best.get("option", {}).get("enName", ""),
		delivery_days=str(best.get("arrivalTime", "")),
		quoted_at=best.get("quoted_at", ""),
	)
