import frappe
from frappe.model.document import Document


class GameCheckout(Document):
    def validate(self):
        self.check_copy_availability()
        self.set_rental_fee()

    def check_copy_availability(self):
        game_copy = frappe.get_doc("Game Copy", self.game_copy)
        if not self.return_time and game_copy.condition_status != "Available":
            frappe.throw(
                f"Copy '{game_copy.copy_code}' is currently '{game_copy.condition_status}' and cannot be checked out."
            )

    def set_rental_fee(self):
        if not self.rental_fee:
            game_copy = frappe.get_doc("Game Copy", self.game_copy)
            game_title = frappe.get_doc("Game Title", game_copy.game_title)
            self.rental_fee = game_title.rental_price or 0

    def on_update(self):
        game_copy = frappe.get_doc("Game Copy", self.game_copy)

        if not self.return_time:
            game_copy.condition_status = "Checked Out"
            game_copy.total_checkouts = (game_copy.total_checkouts or 0) + 1
        elif self.piece_check_status == "Missing Pieces":
            game_copy.condition_status = "Missing Pieces"
        elif self.piece_check_status == "Verification Complete":
            game_copy.condition_status = "Available"
        else:
            game_copy.condition_status = "Under Repair"

        game_copy.save(ignore_permissions=True)
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

        frappe.db.set_value("Customer Session", self.customer_session, "total_bill_amount", game_total + food_total)


def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    if "Cafe Staff" in frappe.get_roles(user):
        return ""

    return f"""`tabGame Checkout`.customer_session in (
        select name from `tabCustomer Session` where customer = '{user}'
    )"""