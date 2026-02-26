"""
CLI entry point for the Binance Futures Testnet Trading Bot.

Parses command-line arguments, validates inputs, prints a pre-execution
summary, delegates to the service layer, and formats the result.
Contains no business logic or API code.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from logging_config import get_logger
from validators import validate_order_params, ValidationError
from client import BinanceClient, BinanceAPIError, NetworkError
from orders import place_order

logger = get_logger("cli")

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet (USDT-M) — Market & Limit order bot",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair (e.g. BTCUSDT)")
    parser.add_argument("--side", required=True, help="Order side: BUY or SELL")
    parser.add_argument("--order-type", required=True, dest="order_type",
                        help="Order type: MARKET or LIMIT")
    parser.add_argument("--quantity", required=True, help="Order quantity (e.g. 0.01)")
    parser.add_argument("--price", default=None,
                        help="Limit price (required for LIMIT orders)")
    return parser


# ---------------------------------------------------------------------------
# Console output helpers
# ---------------------------------------------------------------------------

def _print_header(text: str) -> None:
    width = max(len(text) + 4, 50)
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def _print_order_summary(params: dict) -> None:
    _print_header("ORDER REQUEST SUMMARY")
    print(f"  Symbol     : {params['symbol']}")
    print(f"  Side       : {params['side']}")
    print(f"  Type       : {params['order_type']}")
    print(f"  Quantity   : {params['quantity']}")
    if params.get("price") is not None:
        print(f"  Price      : {params['price']}")
    print("-" * 50)


def _print_result(result: dict) -> None:
    _print_header("ORDER CONFIRMATION")
    print(f"  Order ID   : {result['orderId']}")
    print(f"  Status     : {result['status']}")
    print(f"  Symbol     : {result['symbol']}")
    print(f"  Side       : {result['side']}")
    print(f"  Type       : {result['type']}")
    print(f"  Filled Qty : {result['executedQty']}")
    print(f"  Avg Price  : {result['avgPrice']}")
    print("=" * 50 + "\n")


def _print_error(message: str) -> None:
    print(f"\n  ✖  ERROR: {message}\n", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Run the trading bot CLI. Returns an exit code (0 = success)."""
    load_dotenv()

    logger.info("Application started")

    parser = _build_parser()
    args = parser.parse_args()

    # ---- Validate inputs ------------------------------------------------
    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
    except ValidationError as exc:
        logger.warning("Validation failed — %s", exc)
        _print_error(str(exc))
        return 1

    _print_order_summary(params)

    # ---- Load credentials -----------------------------------------------
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    if not api_key or not api_secret:
        msg = (
            "Missing API credentials. Set BINANCE_API_KEY and "
            "BINANCE_API_SECRET in your environment or .env file."
        )
        logger.error(msg)
        _print_error(msg)
        return 1

    # ---- Place order -----------------------------------------------------
    client = BinanceClient(api_key=api_key, api_secret=api_secret)

    try:
        result = place_order(
            client=client,
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params.get("price"),
        )
    except BinanceAPIError as exc:
        logger.error("Binance API error — code=%s msg=%s", exc.code, exc.message)
        _print_error(f"Binance rejected the order (code {exc.code}): {exc.message}")
        return 1
    except NetworkError as exc:
        logger.error("Network error — %s", exc)
        _print_error(f"Network failure: {exc}")
        return 1
    except Exception as exc:
        logger.critical("Unexpected error — %s", exc, exc_info=True)
        _print_error(
            "An unexpected error occurred. Check logs/trading_bot.log for details."
        )
        return 1

    _print_result(result)
    logger.info("Application finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
