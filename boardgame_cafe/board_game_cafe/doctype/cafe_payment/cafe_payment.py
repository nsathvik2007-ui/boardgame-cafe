# Copyright (c) 2026, Sathvik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CafePayment(Document):
	pass

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""
    if "Cafe Staff" in frappe.get_roles(user):
        return ""
    return f"""`tabCafe Payment`.customer_session in (
        select name from `tabCustomer Session` where customer = '{user}'
    )"""