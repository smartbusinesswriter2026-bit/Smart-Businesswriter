"""Timing rule engine (G4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .money import q


def months_expired(coverage_start: date, coverage_end: date, year_end: date) -> int:
    if year_end < coverage_start:
        return 0
    if year_end >= coverage_end:
        return (coverage_end.year - coverage_start.year) * 12 + (coverage_end.month - coverage_start.month)
    return (year_end.year - coverage_start.year) * 12 + (year_end.month - coverage_start.month) + 1


def depreciation_for_year(cost, salvage, life_years, acquired: date, year_end: date,
                         convention: str) -> Decimal:
    annual = (Decimal(str(cost)) - Decimal(str(salvage))) / Decimal(str(life_years))
    if convention == "full_year":
        return q(annual)
    if convention == "pro_rata":
        months = (year_end.year - acquired.year) * 12 + (year_end.month - acquired.month) + 1
        months = min(max(months, 0), 12)
        return q(annual * Decimal(months) / Decimal(12))
    if convention == "half_year":
        return q(annual / Decimal(2))
    raise ValueError(f"unknown convention: {convention}")


def resolve_depreciation_convention(text: str):
    low = text.lower()
    if "full year of depreciation" in low or "full-year depreciation" in low:
        return "full_year"
    if "pro-rata" in low or "proportional" in low or "pro rata" in low:
        return "pro_rata"
    if "half-year" in low or "half year" in low:
        return "half_year"
    return None


def resolve_interest_timing(text: str):
    low = text.lower()
    if "interest paid annually" in low or "interest paid on dec. 31" in low or "interest paid on dec 31" in low:
        return "annual"
    if "interest is paid in full at maturity" in low or "no annual interest" in low or "paid at maturity" in low:
        return "at_maturity"
    return None
