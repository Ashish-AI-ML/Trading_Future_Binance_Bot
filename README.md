# Binance Futures Testnet Trading Bot (USDT-M)

A production-grade, layered CLI trading bot built in Python that places **Market** and **Limit** orders on the Binance Futures Testnet using direct REST API integration with HMAC-SHA256 authentication.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture & Design Philosophy](#architecture--design-philosophy)
- [Request Lifecycle — Step-by-Step Flow](#request-lifecycle--step-by-step-flow)
- [Module Breakdown](#module-breakdown)
- [Setup & Installation](#setup--installation)
- [Usage Examples](#usage-examples)
- [Input Validation Logic](#input-validation-logic)
- [Error Handling Strategy](#error-handling-strategy)
- [Logging & Observability](#logging--observability)
- [Security Practices](#security-practices)
- [Test Cases & Results](#test-cases--results)
- [Challenges Faced & Solutions](#challenges-faced--solutions)
- [Future Enhancements](#future-enhancements)

---

## Project Overview

### What This Bot Does

This is a command-line Python application that connects to the **Binance Futures Testnet (USDT-M)** to place trading orders programmatically. It supports two order types:

| Order Type | Behaviour |
|---|---|
| **MARKET** | Executes immediately at the best available price. No price parameter needed. |
| **LIMIT** | Sits in the order book at a specified price until filled, cancelled, or expired. `timeInForce=GTC` (Good Till Cancelled). |

### Why This Architecture?

This is **not a quick script** — it's engineered as a layered application with the same discipline expected of production financial software:

- **Separation of concerns** — each module has a single, bounded responsibility
- **Full observability** — every API request/response is logged with timestamps
- **Security-first** — credentials never appear in logs or source code
- **Graceful failure** — every error path produces a human-readable message, never a raw stack trace

---

## Architecture & Design Philosophy

### Four-Layer Architecture

The system uses a strict top-down layer separation. No layer communicates with a non-adjacent layer.

```
┌─────────────────────────────────────────────────┐
│                   USER (Terminal)                │
└──────────────────────┬──────────────────────────┘
                       │ CLI arguments
                       ▼
┌─────────────────────────────────────────────────┐
│             CLI LAYER (cli.py)                  │
│  • Parses arguments (argparse)                  │
│  • Prints pre-execution summary                 │
│  • Formats success/error output                 │
│  • Exit codes: 0 (success), 1 (failure)         │
└──────────────────────┬──────────────────────────┘
                       │ Raw inputs
                       ▼
┌─────────────────────────────────────────────────┐
│         VALIDATION LAYER (validators.py)        │
│  • Pure logic — no I/O, no API calls            │
│  • Type checks → Range checks → Conditional     │
│  • Short-circuits on first error                │
│  • Returns normalized dict or ValidationError   │
└──────────────────────┬──────────────────────────┘
                       │ Validated params
                       ▼
┌─────────────────────────────────────────────────┐
│          SERVICE LAYER (orders.py)              │
│  • Orchestrates order placement workflow        │
│  • Constructs Binance-compatible payload        │
│  • Adds timeInForce=GTC for LIMIT orders        │
│  • Extracts key fields from API response        │
└──────────────────────┬──────────────────────────┘
                       │ Request payload
                       ▼
┌─────────────────────────────────────────────────┐
│         API CLIENT LAYER (client.py)            │
│  • HMAC-SHA256 request signing                  │
│  • HTTP transport via `requests` library        │
│  • Handles network errors, JSON parsing         │
│  • Returns raw response or raises exception     │
└──────────────────────┬──────────────────────────┘
                       │ Signed HTTPS request
                       ▼
┌─────────────────────────────────────────────────┐
│        BINANCE FUTURES TESTNET REST API         │
│     https://testnet.binancefuture.com           │
│              POST /fapi/v1/order                │
└─────────────────────────────────────────────────┘
```

### Why Not a Single Script?

| Monolithic Script | Layered Architecture (This Project) |
|---|---|
| Validation mixed with API calls | Validation runs independently, before any network call |
| Can't test components individually | Each layer is independently testable |
| Adding a new order type means reading the entire file | Extend `_build_payload()` and add validation rules — no other changes |
| Logging scattered everywhere | Centralized in `logging_config.py` |
| Credentials might leak into logs | Sanitization enforced at the logging layer |

---

## Request Lifecycle — Step-by-Step Flow

Here's exactly what happens when you run a command:

```
python cli.py --symbol BTCUSDT --side BUY --order-type LIMIT --quantity 0.01 --price 71500
```

| Step | Module | Action |
|---|---|---|
| 1 | `cli.py` | `argparse` parses raw CLI strings into a structured namespace |
| 2 | `cli.py` | Loads `.env` credentials via `python-dotenv` |
| 3 | `validators.py` | Normalizes inputs to uppercase, validates types, ranges, and conditional rules |
| 4 | `validators.py` | If invalid → raises `ValidationError` → CLI prints error, exits with code 1 |
| 5 | `cli.py` | Prints **ORDER REQUEST SUMMARY** to console |
| 6 | `orders.py` | Constructs API payload: `{symbol, side, type, quantity, timeInForce, price}` |
| 7 | `client.py` | Adds `timestamp` + `recvWindow`, signs with HMAC-SHA256 |
| 8 | `client.py` | Sends `POST /fapi/v1/order` to Binance Testnet |
| 9 | `client.py` | Parses JSON response, checks for Binance error codes |
| 10 | `orders.py` | Extracts `orderId`, `status`, `executedQty`, `avgPrice` |
| 11 | `cli.py` | Prints **ORDER CONFIRMATION** to console |
| 12 | All layers | Every step logged to `logs/trading_bot.log` with ISO 8601 timestamps |

---

## Module Breakdown

| File | Lines | Responsibility |
|---|---|---|
| `cli.py` | Entry point | Argument parsing, console I/O, error handling orchestration, exit codes |
| `validators.py` | Validation | Pure input validation — no I/O, no network. Custom `ValidationError` exception |
| `orders.py` | Service | Business logic, payload construction, response extraction |
| `client.py` | API Client | HMAC-SHA256 signing, HTTP transport, `BinanceAPIError` / `NetworkError` exceptions |
| `logging_config.py` | Logging | Rotating file handler (10 MB / 5 backups), credential sanitization |

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Binance Futures Testnet account → [https://testnet.binancefuture.com/](https://testnet.binancefuture.com/)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies: `requests` (HTTP client), `python-dotenv` (.env file loader)

### 2. Configure API Credentials

```bash
cp .env.example .env
```

Edit `.env` with your **Futures Testnet** keys (not Spot Testnet):

```
BINANCE_API_KEY=your_actual_api_key
BINANCE_API_SECRET=your_actual_api_secret
```

> ⚠️ **Important:** Keys from `testnet.binance.vision` (Spot Testnet) will **not** work. You need keys from `testnet.binancefuture.com` (Futures Testnet).

### 3. Run the Bot

```bash
python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.01
```

---

## Usage Examples

### Market Order (executes immediately)

```bash
python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.01
```

```
==================================================
  ORDER REQUEST SUMMARY
==================================================
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.01
--------------------------------------------------

==================================================
  ORDER CONFIRMATION
==================================================
  Order ID   : 12548972562
  Status     : NEW
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Filled Qty : 0.000
  Avg Price  : 0.00
==================================================
```

### Limit Order (waits at specified price)

```bash
python cli.py --symbol BTCUSDT --side BUY --order-type LIMIT --quantity 0.01 --price 71500
```

### Sell Order

```bash
python cli.py --symbol ETHUSDT --side SELL --order-type MARKET --quantity 0.1
```

---

## Input Validation Logic

Validation runs **before any API call** and short-circuits on the first error:

```
Symbol   →  Non-empty string → normalize to UPPERCASE
Side     →  Must be BUY or SELL (case-insensitive input)
Type     →  Must be MARKET or LIMIT (case-insensitive input)
Quantity →  Cast to Decimal → must be > 0
Price    →  LIMIT: required, must be Decimal > 0
             MARKET: silently ignored
```

**Why Decimal instead of float?**
Financial calculations require exact precision. Python's `float` type uses binary floating-point which causes rounding errors (e.g., `0.1 + 0.2 = 0.30000000000000004`). `Decimal` provides exact decimal arithmetic.

---

## Error Handling Strategy

The bot handles **four categories of errors**, each at the appropriate layer:

| Category | Example | Handled By | Log Level |
|---|---|---|---|
| **Validation Errors** | Invalid side `BUUY`, missing price for LIMIT | `validators.py` | WARNING |
| **Binance API Errors** | Invalid symbol, price too high, insufficient balance | `client.py` → `cli.py` | ERROR |
| **Network Errors** | Timeout, DNS failure, connection refused | `client.py` → `cli.py` | ERROR |
| **Unexpected Errors** | Programming bugs, unhandled edge cases | `cli.py` (top-level catch) | CRITICAL |

**Key principle:** The bot **never crashes** with a raw Python traceback. Every error produces a human-readable message on the console, and the full details (including stack traces for unexpected errors) are written only to the log file.

---

## Logging & Observability

### Log Format

```
[2026-02-26 12:45:09] [INFO] [trading_bot.orders] — Order placed successfully — orderId=12548934038 status=NEW
```

Every entry includes: **ISO 8601 timestamp**, **log level**, **module name**, and **structured message**.

### Log Levels

| Level | What it captures | Where |
|---|---|---|
| DEBUG | Raw API requests/responses, internal state | File only |
| INFO | Order submitted, order confirmed, app start/exit | File |
| WARNING | Validation failures | File + Console |
| ERROR | API rejections, network failures | File + Console |
| CRITICAL | Unexpected programming errors (with stack trace) | File + Console |

### Log File Management

- **Location:** `./logs/trading_bot.log`
- **Rotation:** Automatic at 10 MB, keeps 5 backups
- **Encoding:** UTF-8
- **Credential sanitization:** API keys, secrets, and signatures are replaced with `***REDACTED***` before writing

---

## Security Practices

| Practice | Implementation |
|---|---|
| Credential storage | Environment variables / `.env` file — never hardcoded |
| Git protection | `.env` excluded via `.gitignore` |
| Log sanitization | `sanitize_params()` strips `api_key`, `secret`, `signature` fields |
| Template provided | `.env.example` with placeholder values for documentation |
| No console exposure | Credentials never echoed to terminal output |

---

## Test Cases & Results

### ✅ Successful Orders (Verified on Binance Futures Testnet)

| # | Command | Result | Order ID |
|---|---|---|---|
| 1 | `--symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.01` | ✅ Filled at 68,208.9 | 12548934038 |
| 2 | `--symbol BTCUSDT --side BUY --order-type LIMIT --quantity 0.01 --price 50000` | ✅ Placed (Open Order, below market price) | 12548934338 |
| 3 | `--symbol BTCUSDT --side BUY --order-type LIMIT --quantity 0.01 --price 71500` | ✅ Filled immediately (above market price) | 12548973138 |

### ❌ Validation Errors (Caught Before API Call)

| # | Test Case | Error Message |
|---|---|---|
| 4 | Missing `--price` for LIMIT order | `Invalid price: 'None'. Price is required for LIMIT orders.` |
| 5 | Typo in side: `--side BUUY` | `Invalid side: 'BUUY'. Expected one of: BUY, SELL.` |
| 6 | Negative quantity: `--quantity -5` | `Invalid quantity: '-5'. Must be strictly greater than zero.` |

### ⚠️ API Errors (Handled Gracefully)

| # | Test Case | Binance Error | Bot Output |
|---|---|---|---|
| 7 | Invalid API keys | Code -2015 | `Binance rejected the order (code -2015): Invalid API-key, IP, or permissions for action` |
| 8 | LIMIT price too high: `--price 100000` | Code -4016 | `Binance rejected the order (code -4016): Limit price can't be higher than 71512.10.` |

### Verification on Exchange

All orders were confirmed on the Binance Futures Testnet web interface:
- **Open Orders** tab showed unfilled LIMIT orders (price below market)
- **Trade History** tab showed filled orders with exact prices, quantities, and fees
- **Order History** tab showed cancelled/expired orders after manual cancellation

---

## Challenges Faced & Solutions

### 1. API Key Confusion — Spot Testnet vs. Futures Testnet

**Problem:** Initial API keys generated from `testnet.binance.vision` (Spot Testnet) returned error `-2015: Invalid API-key, IP, or permissions for action` when calling the Futures endpoint.

**Root Cause:** Binance operates separate testnet environments for Spot and Futures. Each has its own API keys that are not interchangeable.

**Solution:** Generated new keys from `testnet.binancefuture.com` (the correct Futures Testnet). Added a clear warning in the README and `.env.example` to prevent other users from making the same mistake.

---

### 2. LIMIT Order Price Boundaries

**Problem:** A LIMIT BUY at price `100,000` was rejected with error `-4016: Limit price can't be higher than 71512.10`.

**Root Cause:** Binance enforces price filter rules that restrict how far a LIMIT price can deviate from the current market price. This is a risk control mechanism to prevent accidental orders.

**Solution:** The bot surfaces this error cleanly to the user. In a future version, we could query `/fapi/v1/exchangeInfo` to fetch symbol filters and pre-validate prices locally.

---

### 3. Understanding Order Status — "NEW" vs "FILLED"

**Problem:** Both MARKET and LIMIT orders returned `status: NEW` in the initial API response, which was confusing because MARKET orders should fill immediately.

**Root Cause:** Binance's order API returns the order's status at the moment of **acceptance**. The exchange processes fills asynchronously. The `NEW` status means "accepted by the matching engine." The fill happens milliseconds later and is reflected in the Trade History.

**Solution:** Documented this behavior. Users should check the **Trade History** tab on the testnet for fill confirmation, not just the API response status.

---

### 4. LIMIT Orders Filling Instantly

**Problem:** A LIMIT BUY order at 71,500 filled immediately instead of sitting in the order book, which was unexpected.

**Root Cause:** The testnet BTC price was ~68,208 — below the limit price. A LIMIT BUY at 71,500 means *"buy at 71,500 or better."* Since 68,208 is a better price, the order matched immediately.

**Solution:** This is correct exchange behavior. A LIMIT order only rests in the order book when it **cannot** be matched at the current market price (e.g., a BUY limit below market price, or a SELL limit above market price).

---

### 5. Credential Security in Logging

**Problem:** HMAC signatures and API keys could potentially appear in debug logs when logging request parameters.

**Solution:** Implemented `sanitize_params()` in `logging_config.py` that scans all dictionary fields against a set of sensitive key patterns (`api_key`, `secret`, `signature`, etc.) and replaces their values with `***REDACTED***` before writing to any log handler.

---

## Future Enhancements

| Enhancement | Approach |
|---|---|
| **Stop-Limit / OCO orders** | Add new payload constructors in `orders.py`, extend validation rules |
| **Symbol precision validation** | Query `/fapi/v1/exchangeInfo` for lot size / tick size filters |
| **Order status tracking** | Add `GET /fapi/v1/order` query capability |
| **Strategy engine** | New layer above service — consumes market data, generates order signals |
| **Database logging** | Add PostgreSQL/SQLite writer alongside file logger |
| **Web dashboard** | Expose service layer via FastAPI, add React frontend |
| **Async execution** | Replace `requests` with `httpx` for concurrent order placement |

---

## Project Structure

```
trading_Bot/
├── cli.py                 # CLI entry point — argparse, console I/O
├── validators.py          # Pure input validation — no I/O
├── orders.py              # Service layer — business logic
├── client.py              # API client — HMAC signing, HTTP transport
├── logging_config.py      # Rotating logger, credential sanitization
├── requirements.txt       # Python dependencies
├── .env.example           # Credential template (safe to commit)
├── .env                   # Actual credentials (NEVER commit)
├── .gitignore             # Excludes .env, logs, __pycache__
├── README.md              # This file
└── logs/
    └── trading_bot.log    # Structured audit log (auto-created)
```

---

## License

This project is for educational and testnet evaluation purposes.
