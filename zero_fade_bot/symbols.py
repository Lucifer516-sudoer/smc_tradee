from __future__ import annotations


def base_fx_symbol(symbol: str) -> str:
    letters = "".join(char for char in symbol.upper() if char.isalpha())
    return letters[:6]


def is_jpy_pair(symbol: str) -> bool:
    return base_fx_symbol(symbol)[3:6] == "JPY"


def pip_size(symbol: str) -> float:
    return 0.01 if is_jpy_pair(symbol) else 0.0001
