# Copyright (c) 2026, Sathvik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GameCheckout(Document):
    def validate(self):
        self.check_copy_availability()

    def check_copy_availability(self):
        game_copy = frappe.get_doc("Game Copy", self.game_copy)

        # Only block on create / when checkout isn't already returned
        if not self.return_time and game_copy.condition_status != "Available":
            frappe.throw(
                f"Copy '{game_copy.copy_code}' is currently '{game_copy.condition_status}' and cannot be checked out."
            )

    def on_update(self):
        game_copy = frappe.get_doc("Game Copy", self.game_copy)

        if not self.return_time:
            # Actively checked out
            game_copy.condition_status = "Checked Out"
            game_copy.total_checkouts = (game_copy.total_checkouts or 0) + 1
        elif self.return_time and self.piece_check_status == "Pending":
            # Returned but not yet piece-verified — lock it
            game_copy.condition_status = "Under Repair"

        game_copy.save(ignore_permissions=True)