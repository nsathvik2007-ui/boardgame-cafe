import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def checkin(table):
    # Check if this table already has an active session
    existing = frappe.get_all(
        "Customer Session",
        filters={"table": table, "status": "Active"},
        fields=["name"]
    )

    if existing:
        return frappe.get_doc("Customer Session", existing[0].name)

    # Otherwise create a new session for the logged-in user
    session = frappe.get_doc({
        "doctype": "Customer Session",
        "customer": frappe.session.user,
        "table": table,
        "checkin_time": now_datetime(),
        "party_size": 1,  # default, customer can update later
        "status": "Active"
    })
    session.insert(ignore_permissions=True)

    # Also flip the table's status
    frappe.db.set_value("Table", table, "status", "Occupied")

    return session


@frappe.whitelist()
def get_available_games():
    games = frappe.get_all(
        "Game Title",
        fields=[
            "name", "game_name", "category", "min_players",
            "max_players", "avg_play_time_minutes",
            "complexity_rating", "total_copies_owned"
        ]
    )

    for game in games:
        available_count = frappe.db.count("Game Copy", {
            "game_title": game.name,
            "condition_status": "Available"
        })
        game["available_copies"] = available_count

    return games


@frappe.whitelist()
def checkout_game(customer_session, game_copy):
    checkout = frappe.get_doc({
        "doctype": "Game Checkout",
        "customer_session": customer_session,
        "game_copy": game_copy,
        "checkout_time": now_datetime()
    })
    checkout.insert()
    return checkout

@frappe.whitelist()
def end_session(customer_session):
    session = frappe.get_doc("Customer Session", customer_session)
    session.check_out_time = now_datetime()
    session.status = "Completed"
    session.save()

    frappe.db.set_value("Table", session.table, "status", "Cleaning")

    return session


@frappe.whitelist(allow_guest=True)
def customer_signup(email, full_name, password):
    if frappe.db.exists("User", email):
        frappe.throw("An account with this email already exists.")

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name,
        "send_welcome_email": 0,
        "user_type": "Website User"
    })
    user.insert(ignore_permissions=True)

    user.new_password = password
    user.save(ignore_permissions=True)

    return {"message": "Signup successful", "user": user.name}

@frappe.whitelist()
def place_food_order(customer_session, items):
    if isinstance(items, str):
        items = frappe.parse_json(items)

    order = frappe.get_doc({
        "doctype": "Food Order",
        "customer_session": customer_session,
        "order_time": now_datetime(),
        "items": items
    })
    order.insert()
    return order