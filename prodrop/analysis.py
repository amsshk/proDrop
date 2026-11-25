"""Daily analysis: turns catalogue items into profit recommendations.

Pure Python. The ERPNext job will pass in real data and a real freight fetcher.
Recommends only. Never changes prices, pauses products or places orders.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from prodrop.profit import Economics, assess_product, assess_warehouse_stock

LIVE_CJ = "Live CJ"
CONFIGURED = "Configured estimate"
PROADS = "ProAds"


@dataclass(frozen=True)
class Item:
	product: str
	vid: str
	variant_price_usd: float  # CJ variantSellPrice, the supplier cost
	factory_units: Optional[int]
	warehouse_units: Optional[int]  # None means stock format not yet confirmed; check skipped
	selling_price_aed: float


@dataclass(frozen=True)
class Settings:
	fx_usd_to_aed: float
	payment_fee_pct: float
	refund_rate_pct: float  # estimate until real refund data exists
	ad_spend_per_sale_aed: float  # configured estimate unless ProAds data is supplied
	shipping_fallback_usd: float  # used only when the live quote fails, and labelled as such


@dataclass(frozen=True)
class FreightResult:
	shipping_usd: float
	quoted_at: str


def run_analysis(items: list[Item], settings: Settings,
                 fetch_freight: Callable[[str], Optional[FreightResult]],
                 now: str, ad_spend_by_product: Optional[dict] = None) -> list[dict]:
	"""Return recommendation dicts, each with data sources and timestamps recorded."""
	ad_spend_by_product = ad_spend_by_product or {}
	out = []
	for it in items:
		freight = fetch_freight(it.vid)
		if freight is not None:
			shipping_usd, freight_source, freight_time = freight.shipping_usd, LIVE_CJ, freight.quoted_at
		else:
			shipping_usd, freight_source, freight_time = settings.shipping_fallback_usd, CONFIGURED, now

		if it.product in ad_spend_by_product:
			ad_aed, ad_source = ad_spend_by_product[it.product], PROADS
		else:
			ad_aed, ad_source = settings.ad_spend_per_sale_aed, CONFIGURED

		econ = Economics(
			selling_price=it.selling_price_aed,
			supplier_cost=round(it.variant_price_usd * settings.fx_usd_to_aed, 2),
			shipping=round(shipping_usd * settings.fx_usd_to_aed, 2),
			payment_fee_pct=settings.payment_fee_pct,
			refund_rate_pct=settings.refund_rate_pct,
			ad_spend_per_sale=ad_aed,
		)
		sources = {
			"supplier_cost": {"source": LIVE_CJ, "retrieved_at": now},
			"shipping": {"source": freight_source, "retrieved_at": freight_time},
			"ad_spend": {"source": ad_source, "retrieved_at": now},
			"refund_rate": {"source": CONFIGURED, "retrieved_at": now},
		}
		checks = [assess_product(it.product, econ)]
		if it.warehouse_units is not None:
			checks.append(assess_warehouse_stock(it.product, it.factory_units or 0, it.warehouse_units))
		for rec in checks:
			if rec is None:
				continue
			rec.evidence["data_sources"] = sources
			rec.evidence["calculated_at"] = now
			out.append(rec.as_dict())
	return out


def drop_already_pending(recs: list[dict], pending: set[tuple[str, str]]) -> list[dict]:
	"""Remove recommendations that already have a Pending record for the same product and type.

	pending holds (product, kind) pairs taken from existing Pending recommendations.
	"""
	return [r for r in recs if (r["product"], r["kind"]) not in pending]


def split_pending(recs: list[dict], pending: dict[tuple[str, str], str]) -> tuple[list[dict], list[tuple[str, dict]]]:
	"""Split recommendations into new ones and updates to existing Pending records.

	pending maps (product, kind) to the existing record's name.
	Returns (to_create, [(record_name, rec), ...]).
	"""
	to_create, to_update = [], []
	for r in recs:
		name = pending.get((r["product"], r["kind"]))
		if name:
			to_update.append((name, r))
		else:
			to_create.append(r)
	return to_create, to_update
