app_name = "prodrop"
app_title = "proDrop"
app_publisher = "EzDevSoft"
app_description = "Automated dropshipping for ERPNext"
app_email = "admin@ezdevsoft.net"
app_license = "mit"

required_apps = ["erpnext"]

# Wire these up once the supplier connector is implemented.
#
# doc_events = {
# 	"Sales Order": {"on_submit": "prodrop.orders.on_sales_order_submit"},
# }
#
# scheduler_events = {
# 	"hourly": ["prodrop.tasks.sync_supplier_stock"],
# 	"daily": ["prodrop.tasks.refresh_trends"],
# }
