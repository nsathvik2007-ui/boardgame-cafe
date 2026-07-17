# Board Game Café Management System

A unified backend system for a board game café, built on the [Frappe Framework](https://frappeframework.com/) and [ERPNext](https://erpnext.com/). It manages the full customer lifecycle — QR-based table check-in, live game library browsing with piece-level inventory tracking, food ordering, and Razorpay payment — all tied together through a single session model, with real accounting and stock behind it via ERPNext rather than a parallel home-grown system.

The companion frontend (React/Vite) lives in a separate repo: [boardgame-cafe-frontend](https://github.com/nsathvik2007-ui/boardgame-cafe-frontend).

## The Problem

Board game cafés typically juggle two disconnected systems: one for tracking game inventory (which is fragile — games have hundreds of small pieces that go missing) and another for food/table service. This project unifies both under a single **Customer Session**, so a customer's entire visit — from sitting down, to borrowing a game, to ordering food, to paying, to leaving — is tracked coherently in one place.

It also solves a specific, often-overlooked problem in board game cafés: **incomplete games silently get re-rented**. This system enforces a locking mechanism so a game copy can never be checked out again until a staff member has verified all its pieces are present.

## Core Concept

Everything hangs off **Customer Session** — created automatically when a customer scans a QR code at their table and logs in. From there, they can browse available games (with live copy counts), check out a game, place food orders, and pay the bill, all scoped to that one session.

```
Customer scans QR at table
        │
        ▼
   Signs up / Logs in
        │
        ▼
  Customer Session created (via checkin API)
        │
        ├──► Browse Game Library ──► Checkout Game ──► Return ──► Piece Verification ──► Unlocked
        │
        ├──► Browse Menu ──► Place Food Order ──► Bill auto-updates on Session
        │                          │
        │                          ▼ (staff side)
        │                    Kitchen Queue ──► Preparing ──► Served
        │
        ▼
  Pay Bill (Razorpay) ──► Sales Invoice created in ERPNext ──► Session ends, table freed
```

## Why ERPNext, not just Frappe

This app deliberately doesn't reinvent stock tracking or billing — it hangs off ERPNext's existing modules instead:

- Every **Menu Item** auto-creates/syncs a real ERPNext **Item** (`menu_item.py`'s `on_update` hook), so stock levels are read via `erpnext.stock.utils.get_stock_balance` against a real **Warehouse**, and restocking goes through an actual **Stock Reconciliation** entry — not a plain integer field on Menu Item.
- Every customer signup creates a real ERPNext **Customer** record (with `Customer Group` and `Territory`), and paying a bill generates a real ERPNext **Sales Invoice** — viewable and auditable in the standard ERPNext accounting UI, not a bespoke invoice table.

The tradeoff: a fresh install needs a Company (with its default warehouses/accounts) and the `Individual` Customer Group / `India` Territory to already exist — normally created by ERPNext's Setup Wizard, which this app's headless install flow skips. If those are missing, you'll see a `LinkValidationError` on signup or `on_update` failures on Menu Item — create the missing master records once, and it's a non-issue going forward.

## Doctypes (Data Model)

| Doctype | Purpose |
|---|---|
| **Game Title** | Master data for a game (name, category, player count, complexity) |
| **Game Copy** | A physical copy of a game, with lifecycle status (`Available` → `Checked Out` → `Under Repair` → `Available`/`Missing Pieces` → `Retired`) |
| **Table** | Physical café table (`table_number` is the docname), seating capacity, zone, status; auto-generates its `checkin_url`/QR target from the `frontend_url` site config |
| **Customer Session** | The hub — one record per visit, links customer, table, running bill, and (once paid) the resulting Sales Invoice |
| **Game Checkout** | A borrow record; blocks checkout of unavailable copies via `validate()` |
| **Piece Inventory Check** | Logged when a returned copy is verified; auto-calculates discrepancy and unlocks/relocks the copy |
| **Menu Item** | Food/beverage master data; syncs to a real ERPNext **Item** on save (see above) |
| **Food Order** | Order tied to a session, with a child table of line items; staff can edit/cancel while status is `Placed` |
| **Food Order Item** *(child table)* | Individual line item; auto-calculates rate and amount |
| **Cafe Payment** | One record per Razorpay order; tracks `Created` → `Paid` status and links back to the Customer Session |

### Key design decisions worth noting

- **`Retired` instead of delete**: Game Copies are never deleted, even when out of circulation — this preserves the link integrity of historical `Game Checkout` records and keeps an audit trail.
- **Piece-check locking**: A returned game copy goes to `Under Repair` (not directly back to `Available`) until a `Piece Inventory Check` confirms the count matches. This prevents an incomplete game from being silently re-rented.
- **Session as hub, not per-feature accounts**: Rather than separate systems for games, food, and payment, all three link through `Customer Session`, so the café gets one coherent bill and one coherent history per visit.
- **Real ERPNext masters behind the scenes**: see "Why ERPNext, not just Frappe" above — Menu Items and payments aren't tracked in isolation, they're real Items/Warehouses/Sales Invoices.

## Custom API Endpoints

Beyond Frappe's default REST API (`/api/resource/<doctype>`), this app exposes purpose-built endpoints for the actual customer and staff flows.

**Customer-facing**

| Endpoint | Method | Purpose |
|---|---|---|
| `customer_signup` | POST | Creates a Website User + linked ERPNext Customer, returns an API key/secret pair |
| `customer_login` | POST | Verifies credentials, returns the user's existing API key/secret and roles |
| `get_my_profile` / `update_my_profile` | GET / POST | Read/update the logged-in user's profile |
| `checkin` | POST | QR-triggered: finds or creates an active session for a table |
| `update_party_size` | POST | Updates how many people are at the table for a session |
| `get_available_games` | GET | All games with live available-copy counts |
| `get_first_available_copy` | GET | First free copy of a given game title |
| `checkout_game` | POST | Checks out a game copy to a session (enforces availability) |
| `get_menu` | GET | Available menu items |
| `place_food_order` | POST | Places a multi-item food order, auto-calculates totals |
| `edit_food_order` / `cancel_food_order` | POST | Modify or cancel an order while it's still `Placed` |
| `create_payment_order` | POST | Creates a Razorpay order for the session's bill |
| `verify_payment` | POST | Verifies Razorpay's signature, finalizes payment, generates the Sales Invoice |
| `get_invoice` | GET | The resulting Sales Invoice for a paid session |
| `get_session_summary` | GET | Running bill breakdown for a session |
| `end_session` | POST | Closes out a session and frees the table for cleaning |

**Staff-facing** (all require the `Cafe Staff` role, or Administrator)

| Endpoint | Method | Purpose |
|---|---|---|
| `get_dashboard_overview` | GET | Table statuses + active session summary |
| `get_table_qr` | GET | Generates the QR code (PNG, base64) for a table's check-in URL |
| `mark_table_free` | POST | Manually frees a table |
| `force_end_session` | POST | Staff override to close a session |
| `get_unpaid_sessions` | GET | Sessions awaiting payment |
| `get_checked_out_games` | GET | All currently checked-out copies |
| `return_game` | POST | Logs a return + piece verification result |
| `get_kitchen_queue` | GET | Live food order queue |
| `update_food_order_status` | POST | Advances an order (`Placed` → `Preparing` → `Served`) |
| `get_food_inventory` | GET | Stock level per menu item (via ERPNext stock balance) |
| `restock_menu_item` | POST | Creates a Stock Reconciliation to add quantity |

**Webhook**

| Endpoint | Method | Purpose |
|---|---|---|
| `razorpay_webhook` | POST | Server-to-server payment confirmation (`allow_guest`) — verifies Razorpay's HMAC signature, marks a session paid even if the customer closes their browser right after paying |

## Authentication & Permissions

- **Customers** are Frappe **Website Users**, authenticated via **token-based auth** (API key/secret pair), not session cookies. On signup or login, the backend generates/returns an `api_key` and `api_secret`, which the frontend stores (e.g. in `localStorage`) and attaches to every subsequent request as `Authorization: token {api_key}:{api_secret}`.
  - This was a deliberate choice over cookie-based session auth: the frontend is a separately-run app (different origin from the Frappe backend), and cross-site cookies bring real friction (`SameSite` restrictions, CORS-with-credentials limitations, browser third-party cookie crackdowns). A bearer token avoids all of that.
  - Tradeoff, stated plainly: `api_secret` is stored retrievably server-side so it can be re-issued on login, rather than using short-lived rotating tokens. This is a deliberate simplification appropriate for this project's scope, not a production-grade token strategy.
- **Staff/Admin** use the same API key/secret mechanism, but the account itself must be created directly in the desk (**User → API Access → Generate Keys**, plus the `Cafe Staff` role) — there is no self-service staff signup endpoint, by design.
- **Row-level permission scoping**: Customers can only see their own `Customer Session`, `Game Checkout`, `Food Order`, and `Cafe Payment` records, enforced via `permission_query_conditions` hooks — not just default doctype permissions.
- Game and menu browsing require authentication (a deliberate product choice — signup is required before browsing, not just before ordering).

## Tech Stack

- **Backend**: Frappe Framework (Python) + ERPNext, on MariaDB + Redis
- **Payments**: Razorpay (Orders API + webhook signature verification)
- **Frontend**: React (Vite) + Tailwind CSS, deployed separately (Vercel) from the backend
- **Auth**: Token-based (Frappe API key/secret), issued via custom signup/login endpoints — no session cookies

## Local Setup

```bash
# Clone into your bench's apps folder
cd frappe-bench/apps
git clone https://github.com/nsathvik2007-ui/boardgame-cafe.git boardgame_cafe

# ERPNext is a hard dependency (required_apps in hooks.py) — fetch it first if not already present
cd ..
bench get-app erpnext --branch version-15   # match your Frappe branch

# Install both on your site
bench --site your-site.local install-app erpnext
bench --site your-site.local install-app boardgame_cafe

# Enable developer mode (needed to edit doctypes as files)
bench --site your-site.local set-config developer_mode 1
bench --site your-site.local clear-cache

bench start
```

If this is a genuinely fresh site (no ERPNext Setup Wizard ever run), also create the default masters this app assumes exist — see "Why ERPNext, not just Frappe" above:

```python
# bench --site your-site.local console
frappe.get_doc({"doctype": "Territory", "territory_name": "All Territories", "is_group": 1}).insert()
frappe.get_doc({"doctype": "Territory", "territory_name": "India", "parent_territory": "All Territories"}).insert()
frappe.get_doc({"doctype": "Customer Group", "customer_group_name": "All Customer Groups", "is_group": 1}).insert()
frappe.get_doc({"doctype": "Customer Group", "customer_group_name": "Individual", "parent_customer_group": "All Customer Groups"}).insert()
```

Configure Razorpay (test-mode keys are fine for development):

```bash
bench --site your-site.local set-config razorpay_key_id "rzp_test_..."
bench --site your-site.local set-config razorpay_key_secret "..."
bench --site your-site.local set-config razorpay_webhook_secret "..."   # optional, needed for the webhook only
```

Generate an API key (Administrator or a staff user) via **User → API Access → Generate Keys** in the desk UI for staff/admin access, or use the `customer_signup` endpoint for customer-side testing.

### Frontend setup

```bash
cd boardgame-cafe-frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` by default. Requires the backend to be running and reachable, with CORS enabled for the frontend's origin:

```bash
bench --site your-site.local set-config allow_cors "http://localhost:5173"
```

Also set `frontend_url` on the backend so table QR codes point at the right place:

```bash
bench --site your-site.local set-config frontend_url "http://localhost:5173"
```

## Deployment

A live instance runs on an Oracle Cloud free-tier VM (1 GB RAM — swap-tuned, gunicorn/worker counts scaled down accordingly), behind nginx + supervisor, with a free [sslip.io](https://sslip.io) hostname and a real Let's Encrypt certificate (no purchased domain needed). The frontend is on Vercel; CORS is scoped to its exact assigned domain. Full deployment notes (every issue hit and how it was fixed) exist as a separate write-up outside this repo — ask if you need them.

## Project Status

- [x] Core doctype schema and relationships
- [x] Game lifecycle logic (checkout locking, piece verification, unlock/relock)
- [x] Food ordering with auto-calculated pricing, staff edit/cancel, kitchen queue
- [x] Customer signup/login (token-based auth)
- [x] Row-level permission scoping
- [x] Full custom API surface for the customer and staff flows
- [x] QR code generation for tables
- [x] Staff dashboard, kitchen queue, game-return inventory check, food inventory/restock
- [x] Razorpay payment integration (order creation, signature verification, webhook fallback)
- [x] ERPNext integration for real stock (Menu Item ↔ Item) and billing (Sales Invoice on payment)
- [x] Frontend — all customer and staff pages built and deployed
- [x] Deployed end-to-end (backend on Oracle Cloud + HTTPS, frontend on Vercel)
- [ ] Automated test coverage beyond the generated doctype test stubs
- [ ] Email notifications (signup confirmation, order/payment receipts)
