# Copyright (c) 2026, Sathvik and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
def validate(self):
    self.checkin_url = f"https://yourfrontend.com/checkin?table={self.table_number}"

class Table(Document):
	pass
