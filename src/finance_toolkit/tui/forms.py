"""Pure form boundaries: explicit percent labels, no UI imports or formulas."""

from __future__ import annotations

import math
import types
from dataclasses import dataclass, fields
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints


@dataclass(frozen=True)
class Field:
    name: str
    label: str
    annotation: Any
    percent: bool = False


PERCENT_FIELDS = {
    "drifts",
    "volatilities",
    "volatility",
    "dividend_yield",
    "coupon_rate",
    "rate",
    "lending_rate",
    "borrowing_rate",
    "stock_borrow_rate",
    "confidence",
    "proportional_fee",
    "spot_shocks",
    "rate_shocks",
    "volatility_shock",
}
LABELS = {
    "spots": "Aktien-Spots (Währung; Komma-Liste)",
    "drifts": "Reale GBM-Drifts (% pro Jahr; Komma-Liste)",
    "volatilities": "GBM-Volatilitäten (% pro Jahr; Komma-Liste)",
    "volatility": "Options-Modellvolatilität (% pro Jahr)",
    "correlation": "Korrelation (Kommas; Zeilen mit Semikolon; leer=Identität)",
    "horizon": "Horizont (Jahre)",
    "steps": "Zeitschritte",
    "paths": "Pfade",
    "seed": "Seed (nichtnegative ganze Zahl)",
    "initial_cash": "Anfangskapital (Währung)",
    "rate": "Bewertungszins (% pro Jahr, stetig)",
    "lending_rate": "Guthabenzins (% pro Jahr, stetig)",
    "borrowing_rate": "Kreditzins (% pro Jahr, stetig)",
    "kind": "Instrument (stock/call/put/bond)",
    "asset": "Assetindex (ab 0)",
    "strike": "Strike (Währung pro Underlying)",
    "maturity": "Fälligkeit (Jahre ab t=0)",
    "multiplier": "Optionsmultiplikator (Underlying pro Vertrag)",
    "dividend_yield": "Dividendenrendite (% pro Jahr; Bewertungsparameter)",
    "face": "Anleihen-Nennwert (Währung)",
    "coupon_rate": "Kupon (% pro Jahr)",
    "frequency": "Kupons pro Jahr",
    "time": "Tradezeit (Jahre ab t=0)",
    "quantity": "Menge (+ Kauf / − Verkauf, Aktien/Verträge/Anleihen)",
    "price": "Ausführungsquote (Währung; leer=Modellquote)",
    "fee": "Tradegebühr (Währung)",
}


def form_fields(
    cls: type[Any], *, exclude: set[str] | None = None
) -> tuple[Field, ...]:
    """Describe scalar/vector fields; nested objects are edited in dedicated dialogs."""
    hints = get_type_hints(cls)
    return tuple(
        Field(
            f.name, LABELS.get(f.name, f.name), hints[f.name], f.name in PERCENT_FIELDS
        )
        for f in fields(cls)
        if f.name not in (exclude or set())
    )


def parse_field(text: str, annotation: Any, *, percent: bool = False) -> Any:
    """Parse a labelled value; vectors use commas, matrices semicolon rows."""
    value = text.strip()
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (types.UnionType, Union):
        if type(None) in args and not value:
            return None
        for candidate in args:
            if candidate is not type(None):
                try:
                    return parse_field(value, candidate, percent=percent)
                except ValueError:
                    pass
        raise ValueError("Ungültiger Wert oder Typ")
    if origin is tuple:
        if not value:
            return []
        separator = ";" if get_origin(args[0]) is tuple else ","
        return [
            parse_field(part, args[0], percent=percent)
            for part in value.split(separator)
        ]
    if origin is Literal:
        if value in args:
            return value
        raise ValueError(f"Erlaubt: {', '.join(str(x) for x in args)}")
    if annotation is str:
        return value
    if annotation is bool:
        if value.lower() in ("ja", "true"):
            return True
        if value.lower() in ("nein", "false"):
            return False
        raise ValueError("Bitte ja oder nein eingeben")
    if annotation is int:
        try:
            return int(value)
        except ValueError as error:
            raise ValueError("Ganze Zahl erforderlich") from error
    if annotation is float:
        try:
            number = float(value)
        except ValueError as error:
            raise ValueError("Zahl erforderlich") from error
        if not math.isfinite(number):
            raise ValueError("Endliche Zahl erforderlich")
        return number / 100 if percent else number
    raise ValueError("Nicht unterstützter Formularwert")


def format_field(value: object, *, percent: bool = False) -> str:
    """Format full-precision inputs; never round data for calculation/export."""
    if value is None:
        return ""
    if isinstance(value, tuple | list):
        separator = "; " if value and isinstance(value[0], tuple | list) else ", "
        return separator.join(format_field(x, percent=percent) for x in value)
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if percent and isinstance(value, float | int):
        return repr(value * 100)
    return str(value)
