"""Read-only CJ product catalogue API for proDrop."""

import frappe
from prodrop.suppliers.cj import CJClient


def _get_cj_client():
    frappe.only_for("System Manager")

    settings = frappe.get_single("CJ Settings")

    if not settings.enabled:
        frappe.throw("Enable CJ Integration in CJ Settings first.")

    api_key = settings.get_password("api_key")
    if not api_key:
        frappe.throw("CJ API Key is missing.")

    platform_token = (
        settings.get_password("platform_token", raise_exception=False) or None
    )

    return CJClient(api_key, platform_token)


@frappe.whitelist()
def search_products(keyword=None, sku=None, category_id=None, page=1, size=20):
    """Search CJ products. Does not import or modify ERPNext Items."""
    try:
        page = max(1, min(int(page), 1000))
        size = max(1, min(int(size), 100))

        client = _get_cj_client()
        return client.list_products(
            page=page,
            size=size,
            keyword=keyword,
            sku=sku,
            category_id=category_id,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "proDrop CJ Catalogue Search")
        frappe.throw("CJ product search failed. Check the Error Log.")


@frappe.whitelist()
def get_product_details(pid):
    """Retrieve details for one CJ product."""
    if not pid:
        frappe.throw("A CJ product ID is required.")

    try:
        return _get_cj_client().get_product_detail(str(pid))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "proDrop CJ Product Details")
        frappe.throw("Could not retrieve CJ product details. Check the Error Log.")


@frappe.whitelist()
def get_product_variants(pid, country_code=None):
    """Retrieve variants for one CJ product."""
    if not pid:
        frappe.throw("A CJ product ID is required.")

    try:
        return _get_cj_client().list_variants(
            str(pid),
            country_code=country_code or None,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "proDrop CJ Product Variants")
        frappe.throw("Could not retrieve CJ product variants. Check the Error Log.")


@frappe.whitelist()
def get_variant_stock(vid):
    """Retrieve live CJ stock for one product variant."""
    if not vid:
        frappe.throw("A CJ variant ID is required.")

    try:
        return _get_cj_client().get_stock(str(vid))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "proDrop CJ Variant Stock")
        frappe.throw("Could not retrieve CJ variant stock. Check the Error Log.")
