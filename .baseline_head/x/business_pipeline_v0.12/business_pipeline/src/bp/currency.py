"""Currency registry and declared-rate conversion (B-069). Standard library only.

What this module is: a DECLARED ISO 4217 table of currency codes with their minor units (the number of
decimal places the currency uses), so money is rendered and rounded per currency instead of always at two
places — JPY has none, KWD has three — plus exact Decimal conversion at a rate the owner DECLARES.

What this module is not: an FX price source. No exchange rate is retrieved, guessed or hard-coded as real:
a conversion requires a declared rate and records where it came from. A rate date and source may be
recorded but are the owner's declarations, not verified facts. This is the same rule the retrieval boundary
uses for citations (REW §9) and the same rule taxation was deferred under (B-052).

The table is ISO 4217 monetary codes with a defined minor unit. Metals (XAU, XAG, XPT, XPD), testing and
"no currency" codes (XTS, XXX) and units of account without minor units (XDR) are not accepted; they are not
currencies in the sense used here.
"""
from decimal import Decimal as D, InvalidOperation

class CurrencyError(ValueError):
    """Unknown currency code, invalid rate, or a multi-currency operation that would need an unknown rate."""

# code: (name, minor units) — ISO 4217, declared table (verify against the standard when precision matters)
_CURRENCIES = {
    "AED": ("UAE dirham", 2), "AFN": ("Afghan afghani", 2), "ALL": ("Albanian lek", 2), "AMD": ("Armenian dram", 2),
    "ANG": ("Netherlands Antillean guilder", 2), "AOA": ("Angolan kwanza", 2), "ARS": ("Argentine peso", 2),
    "AUD": ("Australian dollar", 2), "AWG": ("Aruban florin", 2), "AZN": ("Azerbaijani manat", 2),
    "BAM": ("Bosnia-Herzegovina convertible mark", 2), "BBD": ("Barbadian dollar", 2), "BDT": ("Bangladeshi taka", 2),
    "BGN": ("Bulgarian lev", 2), "BHD": ("Bahraini dinar", 3), "BIF": ("Burundian franc", 0),
    "BMD": ("Bermudian dollar", 2), "BND": ("Brunei dollar", 2), "BOB": ("Bolivian boliviano", 2),
    "BOV": ("Bolivian Mvdol (fund)", 2), "BRL": ("Brazilian real", 2), "BSD": ("Bahamian dollar", 2),
    "BTN": ("Bhutanese ngultrum", 2), "BWP": ("Botswana pula", 2), "BYN": ("Belarusian ruble", 2),
    "BZD": ("Belize dollar", 2), "CAD": ("Canadian dollar", 2), "CDF": ("Congolese franc", 2),
    "CHE": ("WIR euro (complementary)", 2), "CHF": ("Swiss franc", 2), "CHW": ("WIR franc (complementary)", 2),
    "CLF": ("Unidad de Fomento (fund)", 4), "CLP": ("Chilean peso", 0), "CNY": ("Chinese yuan", 2),
    "COP": ("Colombian peso", 2), "COU": ("Unidad de Valor Real (fund)", 2), "CRC": ("Costa Rican colon", 2),
    "CUP": ("Cuban peso", 2), "CVE": ("Cape Verdean escudo", 2), "CZK": ("Czech koruna", 2),
    "DJF": ("Djiboutian franc", 0), "DKK": ("Danish krone", 2), "DOP": ("Dominican peso", 2),
    "DZD": ("Algerian dinar", 2), "EGP": ("Egyptian pound", 2), "ERN": ("Eritrean nakfa", 2),
    "ETB": ("Ethiopian birr", 2), "EUR": ("Euro", 2), "FJD": ("Fijian dollar", 2), "FKP": ("Falkland Islands pound", 2),
    "GBP": ("Pound sterling", 2), "GEL": ("Georgian lari", 2), "GHS": ("Ghanaian cedi", 2), "GIP": ("Gibraltar pound", 2),
    "GMD": ("Gambian dalasi", 2), "GNF": ("Guinean franc", 0), "GTQ": ("Guatemalan quetzal", 2),
    "GYD": ("Guyanese dollar", 2), "HKD": ("Hong Kong dollar", 2), "HNL": ("Honduran lempira", 2),
    "HTG": ("Haitian gourde", 2), "HUF": ("Hungarian forint", 2), "IDR": ("Indonesian rupiah", 2),
    "ILS": ("Israeli new shekel", 2), "INR": ("Indian rupee", 2), "IQD": ("Iraqi dinar", 3), "IRR": ("Iranian rial", 2),
    "ISK": ("Icelandic krona", 0), "JMD": ("Jamaican dollar", 2), "JOD": ("Jordanian dinar", 3),
    "JPY": ("Japanese yen", 0), "KES": ("Kenyan shilling", 2), "KGS": ("Kyrgyzstani som", 2),
    "KHR": ("Cambodian riel", 2), "KMF": ("Comorian franc", 0), "KPW": ("North Korean won", 2),
    "KRW": ("South Korean won", 0), "KWD": ("Kuwaiti dinar", 3), "KYD": ("Cayman Islands dollar", 2),
    "KZT": ("Kazakhstani tenge", 2), "LAK": ("Lao kip", 2), "LBP": ("Lebanese pound", 2), "LKR": ("Sri Lankan rupee", 2),
    "LRD": ("Liberian dollar", 2), "LSL": ("Lesotho loti", 2), "LYD": ("Libyan dinar", 3), "MAD": ("Moroccan dirham", 2),
    "MDL": ("Moldovan leu", 2), "MGA": ("Malagasy ariary", 2), "MKD": ("Macedonian denar", 2), "MMK": ("Myanmar kyat", 2),
    "MNT": ("Mongolian tugrik", 2), "MOP": ("Macanese pataca", 2), "MRU": ("Mauritanian ouguiya", 2),
    "MUR": ("Mauritian rupee", 2), "MVR": ("Maldivian rufiyaa", 2), "MWK": ("Malawian kwacha", 2),
    "MXN": ("Mexican peso", 2), "MXV": ("Mexican Unidad de Inversion (fund)", 2), "MYR": ("Malaysian ringgit", 2),
    "MZN": ("Mozambican metical", 2), "NAD": ("Namibian dollar", 2), "NGN": ("Nigerian naira", 2),
    "NIO": ("Nicaraguan cordoba", 2), "NOK": ("Norwegian krone", 2), "NPR": ("Nepalese rupee", 2),
    "NZD": ("New Zealand dollar", 2), "OMR": ("Omani rial", 3), "PAB": ("Panamanian balboa", 2),
    "PEN": ("Peruvian sol", 2), "PGK": ("Papua New Guinean kina", 2), "PHP": ("Philippine peso", 2),
    "PKR": ("Pakistani rupee", 2), "PLN": ("Polish zloty", 2), "PYG": ("Paraguayan guarani", 0),
    "QAR": ("Qatari riyal", 2), "RON": ("Romanian leu", 2), "RSD": ("Serbian dinar", 2), "RUB": ("Russian ruble", 2),
    "RWF": ("Rwandan franc", 0), "SAR": ("Saudi riyal", 2), "SBD": ("Solomon Islands dollar", 2),
    "SCR": ("Seychellois rupee", 2), "SDG": ("Sudanese pound", 2), "SEK": ("Swedish krona", 2),
    "SGD": ("Singapore dollar", 2), "SHP": ("Saint Helena pound", 2), "SLE": ("Sierra Leonean leone", 2),
    "SOS": ("Somali shilling", 2), "SRD": ("Surinamese dollar", 2), "SSP": ("South Sudanese pound", 2),
    "STN": ("Sao Tome and Principe dobra", 2), "SVC": ("Salvadoran colon", 2), "SYP": ("Syrian pound", 2),
    "SZL": ("Eswatini lilangeni", 2), "THB": ("Thai baht", 2), "TJS": ("Tajikistani somoni", 2),
    "TMT": ("Turkmenistani manat", 2), "TND": ("Tunisian dinar", 3), "TOP": ("Tongan pa'anga", 2),
    "TRY": ("Turkish lira", 2), "TTD": ("Trinidad and Tobago dollar", 2), "TWD": ("New Taiwan dollar", 2),
    "TZS": ("Tanzanian shilling", 2), "UAH": ("Ukrainian hryvnia", 2), "UGX": ("Ugandan shilling", 0),
    "USD": ("United States dollar", 2), "USN": ("United States dollar (next day, fund)", 2),
    "UYI": ("Uruguay Peso en Unidades Indexadas (fund)", 0), "UYU": ("Uruguayan peso", 2),
    "UYW": ("Unidad Previsional (fund)", 4), "UZS": ("Uzbekistani som", 2), "VED": ("Venezuelan digital bolivar", 2),
    "VES": ("Venezuelan bolivar", 2), "VND": ("Vietnamese dong", 0), "VUV": ("Vanuatu vatu", 0),
    "WST": ("Samoan tala", 2), "XAF": ("Central African CFA franc", 0), "XCD": ("East Caribbean dollar", 2),
    "XOF": ("West African CFA franc", 0), "XPF": ("CFP franc", 0), "YER": ("Yemeni rial", 2),
    "ZAR": ("South African rand", 2), "ZMW": ("Zambian kwacha", 2), "ZWL": ("Zimbabwean dollar", 2),
}

def codes(): return sorted(_CURRENCIES)

def catalog():
    """List for the API/UI: code, name, minor units, sorted by code."""
    return [{"code": c, "name": _CURRENCIES[c][0], "minor_units": _CURRENCIES[c][1]} for c in codes()]

def normalize(code):
    if not isinstance(code, str) or not code.strip(): raise CurrencyError("currency code is required (ISO 4217, e.g. USD, EUR, CNY, JPY)")
    return code.strip().upper()

def minor_units(code):
    """Decimal places for the currency (0..4). Unknown codes raise rather than defaulting silently."""
    c = normalize(code)
    if c not in _CURRENCIES: raise CurrencyError(f"unknown currency {c!r}; use an ISO 4217 code (for example USD, EUR, CNY, JPY, KWD)")
    return _CURRENCIES[c][1]

def name(code): return _CURRENCIES[normalize(code)][0]

def same_code(a, b): return normalize(a) == normalize(b)

def convert(amount, from_currency, to_currency, rate, rate_date=None, rate_source=None, rate_provenance="user"):
    """Convert `amount` from one currency to another at a DECLARED rate (units of `to` per 1 of `from`).

    The rate is never looked up or invented. Its provenance is recorded: `user` (the owner typed it),
    `sourced` (the owner names a source, which the system does not verify) or `assumption`. A `sourced`
    rate requires `rate_source`; nothing here turns an assumption into a fact.
    """
    f, t = normalize(from_currency), normalize(to_currency)
    for c in (f, t):
        if c not in _CURRENCIES: raise CurrencyError(f"unknown currency {c!r}; use an ISO 4217 code")
    try: r = D(str(rate))
    except (InvalidOperation, ValueError, TypeError): raise CurrencyError("rate must be a decimal number")
    if not r.is_finite() or r <= 0: raise CurrencyError("rate must be a positive finite number")
    if not isinstance(rate_provenance, str) or rate_provenance not in ("user", "sourced", "assumption"):
        raise CurrencyError("rate_provenance must be user, sourced or assumption")
    if rate_provenance == "sourced" and not (isinstance(rate_source, str) and rate_source.strip()):
        raise CurrencyError("a sourced rate needs rate_source (where it came from); the system does not verify it")
    if same_code(f, t) and r != 1:
        raise CurrencyError("converting a currency to itself requires rate 1; the declared rate contradicts the codes")
    try: a = D(str(amount))
    except (InvalidOperation, ValueError, TypeError): raise CurrencyError("amount must be a decimal number")
    if not a.is_finite(): raise CurrencyError("amount must be finite")
    return {"amount": a * r, "amount_from": a, "rate": r, "from_currency": f, "to_currency": t,
            "rate_date": rate_date, "rate_source": rate_source, "rate_provenance": rate_provenance,
            "provenance_note": "The exchange rate is the owner's declaration and is not retrieved or verified by the system."}
