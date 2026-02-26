"""
Order service layer.

Orchestrates the order-placement workflow: builds the API payload from
validated parameters, calls the Binance client, and returns a structured
result.  All business-logic decisions live here.
"""

from logging_config import get_logger

logger = get_logger("orders")


def place_order(
    client,
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
) -> dict:
    """Place an order via *client* and return a structured result dict.

    Parameters are expected to be **already validated** by the validation
    layer.  This function constructs the Binance-compatible payload, calls
    the API, and extracts the key fields from the response.

    Returns::

        {
            "orderId":     12345,
            "status":      "FILLED",
            "symbol":      "BTCUSDT",
            "side":        "BUY",
            "type":        "MARKET",
            "executedQty": "0.01",
            "avgPrice":    "65432.10",
        }
    """
    payload = _build_payload(symbol, side, order_type, quantity, price)

    logger.info(
        "Placing order — symbol=%s side=%s type=%s qty=%s price=%s",
        symbol, side, order_type, quantity, price,
    )

    raw = client.place_order(payload)

    result = {
        "orderId": raw.get("orderId"),
        "status": raw.get("status"),
        "symbol": raw.get("symbol"),
        "side": raw.get("side"),
        "type": raw.get("type"),
        "executedQty": raw.get("executedQty", "0"),
        "avgPrice": raw.get("avgPrice", "0"),
    }

    logger.info(
        "Order placed successfully — orderId=%s status=%s executedQty=%s avgPrice=%s",
        result["orderId"], result["status"],
        result["executedQty"], result["avgPrice"],
    )

    return result


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------

def _build_payload(symbol, side, order_type, quantity, price) -> dict:
    """Build a Binance-compatible request payload dict."""
    payload = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": str(quantity),
    }

    if order_type == "LIMIT":
        payload["timeInForce"] = "GTC"
        payload["price"] = str(price)

    return payload
