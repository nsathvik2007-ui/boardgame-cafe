# Copyright (c) 2026, Sathvik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PieceInventoryCheck(Document):
    def validate(self):
        game_copy = frappe.get_doc("Game Copy", self.game_copy)

        # Auto-pull expected count from the Game Copy
        self.expected_count = game_copy.total_piece_count

        # Calculate discrepancy
        self.discrepancy = self.expected_count - self.actual_count

    def on_update(self):
        game_copy = frappe.get_doc("Game Copy", self.game_copy)

        if self.discrepancy == 0:
            game_copy.condition_status = "Available"
        else:
            game_copy.condition_status = "Missing Pieces"

        game_copy.last_verified_datetime = self.check_date
        game_copy.save(ignore_permissions=True)