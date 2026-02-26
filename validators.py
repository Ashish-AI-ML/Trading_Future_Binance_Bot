"""
Input validation for order parameters.

All validation is performed here *before* any API call is made.
The module is pure logic — no I/O, no network, no side effects.
"""

from decimal import Decimal, InvalidOperation

from logging_config import get_logger

logger = get_logger("validators")


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------
class ValidationError(Exception):
    """Raised when an order parameter fails validation.

    Attributes:
        field   -- name of the invalid parameter
        value   -- the value that was rejected
        message -- human-readable guidance
    """

    def __init__(self, field: str, value, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"Invalid {field}: '{value}'. {message}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_VALID_SIDES = {"BUY", "SELL"}
_VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None = None,
) -> dict:
    """Validate and normalise raw CLI inputs.

    Returns a dict with cleaned values ready for the service layer::

        {
            "symbol":     "BTCUSDT",
            "side":       "BUY",
            "order_type": "LIMIT",
            "quantity":   Decimal("0.01"),
            "price":      Decimal("30000"),   # None for MARKET
        }

    Raises ``ValidationError`` on the first failing rule.
    """

    # --- Symbol ---
    if not symbol or not symbol.strip():
        raise ValidationError("symbol", symbol, "Symbol must be a non-empty string.")
    clean_symbol = symbol.strip().upper()

    # --- Side ---
    clean_side = side.strip().upper() if side else ""
    if clean_side not in _VALID_SIDES:
        raise ValidationError(
            "side", side, f"Expected one of: {', '.join(sorted(_VALID_SIDES))}."
        )

    # --- Order type ---
    clean_type = order_type.strip().upper() if order_type else ""
    if clean_type not in _VALID_ORDER_TYPES:
        raise ValidationError(
            "order_type",
            order_type,
            f"Expected one of: {', '.join(sorted(_VALID_ORDER_TYPES))}.",
        )

    # --- Quantity ---
    try:
        qty = Decimal(quantity)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(
            "quantity", quantity, "Must be a valid positive number (e.g. 0.01)."
        )
    if qty <= 0:
        raise ValidationError(
            "quantity", quantity, "Must be strictly greater than zero."
        )

    # --- Price (conditional on order type) ---
    clean_price = None
    if clean_type == "LIMIT":
        if price is None or (isinstance(price, str) and not price.strip()):
            raise ValidationError(
                "price",
                price,
                "Price is required for LIMIT orders.",
            )
        try:
            clean_price = Decimal(price)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError(
                "price", price, "Must be a valid positive number (e.g. 30000)."
            )
        if clean_price <= 0:
            raise ValidationError(
                "price", price, "Must be strictly greater than zero."
            )

    logger.debug(
        "Validation passed — symbol=%s side=%s type=%s qty=%s price=%s",
        clean_symbol, clean_side, clean_type, qty, clean_price,
    )

    return {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": qty,
        "price": clean_price,
    }
