"""Scheduled jobs and manual runs.

run_analysis_now() is safe to run by hand. It creates Pending recommendations only.
Nothing here changes prices, pauses products or places orders.
The daily schedule stays off in hooks.py until a manual run has been reviewed.
"""

import json

import frappe
import requests

from prodrop.analysis import FreightResult, Item, Settings, rule_of, run_analysis, split_pending, stock_totals
from prodrop.suppliers.cj import CJClient, BASE_URL
from prodrop.suppliers.cj_freight import build_tip_request, pick_cheapest

DEFAULT_REFUND_RATE_PCT = 0.0  # no refund data yet; labelled as a configured estimate


def _load_settings():
	s = frappe.get_single("ProDrop Pricing Settings")
	return Settings(
		fx_usd_to_aed=float(s.exchange_rate or 0),
		payment_fee_pct=float(s.payment_fee_percent or 0),
		refund_rate_pct=DEFAULT_REFUND_RATE_PCT,
		ad_spend_per_sale_aed=float(s.advertising_cost or 0),
		shipping_fallback_usd=float(s.shipping_cost or 0),
	)


def _freight_fetcher(client, now):
	def fetch(vid):
		try:
			body = build_tip_request(vid, weight_g=50, dest_country="AE")
			data = client._request("POST", "/logistic/freightCalculateTip", json=body)
			quote = pick_cheapest(data or [])
			if quote is None:
				return None
			return FreightResult(shipping_usd=quote.shipping_usd, quoted_at=now)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "proDrop freight quote")
			return None
	return fetch


def run_analysis_now():
	"""Run the analysis for every enabled tracked product. Returns the number of recommendations created."""
	frappe.only_for("System Manager")
	now = frappe.utils.now_datetime().isoformat()
	settings = _load_settings()
	client = CJClient(frappe.get_single("CJ Settings").get_password("api_key"))

	items = []
	for t in frappe.get_all("ProDrop Tracked Product", filters={"enabled": 1},
	                        fields=["pid", "vid", "product_name", "selling_price_aed"]):
		variants = client.list_variants(t.pid) or []
		match = next((v for v in variants if v.get("vid") == t.vid), None)
		if not match or not match.get("variantSellPrice"):
			frappe.log_error(f"No price for variant {t.vid}", "proDrop analysis")
			continue
		factory_units, warehouse_units = stock_totals(client.get_stock(t.vid))
		items.append(Item(
			product=t.product_name or t.vid,
			vid=t.vid,
			variant_price_usd=float(match["variantSellPrice"]),
			factory_units=factory_units,
			warehouse_units=warehouse_units,
			selling_price_aed=float(t.selling_price_aed),
		))

	recs = run_analysis(items, settings, _freight_fetcher(client, now), now)
	pending = {
		(r.product, r.kind, rule_of(r.evidence)): r.name
		for r in frappe.get_all("ProDrop Recommendation", filters={"status": "Pending"},
		                        fields=["name", "product", "kind", "evidence"])
	}
	to_create, to_update = split_pending(recs, pending)
	for name, r in to_update:
		doc = frappe.get_doc("ProDrop Recommendation", name)
		doc.update({
			"signal": r["signal"],
			"reasoning": r["reasoning"],
			"expected_impact": r["expected_impact"],
			"evidence": json.dumps(r["evidence"], indent=1),
		})
		doc.save(ignore_permissions=True)
	for r in to_create:
		frappe.get_doc({
			"doctype": "ProDrop Recommendation",
			"kind": r["kind"],
			"product": r["product"],
			"signal": r["signal"],
			"reasoning": r["reasoning"],
			"expected_impact": r["expected_impact"],
			"evidence": json.dumps(r["evidence"], indent=1),
			"status": "Pending",
		}).insert(ignore_permissions=True)
	frappe.db.commit()
	return len(to_create) + len(to_update)


def refresh_trends():
	"""Placeholder: trend scoring is not scheduled yet."""
	pass


def sync_supplier_stock():
	"""Placeholder: stock sync is not scheduled yet."""
	pass


@frappe.whitelist()
def decide_recommendation(name, decision, notes=None):
	"""Approve or reject a Pending recommendation and record why.

	This only records the decision. It does not change prices, listings or orders.
	"""
	from prodrop.analysis import can_transition

	frappe.only_for("System Manager")
	if decision not in ("Approved", "Rejected"):
		frappe.throw("Decision must be Approved or Rejected.")
	if not (notes or "").strip():
		frappe.throw("Write a short note explaining your decision.")

	doc = frappe.get_doc("ProDrop Recommendation", name)
	if not can_transition(doc.status, decision):
		frappe.throw(f"Cannot change a {doc.status} recommendation to {decision}.")

	doc.status = decision
	doc.decision_notes = notes.strip()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.status
