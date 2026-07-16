import frappe
import qrcode
import io
import base64
import razorpay
import hmac
import hashlib

from frappe.utils import now_datetime, flt


@frappe.whitelist()
def checkin(table):
    # Check if this table already has an active session
    existing = frappe.get_all(
        "Customer Session",
        filters={"table": table, "status": "Active"},
        fields=["name", "customer"]
    )

    if existing:
        if existing[0].customer == frappe.session.user:
            return frappe.get_doc("Customer Session", existing[0].name)
        frappe.throw("This table is currently occupied. Please ask staff for help.")

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
def get_menu():
    return frappe.get_all(
        "Menu Item",
        filters={"is_available": 1},
        fields=["name", "item_name", "category", "price"]
    )


@frappe.whitelist()
def checkout_game(customer_session, game_copy):
    session = frappe.get_doc("Customer Session", customer_session)
    if session.customer != frappe.session.user:
        frappe.throw("You can only check out games for your own session.")

    checkout = frappe.get_doc({
        "doctype": "Game Checkout",
        "customer_session": customer_session,
        "game_copy": game_copy,
        "checkout_time": now_datetime()
    })
    checkout.insert()
    return checkout

@frappe.whitelist()
def update_party_size(customer_session, party_size):
    session = frappe.get_doc("Customer Session", customer_session)
    if session.customer != frappe.session.user:
        frappe.throw("You can only update your own session.")

    session.party_size = party_size
    session.save()
    return session

@frappe.whitelist()
def end_session(customer_session):
    session = frappe.get_doc("Customer Session", customer_session)
    if session.customer != frappe.session.user:
        frappe.throw("You can only end your own session.")

    session.checkout_time = now_datetime()
    session.status = "Completed"
    session.save()

    frappe.db.set_value("Table", session.table, "status", "Cleaning")

    invoice = session.generate_sales_invoice()

    return {"session": session.name, "sales_invoice": invoice}


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
    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": full_name,
        "customer_type": "Individual",
        "customer_group": "Individual",
        "territory": "India"
    })
    customer.insert(ignore_permissions=True)

    user.db_set("custom_erpnext_customer", customer.name)

    return {
        "message": "Signup successful",
        "user": user.name,
        "api_key": user.api_key,
        "api_secret": api_secret,
        "erpnext_customer": customer.name
    }

@frappe.whitelist()
def place_food_order(customer_session, items):
    session = frappe.get_doc("Customer Session", customer_session)
    if session.customer != frappe.session.user:
        frappe.throw("You can only order food for your own session.")

    if session.status != "Active":
        frappe.throw("Food can only be ordered during an active customer session.")

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

@frappe.whitelist()
def edit_food_order(food_order, items):
    order = frappe.get_doc("Food Order", food_order)
    session = frappe.get_doc("Customer Session", order.customer_session)

    is_staff = frappe.session.user == "Administrator" or "Cafe Staff" in frappe.get_roles(frappe.session.user)
    if not is_staff and session.customer != frappe.session.user:
        frappe.throw("You can only edit your own order.")

    if order.status != "Placed":
        frappe.throw("This order can no longer be edited — it's already being prepared.")

    if session.status != "Active":
        frappe.throw("This order can no longer be edited — the session has ended.")

    if isinstance(items, str):
        items = frappe.parse_json(items)

    old_qty = {}
    for row in order.items:
        old_qty[row.menu_item] = old_qty.get(row.menu_item, 0) + row.quantity

    new_qty = {}
    for row in items:
        new_qty[row["menu_item"]] = new_qty.get(row["menu_item"], 0) + row["quantity"]

    order.items = []
    for row in items:
        order.append("items", row)
    order.save()

    order.adjust_stock_for_edit(old_qty, new_qty)
    return order

@frappe.whitelist()
def cancel_food_order(food_order):
    order = frappe.get_doc("Food Order", food_order)
    session = frappe.get_doc("Customer Session", order.customer_session)

    is_staff = frappe.session.user == "Administrator" or "Cafe Staff" in frappe.get_roles(frappe.session.user)
    if not is_staff and session.customer != frappe.session.user:
        frappe.throw("You can only cancel your own order.")

    if order.status != "Placed":
        frappe.throw("This order can no longer be cancelled — it's already being prepared.")

    order.restore_stock()
    order.status = "Cancelled"
    order.save()
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
        "api_secret": user.get_password("api_secret"),
        "roles": frappe.get_roles(user.name)
    }


@frappe.whitelist()
def get_my_profile():
    user = frappe.get_doc("User", frappe.session.user)
    return {
        "email": user.name,
        "full_name": user.full_name,
        "erpnext_customer": user.custom_erpnext_customer
    }


@frappe.whitelist()
def update_my_profile(full_name):
    user = frappe.get_doc("User", frappe.session.user)
    user.first_name = full_name
    user.save(ignore_permissions=True)
    return {"message": "Profile updated", "full_name": user.full_name}


@frappe.whitelist()
def get_table_qr(table):
    require_staff()

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

    already_paid = frappe.get_all(
        "Cafe Payment",
        filters={"customer_session": customer_session, "status": "Paid"},
        limit=1
    )
    if already_paid:
        frappe.throw("This session has already been paid.")

    amount = session.total_bill_amount
    if not amount or amount <= 0:
        frappe.throw("Nothing to pay — bill amount is zero.")

    client = get_razorpay_client()

    razorpay_order = client.order.create({
        "amount": round(amount * 100),
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
        "amount": round(amount * 100),
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

    if payment.status == "Paid":
        return {"status": "success", "message": "Payment already verified."}

    if payment.customer_session:
        session = frappe.get_doc("Customer Session", payment.customer_session)
        if session.customer != frappe.session.user:
            frappe.throw("You can only verify payments for your own session.")

        other_paid = frappe.get_all(
            "Cafe Payment",
            filters={
                "customer_session": payment.customer_session,
                "status": "Paid",
                "name": ["!=", payment.name],
            },
            limit=1
        )
        if other_paid:
            frappe.throw("This session has already been paid via a different transaction.")

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
    session.checkout_time = frappe.utils.now_datetime()
    session.status = "Completed"
    session.save(ignore_permissions=True)

    frappe.db.set_value("Table", session.table, "status", "Cleaning")

    invoice = session.generate_sales_invoice()

    return {"message": "Session ended by staff.", "session": session.name, "sales_invoice": invoice}


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

@frappe.whitelist()
def return_game(game_checkout, piece_check_status="Verification Complete"):
    require_staff()

    checkout = frappe.get_doc("Game Checkout", game_checkout)
    checkout.return_time = now_datetime()
    checkout.piece_check_status = piece_check_status
    checkout.save(ignore_permissions=True)
    return checkout


@frappe.whitelist()
def get_checked_out_games():
    require_staff()

    checkouts = frappe.get_all(
        "Game Checkout",
        filters={"return_time": ["is", "not set"]},
        fields=["name", "game_copy", "customer_session", "checkout_time", "rental_fee"],
        order_by="checkout_time asc"
    )

    for c in checkouts:
        game_copy = frappe.get_doc("Game Copy", c.game_copy)
        c["copy_code"] = game_copy.copy_code
        c["game_title"] = game_copy.game_title
        c["condition_status"] = game_copy.condition_status

        session = frappe.get_doc("Customer Session", c.customer_session)
        c["table"] = session.table
        c["customer"] = session.customer

    return checkouts

@frappe.whitelist()
def get_food_inventory():
    require_staff()

    from erpnext.stock.utils import get_stock_balance

    menu_items = frappe.get_all(
        "Menu Item",
        fields=["name", "item_name", "category", "price", "is_available", "erpnext_item"]
    )

    current_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        for mi in menu_items:
            mi["stock_qty"] = None
            if not mi.erpnext_item:
                continue

            item = frappe.get_doc("Item", mi.erpnext_item)
            warehouse = item.item_defaults[0].default_warehouse if item.item_defaults else None
            if not warehouse:
                continue

            mi["stock_qty"] = get_stock_balance(item.name, warehouse)
    finally:
        frappe.set_user(current_user)

    return menu_items


@frappe.whitelist()
def restock_menu_item(menu_item, qty):
    require_staff()

    qty = flt(qty)
    if qty <= 0:
        frappe.throw("Restock quantity must be greater than 0.")

    menu = frappe.get_doc("Menu Item", menu_item)
    if not menu.erpnext_item:
        frappe.throw("This item isn't linked to inventory tracking.")

    current_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        from erpnext.stock.utils import get_stock_balance

        item = frappe.get_doc("Item", menu.erpnext_item)
        warehouse = item.item_defaults[0].default_warehouse if item.item_defaults else None
        if not warehouse:
            frappe.throw("No default warehouse configured for this item.")

        new_qty = get_stock_balance(item.name, warehouse) + qty

        company = frappe.db.get_single_value("Global Defaults", "default_company")
        expense_account = frappe.db.get_value(
            "Account", {"company": company, "account_type": "Temporary", "is_group": 0}, "name"
        )

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
                "qty": new_qty,
                "valuation_rate": menu.price,
            }],
        })
        reconciliation.insert(ignore_permissions=True)
        reconciliation.submit()

        final_qty = get_stock_balance(item.name, warehouse)
    finally:
        frappe.set_user(current_user)

    return {"stock_qty": final_qty}


@frappe.whitelist()
def get_kitchen_queue():
    require_staff()

    orders = frappe.get_all(
        "Food Order",
        filters={"status": ["not in", ["Served", "Cancelled"]]},
        fields=["name", "customer_session", "order_time", "status", "total_amount"],
        order_by="order_time asc"
    )

    for order in orders:
        order["items"] = frappe.get_all(
            "Food Order Item",
            filters={"parent": order.name},
            fields=["menu_item", "quantity"]
        )
        order["table"] = frappe.db.get_value("Customer Session", order.customer_session, "table")

    return orders


@frappe.whitelist()
def update_food_order_status(food_order, status):
    require_staff()

    if status not in ("Placed", "Preparing", "Served"):
        frappe.throw("Invalid status. Use cancel_food_order to cancel an order.")

    order = frappe.get_doc("Food Order", food_order)
    order.status = status
    order.save(ignore_permissions=True)
    return order


@frappe.whitelist()
def get_invoice(customer_session):
    session = frappe.get_doc("Customer Session", customer_session)

    is_staff = frappe.session.user == "Administrator" or "Cafe Staff" in frappe.get_roles(frappe.session.user)
    if not is_staff and session.customer != frappe.session.user:
        frappe.throw("You can only view your own invoice.")

    if not session.sales_invoice:
        frappe.throw("No invoice has been generated for this session yet.")

    current_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        invoice = frappe.get_doc("Sales Invoice", session.sales_invoice)
        data = {
            "name": invoice.name,
            "customer": invoice.customer,
            "posting_date": str(invoice.posting_date),
            "grand_total": invoice.grand_total,
            "status": invoice.status,
            "items": [
                {"item_code": i.item_code, "item_name": i.item_name, "qty": i.qty, "rate": i.rate, "amount": i.amount}
                for i in invoice.items
            ],
        }
    finally:
        frappe.set_user(current_user)

    return data


@frappe.whitelist()
def get_session_summary(customer_session):
    session = frappe.get_doc("Customer Session", customer_session)

    is_staff = frappe.session.user == "Administrator" or "Cafe Staff" in frappe.get_roles(frappe.session.user)
    if not is_staff and session.customer != frappe.session.user:
        frappe.throw("You can only view your own session.")

    checkouts = frappe.get_all(
        "Game Checkout",
        filters={"customer_session": customer_session},
        fields=["name", "game_copy", "checkout_time", "return_time", "rental_fee"]
    )
    for c in checkouts:
        c["game_title"] = frappe.db.get_value("Game Copy", c.game_copy, "game_title")

    orders = frappe.get_all(
        "Food Order",
        filters={"customer_session": customer_session},
        fields=["name", "order_time", "status", "total_amount"]
    )
    for o in orders:
        o["items"] = frappe.get_all(
            "Food Order Item",
            filters={"parent": o.name},
            fields=["menu_item", "quantity", "rate", "amount"]
        )

    return {
        "session": session.name,
        "table": session.table,
        "status": session.status,
        "party_size": session.party_size,
        "total_bill_amount": session.total_bill_amount,
        "game_checkouts": checkouts,
        "food_orders": orders
    }