# Copyright (c) 2026, Sathvik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class FoodOrder(Document):
    def before_insert(self):
        if not self.order_time:
            self.order_time = now_datetime()

    def validate(self):
        self.calculate_total()

    def calculate_total(self):
        total = 0

        for item in self.items:
            if item.quantity <= 0:
                frappe.throw("Quantity must be greater than 0.")

            menu = frappe.get_doc("Menu Item", item.menu_item)

            if not menu.is_available:
                frappe.throw(f"{menu.item_name} is currently unavailable.")

            item.rate = flt(menu.price)
            item.amount = flt(item.rate) * flt(item.quantity)

            total += item.amount

        self.total_amount = flt(total)

    def on_update(self):
        self.update_session_bill()

    def update_session_bill(self):
        checkouts = frappe.get_all(
            "Game Checkout",
            filters={"customer_session": self.customer_session},
            fields=["rental_fee"]
        )
        game_total = sum(c.rental_fee or 0 for c in checkouts)

        orders = frappe.get_all(
            "Food Order",
            filters={"customer_session": self.customer_session, "status": ["!=", "Cancelled"]},
            fields=["total_amount"]
        )
        food_total = sum(o.total_amount or 0 for o in orders)

        frappe.db.set_value(
            "Customer Session",
            self.customer_session,
            "total_bill_amount",
            game_total + food_total
        )

    def after_insert(self):
        self.deduct_stock()

    def deduct_stock(self):
        entries = []
        for row in self.items:
            menu = frappe.get_doc("Menu Item", row.menu_item)
            if not menu.erpnext_item:
                continue

            item = frappe.get_doc("Item", menu.erpnext_item)
            warehouse = item.item_defaults[0].default_warehouse if item.item_defaults else None
            if not warehouse:
                continue

            entries.append({
                "item_code": item.name,
                "qty": row.quantity,
                "uom": item.stock_uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": 1,
                "s_warehouse": warehouse,
            })

        if not entries:
            return

        stock_entry = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Issue",
            "company": frappe.db.get_single_value("Global Defaults", "default_company"),
            "items": entries,
        })
        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

    def restore_stock(self):
        entries = []
        for row in self.items:
            menu = frappe.get_doc("Menu Item", row.menu_item)
            if not menu.erpnext_item:
                continue

            item = frappe.get_doc("Item", menu.erpnext_item)
            warehouse = item.item_defaults[0].default_warehouse if item.item_defaults else None
            if not warehouse:
                continue

            entries.append({
                "item_code": item.name,
                "qty": row.quantity,
                "uom": item.stock_uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": 1,
                "t_warehouse": warehouse,
            })

        if not entries:
            return

        stock_entry = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Receipt",
            "company": frappe.db.get_single_value("Global Defaults", "default_company"),
            "items": entries,
        })
        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

    def adjust_stock_for_edit(self, old_qty, new_qty):
        increase_entries = []
        decrease_entries = []

        for menu_item_name in set(old_qty) | set(new_qty):
            delta = new_qty.get(menu_item_name, 0) - old_qty.get(menu_item_name, 0)
            if delta == 0:
                continue

            menu = frappe.get_doc("Menu Item", menu_item_name)
            if not menu.erpnext_item:
                continue
            item = frappe.get_doc("Item", menu.erpnext_item)
            warehouse = item.item_defaults[0].default_warehouse if item.item_defaults else None
            if not warehouse:
                continue

            entry = {
                "item_code": item.name,
                "qty": abs(delta),
                "uom": item.stock_uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": 1,
            }
            if delta > 0:
                increase_entries.append({**entry, "s_warehouse": warehouse})
            else:
                decrease_entries.append({**entry, "t_warehouse": warehouse})

        company = frappe.db.get_single_value("Global Defaults", "default_company")
        for entries, entry_type in [(increase_entries, "Material Issue"), (decrease_entries, "Material Receipt")]:
            if entries:
                stock_entry = frappe.get_doc({
                    "doctype": "Stock Entry",
                    "stock_entry_type": entry_type,
                    "company": company,
                    "items": entries,
                })
                stock_entry.insert(ignore_permissions=True)
                stock_entry.submit()


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""
    if "Cafe Staff" in frappe.get_roles(user):
        return ""

    return f"""`tabFood Order`.customer_session in (
        select name from `tabCustomer Session` where customer = '{user}'
    )"""