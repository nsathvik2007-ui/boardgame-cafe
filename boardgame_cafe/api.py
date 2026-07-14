import frappe
import qrcode
import io
import base64
import razorpay
import hmac
import hashlib

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
            "complexity_rating", "total_copies_owned", "rental_price"
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
    user.append("roles", {"role": "Customer"})
    user.insert(ignore_permissions=True)

    user.new_password = password
    api_secret = frappe.generate_hash(length=15)
    user.api_key = frappe.generate_hash(length=15)
    user.api_secret = api_secret
    user.save(ignore_permissions=True)

    return {
        "message": "Signup successful",
        "user": user.name,
        "api_key": user.api_key,
        "api_secret": api_secret
    }

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

@frappe.whitelist(allow_guest=True)
def customer_login(email, password):
    from frappe.utils.password import check_password

    try:
        check_password(email, password)
    except frappe.AuthenticationError:
        frappe.throw("Invalid email or password.")

    user = frappe.get_doc("User", email)
    return {
        "message": "Login successful",
        "user": user.name,
        "api_key": user.api_key,
        "api_secret": user.get_password("api_secret")
    }


@frappe.whitelist()
def get_table_qr(table):
    table_doc = frappe.get_doc("Table", table)
    checkin_url = table_doc.checkin_url or f"http://localhost:5173/checkin?table={table_doc.table_number}"

    qr = qrcode.make(checkin_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "table_number": table_doc.table_number,
        "checkin_url": checkin_url,
        "qr_image_base64": img_base64
    }

@frappe.whitelist()
def get_first_available_copy(game_title):
    copies = frappe.get_all(
        "Game Copy",
        filters={"game_title": game_title, "condition_status": "Available"},
        fields=["name"],
        limit=1
    )
    if not copies:
        frappe.throw(f"No available copies of {game_title} right now.")
    return copies[0].name



def get_razorpay_client():
    key_id = frappe.conf.get("razorpay_key_id")
    key_secret = frappe.conf.get("razorpay_key_secret")
    return razorpay.Client(auth=(key_id, key_secret))


@frappe.whitelist()
def create_payment_order(customer_session):
    session = frappe.get_doc("Customer Session", customer_session)

    if session.customer != frappe.session.user:
        frappe.throw("You can only pay for your own session.")

    amount = session.total_bill_amount
    if not amount or amount <= 0:
        frappe.throw("Nothing to pay — bill amount is zero.")

    client = get_razorpay_client()

    razorpay_order = client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "receipt": customer_session,
        "payment_capture": 1
    })

    payment = frappe.get_doc({
        "doctype": "Cafe Payment",
        "customer_session": customer_session,
        "amount": amount,
        "razorpay_order_id": razorpay_order["id"],
        "status": "Created"
    })
    payment.insert()

    return {
        "razorpay_order_id": razorpay_order["id"],
        "amount": int(amount * 100),
        "key_id": frappe.conf.get("razorpay_key_id"),
        "payment_doc": payment.name
    }


@frappe.whitelist()
def verify_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    key_secret = frappe.conf.get("razorpay_key_secret")

    generated_signature = hmac.new(
        key_secret.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if generated_signature != razorpay_signature:
        frappe.throw("Payment verification failed. Signature mismatch.")

    payment = frappe.get_doc("Cafe Payment", {"razorpay_order_id": razorpay_order_id})

    if payment.customer_session:
        session = frappe.get_doc("Customer Session", payment.customer_session)
        if session.customer != frappe.session.user:
            frappe.throw("You can only verify payments for your own session.")

    payment.razorpay_payment_id = razorpay_payment_id
    payment.status = "Paid"
    payment.save(ignore_permissions=True)

    return {"status": "success", "message": "Payment verified successfully."}


def require_staff():
    if frappe.session.user == "Administrator":
        return
    roles = frappe.get_roles(frappe.session.user)
    if "Cafe Staff" not in roles:
        frappe.throw("Staff access required.", frappe.PermissionError)


@frappe.whitelist()
def get_dashboard_overview():
    require_staff()

    tables = frappe.get_all(
        "Table",
        fields=["name", "table_number", "zonelocation", "seating_capacity", "status"]
    )

    for table in tables:
        session = frappe.get_all(
            "Customer Session",
            filters={"table": table.name, "status": "Active"},
            fields=["name", "customer", "party_size", "checkin_time", "total_bill_amount"],
            limit=1
        )
        table["active_session"] = session[0] if session else None

        if session:
            payment = frappe.get_all(
                "Cafe Payment",
                filters={"customer_session": session[0].name, "status": "Paid"},
                fields=["name"],
                limit=1
            )
            table["is_paid"] = bool(payment)
        else:
            table["is_paid"] = None

    return tables


@frappe.whitelist()
def mark_table_free(table):
    require_staff()

    active = frappe.get_all(
        "Customer Session",
        filters={"table": table, "status": "Active"},
        fields=["name"]
    )
    if active:
        frappe.throw("Cannot free a table with an active session. End the session first.")

    frappe.db.set_value("Table", table, "status", "Free")
    return {"message": f"Table {table} marked as Free."}


@frappe.whitelist()
def force_end_session(customer_session):
    require_staff()

    session = frappe.get_doc("Customer Session", customer_session)
    session.check_out_time = frappe.utils.now_datetime()
    session.status = "Completed"
    session.save(ignore_permissions=True)

    frappe.db.set_value("Table", session.table, "status", "Cleaning")

    return {"message": "Session ended by staff.", "session": session.name}


@frappe.whitelist()
def get_unpaid_sessions():
    require_staff()

    completed = frappe.get_all(
        "Customer Session",
        filters={"status": "Completed"},
        fields=["name", "customer", "table", "total_bill_amount"]
    )

    unpaid = []
    for s in completed:
        if not s.total_bill_amount:
            continue
        payment = frappe.get_all(
            "Cafe Payment",
            filters={"customer_session": s.name, "status": "Paid"},
            fields=["name"]
        )
        if not payment:
            unpaid.append(s)

    return unpaid