"""Risk management utilities."""


def atr_normalised_size(
    *,
    risk_per_trade: float,
    atr: float,
    atr_risk_mult: float,
    min_size: float,
    max_size: float,
) -> float:
    """
    Calculate position size normalized by ATR.

    Position size is calculated as: risk_per_trade / (atr * atr_risk_mult)
    Result is clamped between min_size and max_size.

    Args:
        risk_per_trade: Amount of capital to risk per trade
        atr: Current ATR value
        atr_risk_mult: ATR multiplier for stop distance
        min_size: Minimum position size
        max_size: Maximum position size

    Returns:
        Position size clamped to [min_size, max_size]
    """
    denom = float(atr) * float(atr_risk_mult)
    if denom <= 0.0:
        return float(min_size)
    raw = float(risk_per_trade) / denom
    return max(float(min_size), min(float(max_size), raw))
