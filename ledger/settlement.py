from __future__ import annotations
def parse_shares(shares_text: str, amount: float, payer: str) -> dict[str, float]:
    """Parse the 分攤對象 mini-syntax into {person: owed_amount}.

    "Alice,Bob,Charlie"  -> equal split
    "Alice:2,Bob:1"       -> weighted split
    ""                    -> payer covers it alone (not shared)
    """
    text = (shares_text or "").strip()
    if not text:
        return {payer: amount}

    entries = [part.strip() for part in text.split(",") if part.strip()]
    weights: dict[str, float] = {}
    for entry in entries:
        if ":" in entry:
            name, weight = entry.split(":", 1)
            weights[name.strip()] = weights.get(name.strip(), 0) + float(weight)
        else:
            weights[entry] = weights.get(entry, 0) + 1

    total_weight = sum(weights.values())
    if total_weight <= 0:
        return {payer: amount}

    shares = {name: amount * weight / total_weight for name, weight in weights.items()}

    # Fix up rounding so the shares sum exactly to `amount`.
    diff = round(amount - sum(shares.values()), 2)
    if diff and shares:
        last_person = list(shares.keys())[-1]
        shares[last_person] = round(shares[last_person] + diff, 2)

    return {name: round(v, 2) for name, v in shares.items()}


def compute_balances(entries: list[dict]) -> dict[str, float]:
    """entries: list of {"付款人": str, "分攤對象": str, "amount_twd": float}."""
    balances: dict[str, float] = {}
    for entry in entries:
        payer = entry["付款人"].strip()
        amount = entry["amount_twd"]
        if not payer:
            continue
        balances[payer] = balances.get(payer, 0) + amount

        shares = parse_shares(entry.get("分攤對象", ""), amount, payer)
        for person, owed in shares.items():
            balances[person] = balances.get(person, 0) - owed

    return {name: round(v, 2) for name, v in balances.items()}


def simplify_debts(balances: dict[str, float]) -> list[tuple[str, str, float]]:
    """Greedy largest-debtor-pays-largest-creditor debt simplification."""
    creditors = sorted([[n, a] for n, a in balances.items() if a > 0.01], key=lambda x: -x[1])
    debtors = sorted([[n, -a] for n, a in balances.items() if a < -0.01], key=lambda x: -x[1])

    transactions: list[tuple[str, str, float]] = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        debtor_name, debtor_amount = debtors[i]
        creditor_name, creditor_amount = creditors[j]
        pay = round(min(debtor_amount, creditor_amount), 2)
        if pay > 0:
            transactions.append((debtor_name, creditor_name, pay))
        debtors[i][1] -= pay
        creditors[j][1] -= pay
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return transactions
