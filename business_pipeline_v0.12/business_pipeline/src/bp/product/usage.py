"""What the repair loop spent (product layer, standard library only).

The repair loop spends model calls to replay a failure.  **What it spent was
never recorded**: the model's log carries the token counts, and nothing copied
them into the record the owner reads.  This module is that copy, and it is
deliberately small.

**The dollar figure is unknown until the owner says what a token costs.**  The
price table below is empty on purpose: a provider's price is the owner's
business, and a guessed price is an invented number wearing a dollar sign.
A model that is not in the table has an **unknown** cost, and an unknown cost
is reported as ``None`` - never as ``0.00``, which would read as "free" and
be wrong.

The token counts themselves are not guesses: they come from the provider's own
usage record, already carried by the model's log.
"""

import json
import os
import time

#: USD per million tokens, by model id: ``{"model-id": (input_usd, output_usd)}``.
#:
#: Empty by default.  The owner's provider prices are not this product's to
#: invent, and a wrong price would make the cost-efficiency report a lie.
#: Fill it in with the owner's own numbers, or point ``BP_MODEL_PRICES`` at a
#: JSON file of the same shape.
MODEL_PRICES = {}


def load_prices(path=None):
    """The price table: the owner's file if there is one, else the empty one."""
    source = path or os.environ.get("BP_MODEL_PRICES")
    if not source or not os.path.isfile(source):
        return dict(MODEL_PRICES)
    try:
        with open(source, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return dict(MODEL_PRICES)
    if not isinstance(data, dict):
        return dict(MODEL_PRICES)
    prices = dict(MODEL_PRICES)
    for model, value in data.items():
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            try:
                prices[str(model)] = (float(value[0]), float(value[1]))
            except (TypeError, ValueError):
                continue
        elif isinstance(value, dict):
            try:
                prices[str(model)] = (float(value.get("input", 0.0)), float(value.get("output", 0.0)))
            except (TypeError, ValueError):
                continue
    return prices


def usage_since(log, index):
    """The token usage recorded after ``index`` entries of a model's log.

    The log is the model's own record of each call; this reads the entries a
    call added and nothing else.
    """
    records = list(log or [])[int(index or 0):]
    out = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "models": {}}
    for record in records:
        if not isinstance(record, dict):
            continue
        model = str(record.get("model") or "unknown")
        row = out["models"].setdefault(model, {"calls": 0, "input_tokens": 0,
                                               "output_tokens": 0, "seconds": 0.0})
        for key in ("input_tokens", "output_tokens"):
            try:
                value = int(record.get(key) or 0)
            except (TypeError, ValueError):
                value = 0
            out[key] += value
            row[key] += value
        try:
            seconds = float(record.get("seconds") or 0.0)
        except (TypeError, ValueError):
            seconds = 0.0
        out["seconds"] += seconds
        row["seconds"] += seconds
        out["calls"] += 1
        row["calls"] += 1
    return out


def cost_of(usage, prices=None):
    """The dollar cost of a usage record, or None when it is unknown.

    ``None`` means "not priced".  It never means "free".
    """
    table = load_prices() if prices is None else prices
    if not usage or not usage.get("calls"):
        return 0.0 if usage else None
    total = 0.0
    for model, row in (usage.get("models") or {}).items():
        price = table.get(model)
        if not price:
            return None
        try:
            per_in, per_out = float(price[0]), float(price[1])
        except (TypeError, ValueError, IndexError):
            return None
        total += (row.get("input_tokens", 0) / 1000000.0) * per_in
        total += (row.get("output_tokens", 0) / 1000000.0) * per_out
    return round(total, 6)


def add(left, right):
    """Two usage records added together."""
    out = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "models": {}}
    for record in (left, right):
        if not record:
            continue
        out["calls"] += int(record.get("calls") or 0)
        out["input_tokens"] += int(record.get("input_tokens") or 0)
        out["output_tokens"] += int(record.get("output_tokens") or 0)
        try:
            out["seconds"] += float(record.get("seconds") or 0.0)
        except (TypeError, ValueError):
            pass
        for model, row in (record.get("models") or {}).items():
            merged = out["models"].setdefault(model, {"calls": 0, "input_tokens": 0,
                                                      "output_tokens": 0, "seconds": 0.0})
            for key in ("calls", "input_tokens", "output_tokens"):
                merged[key] += int(row.get(key) or 0)
            try:
                merged["seconds"] += float(row.get("seconds") or 0.0)
            except (TypeError, ValueError):
                pass
    return out


class Ledger:
    """The usage of one process, for the calls the product makes itself."""

    def __init__(self):
        self._records = []

    def record(self, record):
        """Record one model call's usage.  Returns the record."""
        entry = {
            "ts": time.time(),
            "model": str((record or {}).get("model") or "unknown"),
            "input_tokens": int((record or {}).get("input_tokens") or 0),
            "output_tokens": int((record or {}).get("output_tokens") or 0),
            "seconds": float((record or {}).get("seconds") or 0.0),
        }
        self._records.append(entry)
        return entry

    def usage(self):
        """Everything recorded so far, as one usage record."""
        return usage_since(self._records, 0)

    def cost(self, prices=None):
        """What it cost, or None when the model is not priced."""
        return cost_of(self.usage(), prices=prices)

    def rows(self):
        return list(self._records)
