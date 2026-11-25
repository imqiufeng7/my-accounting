from __future__ import annotations

import config
from ledger import clock, storage


def to_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def amount_twd(row: dict) -> float:
    return to_float(row.get("金額")) * to_float(row.get("匯率"), 1.0)


def load_mode_rows(mode: str) -> list[dict]:
    cfg = config.MODE_CONFIG[mode]
    return storage.read_rows(cfg["file"], cfg["fields"])


def load_master_ledger() -> list[dict]:
    """Merge personal/work/travel entries, each tagged with its source mode and TWD amount."""
    merged = []
    for mode in ("personal", "work", "travel"):
        for row in load_mode_rows(mode):
            entry = dict(row)
            entry["模式"] = config.MODE_CONFIG[mode]["label"]
            entry["_mode"] = mode
            entry["amount_twd"] = amount_twd(row)
            merged.append(entry)
    merged.sort(key=lambda r: r.get("日期", ""), reverse=True)
    return merged


def totals_by_mode(ledger_rows: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in ledger_rows:
        totals[row["模式"]] = totals.get(row["模式"], 0) + row["amount_twd"]
    return {k: round(v, 2) for k, v in totals.items()}


def stock_holdings() -> dict[str, float]:
    """symbol -> net shares held (buys minus sells)."""
    holdings: dict[str, float] = {}
    for row in storage.read_rows(config.STOCK_FILE, config.STOCK_FIELDS):
        symbol = row.get("股票代號", "").strip()
        if not symbol:
            continue
        qty = to_float(row.get("股數"))
        if row.get("交易類型") == "賣":
            qty = -qty
        holdings[symbol] = holdings.get(symbol, 0) + qty
    return holdings


def stock_market_value() -> tuple[float, list[dict]]:
    """Returns (total_twd, [{symbol, shares, price, value_twd}, ...])."""
    holdings = stock_holdings()
    prices = {
        row["股票代號"]: row
        for row in storage.read_rows(config.STOCK_PRICES_FILE, config.STOCK_PRICES_FIELDS)
    }

    details = []
    total = 0.0
    for symbol, shares in holdings.items():
        if abs(shares) < 1e-9:
            continue
        price_row = prices.get(symbol, {})
        price = to_float(price_row.get("目前市價"))
        rate = to_float(price_row.get("匯率"), 1.0)
        value = shares * price * rate
        total += value
        details.append({
            "symbol": symbol,
            "shares": shares,
            "price": price,
            "currency": price_row.get("幣別", ""),
            "value_twd": round(value, 2),
        })

    return round(total, 2), details


def stock_cash_flow_twd(row: dict) -> float:
    """Cash impact of a stock transaction on its 付款方式 account: negative for buys, positive for sells."""
    rate = to_float(row.get("匯率"), 1.0)
    gross = to_float(row.get("股數")) * to_float(row.get("單價")) * rate
    fee = to_float(row.get("手續費")) * rate
    if row.get("交易類型") == "賣":
        return gross - fee
    return -(gross + fee)


def account_balances() -> tuple[float, list[dict]]:
    """Returns (total_twd, [{name, type, balance_twd}, ...])."""
    accounts = storage.read_rows(config.ACCOUNTS_FILE, config.ACCOUNTS_FIELDS)
    ledger_rows = load_master_ledger()
    stock_rows = storage.read_rows(config.STOCK_FILE, config.STOCK_FIELDS)

    details = []
    total = 0.0
    for account in accounts:
        name = account.get("帳戶名稱", "").strip()
        if not name:
            continue
        starting_balance = to_float(account.get("期初餘額")) * to_float(account.get("匯率"), 1.0)
        start_date = account.get("期初日期", "") or "0000-00-00"

        spent = sum(
            row["amount_twd"]
            for row in ledger_rows
            if row.get("付款方式") == name and row.get("日期", "") >= start_date
        )
        stock_cash_flow = sum(
            stock_cash_flow_twd(row)
            for row in stock_rows
            if row.get("付款方式") == name and row.get("日期", "") >= start_date
        )
        balance = starting_balance - spent + stock_cash_flow
        total += balance
        details.append({
            "name": name,
            "type": account.get("類型", ""),
            "balance_twd": round(balance, 2),
        })

    return round(total, 2), details


def net_worth_summary() -> dict:
    account_total, account_details = account_balances()
    stock_total, stock_details = stock_market_value()
    return {
        "account_total": account_total,
        "accounts": account_details,
        "stock_total": stock_total,
        "stocks": stock_details,
        "grand_total": round(account_total + stock_total, 2),
    }


def today_str() -> str:
    return clock.today_str()
