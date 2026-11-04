"""Sign convention guard (G1).

The ONLY place in the codebase that flips a sign. tb.balance(code) is debit-positive
everywhere; presentation_sign converts to the statement's presentation sign.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict


class SignConvention:
    @staticmethod
    def for_statement(account_meta: Dict[str, Any], raw: Decimal) -> Decimal:
        raw = Decimal(str(raw))
        stmt = account_meta.get("statement")
        normal = account_meta.get("normal")
        contra = bool(account_meta.get("contra"))
        if stmt == "IS":
            return -raw if normal == "credit" else raw
        if stmt == "BS":
            if account_meta.get("type") == "asset":
                return -raw if contra else raw
            else:  # liability, equity
                return raw if contra else -raw
        if stmt == "CF":
            raise RuntimeError("CF must not read tb.balance() directly")
        return raw


def delta_wc(tb_begin, tb_end, accounts):
    """Working-capital cash effect: -(change in debit-positive balance)."""
    out = {}
    for code, m in accounts.items():
        if m.get("cf_bucket") == "operating_working_capital":
            out[code] = -(tb_end.balance(code) - tb_begin.balance(code))
    return out
