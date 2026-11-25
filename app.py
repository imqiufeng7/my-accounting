from __future__ import annotations

from flask import Flask, abort, redirect, render_template, request, session, url_for

import config
from ledger import aggregator, auth, clock, preferences, settlement, storage

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY
app.jinja_env.globals["csrf_token"] = auth.csrf_token

EXPENSE_MODES = ("personal", "work", "travel")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.before_request
def verify_csrf():
    """所有會改資料的 POST 都必須帶正確的 CSRF token，防止跨站偽造請求（例如惡意網站偷偷刪帳）。"""
    if request.method != "POST":
        return None
    if not auth.csrf_is_valid(request.form.get(auth.CSRF_FORM_FIELD)):
        abort(400, description="表單已過期或來源不明，請重新整理頁面後再送出。")
    return None


@app.before_request
def require_login():
    if request.endpoint in auth.PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if not session.get("logged_in"):
        return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if auth.check_password(request.form.get("password", "")):
            session["logged_in"] = True
            return redirect(auth.safe_next_url(request.args.get("next")) or url_for("dashboard"))
        error = "密碼錯誤"
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    ledger_rows = aggregator.load_master_ledger()
    return render_template(
        "dashboard.html",
        ledger_rows=ledger_rows[:30],
        totals=aggregator.totals_by_mode(ledger_rows),
        net_worth=aggregator.net_worth_summary(),
    )


# ---------------------------------------------------------------------------
# Expense modes: personal / work / travel
# ---------------------------------------------------------------------------

def _mode_or_404(mode: str) -> dict:
    if mode not in EXPENSE_MODES:
        abort(404)
    return config.MODE_CONFIG[mode]


def _form_to_row(cfg: dict, form) -> dict:
    row = {field: form.get(field, "").strip() for field in cfg["fields"] if field != "id"}
    if not row.get("匯率"):
        row["匯率"] = "1"
    return row


@app.route("/<mode>", methods=["GET", "POST"])
def mode_entries(mode):
    cfg = _mode_or_404(mode)
    if request.method == "POST":
        row = _form_to_row(cfg, request.form)
        storage.append_row(cfg["file"], cfg["fields"], row)
        return redirect(url_for("mode_entries", mode=mode))

    rows = storage.read_rows(cfg["file"], cfg["fields"])
    rows.sort(key=lambda r: r.get("日期", ""), reverse=True)
    settings = preferences.load_settings()
    accounts = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    return render_template(
        "entries.html",
        mode=mode,
        cfg=cfg,
        rows=rows,
        today=clock.today_str(),
        settings=settings,
        accounts=accounts,
    )


@app.route("/<mode>/batch", methods=["GET", "POST"])
def mode_batch(mode):
    cfg = _mode_or_404(mode)
    if request.method == "POST":
        header = {field: request.form.get(field, "").strip() for field in cfg["fields"] if field != "id"}
        if not header.get("匯率"):
            header["匯率"] = "1"

        items = request.form.getlist("項目[]")
        amounts = request.form.getlist("金額[]")
        for item, amount in zip(items, amounts):
            item, amount = item.strip(), amount.strip()
            if not item or not amount:
                continue
            row = dict(header)
            row["項目"] = item
            row["金額"] = amount
            storage.append_row(cfg["file"], cfg["fields"], row)
        return redirect(url_for("mode_entries", mode=mode))

    settings = preferences.load_settings()
    accounts = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    return render_template(
        "batch_entries.html",
        mode=mode,
        cfg=cfg,
        today=clock.today_str(),
        settings=settings,
        accounts=accounts,
    )


@app.route("/<mode>/<row_id>/edit", methods=["GET", "POST"])
def mode_edit(mode, row_id):
    cfg = _mode_or_404(mode)
    rows = storage.read_rows(cfg["file"], cfg["fields"])
    row = next((r for r in rows if r["id"] == row_id), None)
    if row is None:
        abort(404)

    if request.method == "POST":
        updates = _form_to_row(cfg, request.form)
        storage.update_row(cfg["file"], cfg["fields"], row_id, updates)
        return redirect(url_for("mode_entries", mode=mode))

    accounts = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    return render_template(
        "entries.html",
        mode=mode,
        cfg=cfg,
        rows=[],
        edit_row=row,
        accounts=accounts,
        today=clock.today_str(),
        settings=preferences.load_settings(),
    )


@app.route("/<mode>/<row_id>/delete", methods=["POST"])
def mode_delete(mode, row_id):
    cfg = _mode_or_404(mode)
    storage.delete_row(cfg["file"], cfg["fields"], row_id)
    return redirect(url_for("mode_entries", mode=mode))


# ---------------------------------------------------------------------------
# Travel settlement + sharing
# ---------------------------------------------------------------------------

@app.route("/travel/settlement", methods=["GET", "POST"])
def travel_settlement():
    cfg = config.MODE_CONFIG["travel"]
    rows = storage.read_rows(cfg["file"], cfg["fields"])
    destinations = sorted({r["目的地"] for r in rows if r.get("目的地")})

    destination = request.values.get("目的地") or (destinations[0] if destinations else "")
    share_url = None

    if request.method == "POST" and request.form.get("action") == "share":
        destination = request.form.get("目的地", "")
        if destination:
            token = auth.get_or_create_share_token(destination)
            share_url = url_for("share_travel", token=token, _external=True)

    balances, transactions, trip_rows = _compute_trip_settlement(rows, destination)

    return render_template(
        "travel_settlement.html",
        destinations=destinations,
        destination=destination,
        balances=balances,
        transactions=transactions,
        trip_rows=trip_rows,
        share_url=share_url,
    )


def _compute_trip_settlement(rows, destination):
    trip_rows = [r for r in rows if r.get("目的地") == destination]
    entries = []
    for r in trip_rows:
        entries.append({
            "付款人": r.get("付款人", ""),
            "分攤對象": r.get("分攤對象", ""),
            "amount_twd": aggregator.amount_twd(r),
        })
    balances = settlement.compute_balances(entries)
    transactions = settlement.simplify_debts(balances)
    trip_rows_sorted = sorted(trip_rows, key=lambda r: r.get("日期", ""))
    return balances, transactions, trip_rows_sorted


@app.route("/share/travel/<token>")
def share_travel(token):
    destination = auth.resolve_share_token(token)
    if destination is None:
        abort(404)

    cfg = config.MODE_CONFIG["travel"]
    rows = storage.read_rows(cfg["file"], cfg["fields"])
    balances, transactions, trip_rows = _compute_trip_settlement(rows, destination)

    return render_template(
        "travel_share_view.html",
        destination=destination,
        balances=balances,
        transactions=transactions,
        trip_rows=trip_rows,
    )


# ---------------------------------------------------------------------------
# Stock mode
# ---------------------------------------------------------------------------

@app.route("/stock", methods=["GET", "POST"])
def stock():
    if request.method == "POST":
        row = {field: request.form.get(field, "").strip() for field in config.STOCK_FIELDS if field != "id"}
        if not row.get("匯率"):
            row["匯率"] = "1"
        storage.append_row(config.STOCK_FILE, config.STOCK_FIELDS, row)
        return redirect(url_for("stock"))

    rows = storage.read_rows(config.STOCK_FILE, config.STOCK_FIELDS)
    rows.sort(key=lambda r: r.get("日期", ""), reverse=True)
    holdings = aggregator.stock_holdings()
    accounts = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    return render_template(
        "stock.html", rows=rows, holdings=holdings, today=clock.today_str(), accounts=accounts
    )


@app.route("/stock/<row_id>/edit", methods=["GET", "POST"])
def stock_edit(row_id):
    rows = storage.read_rows(config.STOCK_FILE, config.STOCK_FIELDS)
    row = next((r for r in rows if r["id"] == row_id), None)
    if row is None:
        abort(404)

    if request.method == "POST":
        updates = {field: request.form.get(field, "").strip() for field in config.STOCK_FIELDS if field != "id"}
        storage.update_row(config.STOCK_FILE, config.STOCK_FIELDS, row_id, updates)
        return redirect(url_for("stock"))

    accounts = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    return render_template(
        "stock.html", rows=[], edit_row=row, holdings={}, accounts=accounts, today=clock.today_str()
    )


@app.route("/stock/<row_id>/delete", methods=["POST"])
def stock_delete(row_id):
    storage.delete_row(config.STOCK_FILE, config.STOCK_FIELDS, row_id)
    return redirect(url_for("stock"))


@app.route("/stock/prices", methods=["GET", "POST"])
def stock_prices():
    if request.method == "POST":
        symbol = request.form.get("股票代號", "").strip()
        if symbol:
            storage.upsert_keyed_row(
                config.STOCK_PRICES_FILE,
                config.STOCK_PRICES_FIELDS,
                "股票代號",
                symbol,
                {
                    "目前市價": request.form.get("目前市價", "").strip(),
                    "幣別": request.form.get("幣別", "").strip() or "TWD",
                    "匯率": request.form.get("匯率", "").strip() or "1",
                    "更新日期": clock.today_str(),
                },
            )
        return redirect(url_for("stock_prices"))

    rows = storage.read_rows(config.STOCK_PRICES_FILE, config.STOCK_PRICES_FIELDS)
    holdings = aggregator.stock_holdings()
    return render_template("stock_prices.html", rows=rows, holdings=holdings)


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@app.route("/accounts", methods=["GET", "POST"])
def accounts():
    if request.method == "POST":
        name = request.form.get("帳戶名稱", "").strip()
        if name:
            storage.upsert_keyed_row(
                config.ACCOUNTS_FILE,
                config.ACCOUNTS_FIELDS,
                "帳戶名稱",
                name,
                {field: request.form.get(field, "").strip() for field in config.ACCOUNTS_FIELDS if field != "帳戶名稱"},
            )
        return redirect(url_for("accounts"))

    rows = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    _, details = aggregator.account_balances()
    balances_by_name = {d["name"]: d["balance_twd"] for d in details}
    return render_template(
        "accounts.html", rows=rows, balances_by_name=balances_by_name, today=clock.today_str()
    )


# 用 path 轉換器：帳戶名稱可能含「/」（例如「台新/信用卡」），預設的字串轉換器會比對不到
@app.route("/accounts/<path:name>/delete", methods=["POST"])
def account_delete(name):
    storage.delete_keyed_row(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS, "帳戶名稱", name)
    return redirect(url_for("accounts"))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
def settings_view():
    if request.method == "POST":
        preferences.save_settings({
            "預設付款人": request.form.get("預設付款人", "").strip(),
            "預設付款方式": request.form.get("預設付款方式", "").strip(),
        })
        return redirect(url_for("settings_view"))

    accounts_rows = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    return render_template("settings.html", settings=preferences.load_settings(), accounts=accounts_rows)


application = app  # PythonAnywhere WSGI entry point convention

if __name__ == "__main__":
    app.run(debug=True)
