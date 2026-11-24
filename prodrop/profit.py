"""Phase 1 profit intelligence: net profit after every cost, plus recommendation records.

Pure Python (no Frappe imports) so it runs and tests without a bench.
Nothing here moves money or changes prices. It only scores and recommends.
"""

from dataclasses import dataclass, field, asdict

MIN_NET_MARGIN_PCT = 15.0  # below this, a product is flagged as not worth selling


@dataclass(frozen=True)
class Economics:
	selling_price: float
	supplier_cost: float  # landed cost in selling currency
	shipping: float
	payment_fee_pct: float
	refund_rate_pct: float  # share of orders expected to be refunded
	ad_spend_per_sale: float  # advertising cost attributed to one sale

	def expected_net_profit(self) -> float:
		"""Expected profit per order, counting refunds as lost revenue and lost cost."""
		fee = self.selling_price * self.payment_fee_pct / 100
		kept_share = 1 - self.refund_rate_pct / 100
		revenue = self.selling_price * kept_share
		costs = self.supplier_cost + self.shipping + self.ad_spend_per_sale + fee
		return round(revenue - costs, 2)

	def net_margin_pct(self) -> float:
		if self.selling_price <= 0:
			return 0.0
		return round(self.expected_net_profit() / self.selling_price * 100, 2)


@dataclass
class Recommendation:
	kind: str  # "pricing", "supplier_switch", "pause_product", "cash_hold"
	product: str
	signal: str  # what was detected
	reasoning: str  # why this action is suggested
	expected_impact: float  # expected change in profit per order
	status: str = "Pending"  # Pending, Approved, Rejected, Verified
	evidence: dict = field(default_factory=dict)

	def as_dict(self) -> dict:
		return asdict(self)


def assess_product(product: str, econ: Economics) -> Recommendation | None:
	"""Recommend a pause when expected net margin is too thin. Returns None if the product is fine."""
	margin = econ.net_margin_pct()
	if margin >= MIN_NET_MARGIN_PCT:
		return None
	return Recommendation(
		kind="pause_product",
		product=product,
		signal=f"Expected net margin {margin}% is below {MIN_NET_MARGIN_PCT}%",
		reasoning="After shipping, payment fees, refunds and ad cost, this product keeps too little per sale.",
		expected_impact=round(-econ.expected_net_profit(), 2),
		evidence={"net_margin_pct": margin, "net_profit_per_order": econ.expected_net_profit()},
	)


def assess_warehouse_stock(product: str, factory_units: int, warehouse_units: int) -> Recommendation | None:
	"""Flag a variant that has factory stock but none in the warehouse that ships to customers."""
	if warehouse_units > 0:
		return None
	return Recommendation(
		kind="pause_product",
		product=product,
		signal=f"0 warehouse units (factory has {factory_units})",
		reasoning="Orders for this variant cannot ship from the warehouse, so they would stall.",
		expected_impact=0.0,
		evidence={"factory_units": factory_units, "warehouse_units": warehouse_units},
	)


def cash_hold(available_cash: float, pending_supplier_cost: float, ad_budget_today: float, reserve: float) -> Recommendation | None:
	"""Hold new orders when cash cannot cover pending supplier payments, ad spend and the refund reserve."""
	needed = pending_supplier_cost + ad_budget_today + reserve
	if available_cash >= needed:
		return None
	return Recommendation(
		kind="cash_hold",
		product="(store)",
		signal=f"Cash {available_cash} is below needed {needed}",
		reasoning="Taking more orders now could leave supplier payments or ad spend unfunded.",
		expected_impact=round(available_cash - needed, 2),
		evidence={"available_cash": available_cash, "needed": needed, "reserve": reserve},
)
