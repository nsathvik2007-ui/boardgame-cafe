# Board Game Café Management System

A unified backend system for a board game café, built on the [Frappe Framework](https://frappeframework.com/). It manages the full customer lifecycle — QR-based table check-in, live game library browsing with piece-level inventory tracking, and food ordering — all tied together through a single session model.

## The Problem

Board game cafés typically juggle two disconnected systems: one for tracking game inventory (which is fragile — games have hundreds of small pieces that go missing) and another for food/table service. This project unifies both under a single **Customer Session**, so a customer's entire visit — from sitting down, to borrowing a game, to ordering food, to leaving — is tracked coherently in one place.

It also solves a specific, often-overlooked problem in board game cafés: **incomplete games silently get re-rented**. This system enforces a locking mechanism so a game copy can never be checked out again until a staff member has verified all its pieces are present.

## Core Concept

Everything hangs off **Customer Session** — created automatically when a customer scans a QR code at their table and logs in. From there, they can browse available games (with live copy counts), check out a game, and place food orders, all scoped to that one session.

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
        └──► Browse Menu ──► Place Food Order ──► Bill auto-updates on Session
                                    │
                                    ▼
                              End Session (table freed for cleaning)
```

## Doctypes (Data Model)

| Doctype | Purpose |
|---|---|
| **Game Title** | Master data for a game (name, category, player count, complexity) |
| **Game Copy** | A physical copy of a game, with lifecycle status (`Available` → `Checked Out` → `Under Repair` → `Available`/`Missing Pieces` → `Retired`) |
| **Table** | Physical café table with zone and occupancy status |
| **Customer Session** | The hub — one record per visit, links customer, table, and running bill |
| **Game Checkout** | A borrow record; blocks checkout of unavailable copies via `validate()` |
| **Piece Inventory Check** | Logged when a returned copy is verified; auto-calculates discrepancy and unlocks/relocks the copy |
| **Menu Item** | Food/beverage master data |
| **Food Order** | Order tied to a session, with a child table of line items |
| **Food Order Item** *(child table)* | Individual line item; auto-calculates rate and amount |

### Key design decisions worth noting

- **`Retired` instead of delete**: Game Copies are never deleted, even when out of circulation — this preserves the link integrity of historical `Game Checkout` records and keeps an audit trail.
- **Piece-check locking**: A returned game copy goes to `Under Repair` (not directly back to `Available`) until a `Piece Inventory Check` confirms the count matches. This prevents an incomplete game from being silently re-rented.
- **Session as hub, not per-feature accounts**: Rather than separate systems for games and food, both link through `Customer Session`, so the café gets one coherent bill and one coherent history per visit.

## Custom API Endpoints

Beyond Frappe's default REST API (`/api/resource/<doctype>`), this app exposes purpose-built endpoints for the actual customer flow:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/method/boardgame_cafe.api.customer_signup` | POST | Creates a Website User account, returns an API key/secret pair |
| `/api/method/boardgame_cafe.api.customer_login` | POST | Verifies credentials, returns the user's existing API key/secret |
| `/api/method/boardgame_cafe.api.checkin` | POST | QR-triggered: finds or creates an active session for a table |
| `/api/method/boardgame_cafe.api.get_available_games` | GET | Returns all games with live available-copy counts (auth required) |
| `/api/method/boardgame_cafe.api.checkout_game` | POST | Checks out a game copy to a session (enforces availability) |
| `/api/method/boardgame_cafe.api.place_food_order` | POST | Places a multi-item food order, auto-calculates totals |
| `/api/method/boardgame_cafe.api.end_session` | POST | Closes out a session and frees the table for cleaning |

## Authentication & Permissions

- **Customers** are Frappe **Website Users**, authenticated via **token-based auth** (API key/secret pair), not session cookies. On signup or login, the backend generates/returns an `api_key` and `api_secret`, which the frontend stores (e.g. in `localStorage`) and attaches to every subsequent request as `Authorization: token {api_key}:{api_secret}`.
  - This was a deliberate choice over cookie-based session auth: the frontend is a separately-run app (different origin/port from the Frappe backend), and cross-site cookies bring real friction (`SameSite` restrictions, CORS-with-credentials limitations, browser third-party cookie crackdowns). A bearer token avoids all of that.
  - Tradeoff, stated plainly: `api_secret` is stored retrievably server-side so it can be re-issued on login, rather than using short-lived rotating tokens. This is a deliberate simplification appropriate for this project's scope, not a production-grade token strategy.
- **Staff/Admin** use the same API key/secret mechanism, generated manually via the desk UI (**User → API Access → Generate Keys**).
- **Row-level permission scoping**: Customers can only see their own `Customer Session`, `Game Checkout`, and `Food Order` records, enforced via `permission_query_conditions` hooks — not just default doctype permissions.
- Game and menu browsing require authentication (a deliberate product choice — signup is required before browsing, not just before ordering).

## Tech Stack

- **Backend**: Frappe Framework (Python) on MariaDB
- **Frontend**: React (Vite) + Tailwind CSS, deployed/run separately from the backend
- **Auth**: Token-based (Frappe API key/secret), issued via custom signup/login endpoints — no session cookies

## Local Setup

```bash
# Clone into your bench's apps folder
cd frappe-bench/apps
git clone https://github.com/nsathvik2007-ui/boardgame-cafe.git boardgame_cafe

# Install on your site
cd ..
bench --site your-site.local install-app boardgame_cafe

# Enable developer mode (needed to edit doctypes as files)
bench --site your-site.local set-config developer_mode 1
bench --site your-site.local clear-cache

bench start
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

## Project Status

- [x] Core doctype schema and relationships
- [x] Game lifecycle logic (checkout locking, piece verification, unlock/relock)
- [x] Food ordering with auto-calculated pricing
- [x] Customer signup/login (session-based auth)
- [x] Row-level permission scoping
- [x] Custom API endpoints for the full customer flow
- [x] Token-based customer authentication
- [ ] Frontend — in progress (Login/Signup page built)
- [ ] QR code generation for tables
- [ ] Staff-facing reports/dashboard

## Author

Built as a college project by [Your Name] to explore Frappe Framework, REST API design, and session-based authentication beyond typical CRUD tutorials.
