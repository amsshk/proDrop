import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from prodrop.suppliers.cj import CJClient

class CJSettings(Document):
    pass

@frappe.whitelist()
def test_connection():
    frappe.only_for("System Manager")
    settings = frappe.get_single("CJ Settings")
    api_key = settings.get_password("api_key")

    if not api_key:
        frappe.throw("Enter your CJ API Key first.")

    try:
        platform_token = settings.get_password("platform_token", raise_exception=False) or None
        CJClient(api_key, platform_token).list_products(page=1)
        settings.connection_status = "Connected"
        settings.last_connected = now_datetime()
        settings.last_error = ""
        settings.save(ignore_permissions=True)
        return {"success": True, "message": "CJ connection successful."}
    except Exception:
        settings.connection_status = "Failed"
        settings.last_error = "Connection failed. Check credentials and error log."
        settings.save(ignore_permissions=True)
        frappe.log_error(frappe.get_traceback(), "CJ connection test failed")
        frappe.throw("CJ connection failed. Check the Error Log.")
