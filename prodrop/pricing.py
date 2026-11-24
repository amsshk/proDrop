"""proDrop automated pricing engine."""

import frappe
from frappe.utils import flt


def _settings():
    frappe.only_for("System Manager")
    return frappe.get_single("ProDrop Pricing Settings")


def _calculate(supplier_cost, category=None):
    settings = _settings()

    rate = flt(settings.exchange_rate)
    margin = flt(settings.default_margin)
    fee = flt(settings.payment_fee_percent)

    if rate <= 0:
        frappe.throw("Configure a valid exchange rate.")

    rule = None
    if category:
        rule_name = frappe.db.get_value(
            "ProDrop Category Pricing Rule",
            {"category_name": category, "enabled": 1},
            "name"
        )
        if rule_name:
            rule = frappe.get_doc("ProDrop Category Pricing Rule", rule_name)

    shipping = flt(settings.shipping_cost)
    packaging = flt(settings.packaging_cost)
    other = flt(settings.other_cost)
    advertising = flt(settings.advertising_cost)

    if rule:
        if rule.margin_percent:
            margin = flt(rule.margin_percent)
        if rule.payment_fee_percent:
            fee = flt(rule.payment_fee_percent)
        if rule.shipping_cost:
            shipping = flt(rule.shipping_cost)
        if rule.packaging_cost:
            packaging = flt(rule.packaging_cost)
        if rule.other_cost:
            other = flt(rule.other_cost)
        if rule.advertising_cost:
            advertising = flt(rule.advertising_cost)

    if margin < 0 or fee < 0 or margin + fee >= 95:
        frappe.throw("Invalid margin or payment fee configuration.")

    converted = flt(supplier_cost) * rate
    total_cost = converted + shipping + packaging + other + advertising
    price = round(total_cost / (1 - (margin + fee) / 100), 2)
    fee_amount = price * fee / 100
    profit = round(price - total_cost - fee_amount, 2)

    return {
        "supplier_cost": flt(supplier_cost),
        "supplier_currency": settings.supplier_currency or "USD",
        "selling_currency": settings.selling_currency or "AED",
        "exchange_rate": rate,
        "converted_supplier_cost": round(converted, 2),
        "shipping_cost": shipping,
        "packaging_cost": packaging,
        "other_cost": other,
        "advertising_cost": advertising,
        "total_cost": round(total_cost, 2),
        "margin_percent": margin,
        "payment_fee_percent": fee,
        "payment_fee_amount": round(fee_amount, 2),
        "selling_price": price,
        "expected_profit": profit,
        "actual_margin_percent": round(profit / price * 100, 2) if price else 0,
        "price_list": settings.price_list,
        "category_rule": rule.name if rule else None
    }


@frappe.whitelist()
def preview_price(supplier_cost, category=None):
    return _calculate(supplier_cost, category)


@frappe.whitelist()
def request_price_approval(
    supplier_cost,
    product_name,
    cj_product_id=None,
    cj_variant_id=None,
    category=None,
    item_code=None
):
    result = _calculate(supplier_cost, category)

    doc = frappe.get_doc({
        "doctype": "ProDrop Price Approval",
        "product_name": product_name,
        "cj_product_id": cj_product_id,
        "cj_variant_id": cj_variant_id,
        "item_code": item_code,
        "category_name": category,
        "supplier_cost": result["supplier_cost"],
        "supplier_currency": result["supplier_currency"],
        "exchange_rate": result["exchange_rate"],
        "converted_supplier_cost": result["converted_supplier_cost"],
        "shipping_cost": result["shipping_cost"],
        "packaging_cost": result["packaging_cost"],
        "other_cost": result["other_cost"],
        "advertising_cost": result["advertising_cost"],
        "total_cost": result["total_cost"],
        "margin_percent": result["margin_percent"],
        "payment_fee_percent": result["payment_fee_percent"],
        "selling_price": result["selling_price"],
        "expected_profit": result["expected_profit"],
        "price_list": result["price_list"],
        "status": "Pending"
    })
    doc.insert()
    return {"name": doc.name, "status": doc.status, "pricing": result}


@frappe.whitelist()
def decide_price_approval(approval_id, decision, notes=None):
    frappe.only_for("System Manager")

    if decision not in ("Approved", "Rejected"):
        frappe.throw("Invalid decision.")

    doc = frappe.get_doc("ProDrop Price Approval", approval_id)
    if doc.status != "Pending":
        frappe.throw("This proposal has already been decided.")

    if decision == "Approved" and doc.item_code:
        if not frappe.db.exists("Item", doc.item_code):
            frappe.throw("The linked ERPNext Item does not exist.")

        price_list = doc.price_list
        if not price_list or not frappe.db.exists("Price List", price_list):
            frappe.throw("A valid selling Price List is required.")

        if frappe.db.get_value("Price List", price_list, "currency") != "AED":
            frappe.throw("The Price List must use AED.")

        existing = frappe.db.get_value(
            "Item Price",
            {"item_code": doc.item_code, "price_list": price_list, "selling": 1},
            "name"
        )

        if existing:
            price_doc = frappe.get_doc("Item Price", existing)
            price_doc.price_list_rate = doc.selling_price
            price_doc.save(ignore_permissions=True)
        else:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": doc.item_code,
                "price_list": price_list,
                "price_list_rate": doc.selling_price,
                "currency": "AED",
                "selling": 1
            }).insert(ignore_permissions=True)

    doc.status = decision
    doc.decision_notes = notes
    doc.save(ignore_permissions=True)

    return {
        "name": doc.name,
        "status": doc.status,
        "selling_price": doc.selling_price
    }
