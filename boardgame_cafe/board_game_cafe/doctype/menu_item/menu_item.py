import frappe
from frappe.model.document import Document


class MenuItem(Document):
	def on_update(self):
		self.sync_erpnext_item()

	def sync_erpnext_item(self):
		if self.erpnext_item and frappe.db.exists("Item", self.erpnext_item):
			item = frappe.get_doc("Item", self.erpnext_item)
			item.item_name = self.item_name
			item.standard_rate = self.price
			item.disabled = 0 if self.is_available else 1
			item.save(ignore_permissions=True)
			return

		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": self.item_name,
			"item_name": self.item_name,
			"item_group": "Food & Beverage",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"standard_rate": self.price,
			"disabled": 0 if self.is_available else 1,
		})
		item.insert(ignore_permissions=True)
		self.db_set("erpnext_item", item.name)