"""
USD/ILS exchange rate: Bank of Israel (BOI) vs currency_converter (ECB).

The Bank of Israel publishes the *Official Representative Exchange Rate*
(שער יציג) on every Israeli business day. It is sampled from interbank
trading at a specific time of day and is the rate used for accounting,
contracts and tax purposes in Israel.

API documented at:
  https://www.boi.org.il/media/tzxbuhhj/extracting-representative-exchange-rates-from-the-new-series-database.pdf

Series code for USD/ILS = RER_USD_ILS, DATA_TYPE=OF00 (representative).
"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from urllib.parse import urlencode

import requests

BOI_BASE = (
    "https://edge.boi.org.il/FusionEdgeServer/sdmx/v2/data/dataflow/"
    "BOI.STATISTICS/EXR/1.0"
)


def get_boi_representative_rate(d, currency: str = "USD"):
    d = d.date() if hasattr(d, 'date') else d
    series = f"RER_{currency.upper()}_ILS"
    params = {
        "startperiod": d.isoformat(),
        "endperiod":   d.isoformat(),
        "format":      "csv",
    }
    url = f"{BOI_BASE}/{series}?{urlencode(params)}"
    r = requests.get(url, timeout=30)

    if r.status_code == 404:
        return None          # no rate published for this date (holiday/weekend)
    r.raise_for_status()     # still raise on unexpected errors (500, etc.)

    reader = csv.DictReader(io.StringIO(r.text))
    rows = [row for row in reader if row.get("TIME_PERIOD") == d.isoformat()]
    if not rows:
        return None
    return float(rows[0]["OBS_VALUE"])


def get_boi_rate_with_fallback(d: date, currency: str = "USD") -> tuple[date, float]:
    """
    Same as above, but if `d` has no published rate (weekend/holiday),
    walk back day-by-day to the most recent business day with a rate.
    Returns (effective_date, rate).
    """
    cur = d
    for _ in range(10):
        rate = get_boi_representative_rate(cur, currency)
        if rate is not None:
            return cur, rate
        cur -= timedelta(days=1)
    raise RuntimeError(f"No BOI rate found within 10 days of {d.isoformat()}")
