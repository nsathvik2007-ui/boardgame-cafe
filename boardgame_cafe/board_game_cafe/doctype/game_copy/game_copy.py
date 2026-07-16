import frappe
from frappe.model.document import Document


class GameCopy(Document):
	def on_update(self):
		current_user = frappe.session.user
		frappe.set_user("Administrator")
		try:
			self.sync_stock_count()
		finally:
			frappe.set_user(current_user)

	def sync_stock_count(self):
		game_title = frappe.get_doc("Game Title", self.game_title)
		if not game_title.erpnext_item:
			return

		item = frappe.get_doc("Item", game_title.erpnext_item)
		warehouse = item.item_defaults[0].default_warehouse if item.item_defaults else None
		if not warehouse:
			return

		copy_count = frappe.db.count(
			"Game Copy",
			{"game_title": self.game_title, "condition_status": ["!=", "Retired"]}
		)

		from erpnext.stock.utils import get_stock_balance
		current_qty = get_stock_balance(item.name, warehouse)
		if current_qty == copy_count:
			return

		company = frappe.db.get_single_value("Global Defaults", "default_company")
		expense_account = frappe.db.get_value(
			"Account", {"company": company, "account_type": "Temporary", "is_group": 0}, "name"
		)

		try:
			reconciliation = frappe.get_doc({
				"doctype": "Stock Reconciliation",
				"purpose": "Stock Reconciliation",
				"company": company,
				"expense_account": expense_account,
				"posting_date": frappe.utils.nowdate(),
				"posting_time": frappe.utils.nowtime(),
				"items": [{
					"item_code": item.name,
					"warehouse": warehouse,
					"qty": copy_count,
					"valuation_rate": game_title.rental_price or 0,
				}],
			})
			reconciliation.insert(ignore_permissions=True)
			reconciliation.submit()
		except Exception:
			frappe.log_error(title="Game Copy stock sync failed")