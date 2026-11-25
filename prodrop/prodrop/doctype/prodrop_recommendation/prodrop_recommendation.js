frappe.ui.form.on("ProDrop Recommendation", {
	refresh(frm) {
		if (frm.doc.status !== "Pending") return;

		const decide = (decision) => {
			frappe.prompt(
				{ label: "Note (why)", fieldname: "notes", fieldtype: "Small Text", reqd: 1 },
				(values) => {
					frappe.call({
						method: "prodrop.tasks.decide_recommendation",
						args: { name: frm.doc.name, decision: decision, notes: values.notes },
						callback: () => frm.reload_doc(),
					});
				},
				`${decision} this recommendation`,
				decision
			);
		};

		frm.add_custom_button(__("Approve"), () => decide("Approved"));
		frm.add_custom_button(__("Reject"), () => decide("Rejected"));
	},
});
