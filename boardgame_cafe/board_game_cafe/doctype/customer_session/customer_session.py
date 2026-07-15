import frappe
from frappe.model.document import Document


class CustomerSession(Document):
	def generate_sales_invoice(self):
		if self.sales_invoice:
			return self.sales_invoice

		customer = frappe.db.get_value("User", self.customer, "custom_erpnext_customer")
		if not customer:
			return None

		items = []

		checkouts = frappe.get_all(
			"Game Checkout",
			filters={"customer_session": self.name},
			fields=["game_copy", "rental_fee"],
		)
		for checkout in checkouts:
			game_title = frappe.db.get_value("Game Copy", checkout.game_copy, "game_title")
			erpnext_item = frappe.db.get_value("Game Title", game_title, "erpnext_item")
			if not erpnext_item:
				continue
			items.append({
				"item_code": erpnext_item,
				"qty": 1,
				"rate": checkout.rental_fee or 0,
			})

		orders = frappe.get_all("Food Order", filters={"customer_session": self.name}, fields=["name"])
		for order in orders:
			order_doc = frappe.get_doc("Food Order", order.name)
			for row in order_doc.items:
				menu_erpnext_item = frappe.db.get_value("Menu Item", row.menu_item, "erpnext_item")
				if not menu_erpnext_item:
					continue
				items.append({
					"item_code": menu_erpnext_item,
					"qty": row.quantity,
					"rate": row.rate,
				})

		if not items:
			return None

		current_user = frappe.session.user
		frappe.set_user("Administrator")
		try:
			invoice = frappe.get_doc({
				"doctype": "Sales Invoice",
				"customer": customer,
				"company": frappe.db.get_single_value("Global Defaults", "default_company"),
				"items": items,
			})
			invoice.insert(ignore_permissions=True)
			invoice.submit()
		finally:
			frappe.set_user(current_user)

		self.db_set("sales_invoice", invoice.name)
		return invoice.name


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""
    if "Cafe Staff" in frappe.get_roles(user):
        return ""

    return f"`tabCustomer Session`.customer = '{user}'"