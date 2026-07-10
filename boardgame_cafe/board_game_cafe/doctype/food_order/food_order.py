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

        session = frappe.get_doc("Customer Session", self.customer_session)

        if session.status != "Active":
            frappe.throw("Food can only be ordered during an active customer session.")

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
            filters={"customer_session": self.customer_session},
            fields=["total_amount"]
        )
        food_total = sum(o.total_amount or 0 for o in orders)

        frappe.db.set_value(
            "Customer Session",
            self.customer_session,
            "total_bill_amount",
            game_total + food_total
        )


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    return f"""`tabFood Order`.customer_session in (
        select name from `tabCustomer Session` where customer = '{user}'
    )"""