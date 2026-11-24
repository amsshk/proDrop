frappe.ui.form.on("CJ Settings", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Test Connection"), async () => {
                const r = await frappe.call({
                    method: "prodrop.prodrop.doctype.cj_settings.cj_settings.test_connection"
                });
                if (r.message && r.message.success) {
                    frappe.show_alert({
                        message: r.message.message,
                        indicator: "green"
                    });
                    await frm.reload_doc();
                }
            });
        }
    }
});
