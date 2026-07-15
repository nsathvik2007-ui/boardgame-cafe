import frappe
from frappe.model.document import Document


class Table(Document):
	def validate(self):
		base_url = frappe.conf.get("frontend_url", "http://localhost:5173")
		self.checkin_url = f"{base_url}/checkin?table={self.table_number}"
