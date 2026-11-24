import frappe
from frappe.model.document import Document


class ProDropRecommendation(Document):
	def validate(self):
		if self.status in ("Approved", "Rejected") and not self.decision_notes:
			frappe.msgprint("Add a note explaining the decision.", indicator="orange")
