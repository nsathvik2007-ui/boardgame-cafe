import frappe
from frappe.model.document import Document


class GameTitle(Document):
	def on_update(self):
		self.sync_erpnext_item()

	def sync_erpnext_item(self):
		if self.erpnext_item and frappe.db.exists("Item", self.erpnext_item):
			item = frappe.get_doc("Item", self.erpnext_item)
			item.item_name = self.game_name
			item.standard_rate = self.rental_price
			item.save(ignore_permissions=True)
			return

		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": self.game_name,
			"item_name": self.game_name,
			"item_group": "Board Games",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"standard_rate": self.rental_price,
		})
		item.insert(ignore_permissions=True)
		self.db_set("erpnext_item", item.name)
