# PROJECT DEVELOPMENT LOG
# Binance Futures Testnet Trading Bot (USDT-M)
# ============================================

## Session: 2026-02-26

### [12:00] Project Initialization
- Created empty project at c:\Users\win10\Downloads\trading_Bot
- Designed four-layer architecture: CLI → Validation → Service → API Client
- Technology decisions:
  - Direct REST API via `requests` (not python-binance SDK) for full transparency
  - `argparse` for CLI (zero extra dependencies)
  - `python-dotenv` for credential loading
  - HMAC-SHA256 for Binance request signing

### [12:02] Module Implementation
- Created `logging_config.py` — Rotating file handler (10MB/5 backups), credential sanitization
- Created `validators.py` — Pure validation with custom ValidationError, Decimal precision
- Created `client.py` — HMAC-SHA256 signing, BinanceAPIError/NetworkError exceptions
- Created `orders.py` — Service layer, payload construction, response extraction
- Created `cli.py` — argparse entry point, pre-execution summary, structured output
- Created `requirements.txt`, `.env.example`, `.gitignore`, `README.md`

### [12:02] Verification — CLI & Validation Layer
- ✅ `python cli.py --help` — All arguments displayed correctly (exit 0)
- ✅ Missing price for LIMIT → "Invalid price: 'None'. Price is required for LIMIT orders." (exit 1)
- ✅ Invalid side `BUUY` → "Invalid side: 'BUUY'. Expected one of: BUY, SELL." (exit 1)
- ✅ Negative quantity `-5` → "Invalid quantity: '-5'. Must be strictly greater than zero." (exit 1)

### [12:34] First API Test — Invalid Keys
- ❌ Used keys from wrong testnet (Spot instead of Futures)
- Error: `-2015: Invalid API-key, IP, or permissions for action`
- HTTP 401 returned, bot handled gracefully — no crash, clean error message
- Root cause: `testnet.binance.vision` (Spot) keys ≠ `testnet.binancefuture.com` (Futures) keys

### [12:45] Second API Test — Correct Futures Testnet Keys
- ✅ MARKET BUY 0.01 BTCUSDT → orderId=12548934038, status=NEW
  - Filled at price 68,208.9 (confirmed in Trade History on exchange)
- ✅ LIMIT BUY 0.01 BTCUSDT @ 50,000 → orderId=12548934338, status=NEW
  - Stayed in Open Orders (price below market — order rests in order book)

### [13:03] Third API Test — Price Boundary Discovery
- ❌ LIMIT BUY @ 100,000 → rejected with `-4016: Limit price can't be higher than 71512.10`
  - Bot handled error gracefully, displayed Binance error code and message
- ✅ LIMIT BUY @ 71,500 → orderId=12548973138, status=NEW
  - Filled immediately (market price ~68,208 was below limit price)

### [13:03] Additional MARKET Order
- ✅ MARKET BUY 0.01 BTCUSDT → orderId=12548972562, status=NEW

### [13:05] Exchange Verification (Binance Testnet Web UI)
- Open Orders: LIMIT @ 50,000 visible (unfilled, below market)
- Trade History: 3 filled trades confirmed at prices 68,208.8–68,208.9
- Order History: Empty (filled orders move to Trade History, not Order History)

### [13:10] Documentation Update
- Rewrote README.md with:
  - Architecture diagram (ASCII flowchart)
  - 12-step request lifecycle table
  - Validation logic explanation
  - Error handling strategy (4 categories)
  - 8 test cases with real results
  - 5 challenges faced with solutions

### [13:16] Cleanup
- Removed `__pycache__/` directory
- Created this project development log

---

## Summary of Test Results

| # | Test | Type | Result |
|---|---|---|---|
| 1 | CLI `--help` | Smoke | ✅ Pass |
| 2 | Missing price for LIMIT | Validation | ✅ Caught |
| 3 | Invalid side `BUUY` | Validation | ✅ Caught |
| 4 | Negative quantity `-5` | Validation | ✅ Caught |
| 5 | Wrong API keys (Spot Testnet) | API Error | ✅ Handled (-2015) |
| 6 | MARKET BUY BTCUSDT | Order | ✅ Filled (68,208.9) |
| 7 | LIMIT BUY BTCUSDT @ 50,000 | Order | ✅ Open Order |
| 8 | LIMIT BUY BTCUSDT @ 100,000 | API Error | ✅ Handled (-4016) |
| 9 | LIMIT BUY BTCUSDT @ 71,500 | Order | ✅ Filled |
| 10 | MARKET BUY BTCUSDT (re-test) | Order | ✅ Filled |

---

## Final Project Structure

```
trading_Bot/
├── cli.py                 # CLI entry point
├── validators.py          # Input validation
├── orders.py              # Service layer
├── client.py              # API client (HMAC-SHA256)
├── logging_config.py      # Logging configuration
├── requirements.txt       # Dependencies
├── .env.example           # Credential template
├── .env                   # Actual credentials (gitignored)
├── .gitignore             # Git exclusion rules
├── README.md              # Full documentation
├── PROJECT_LOG.md         # This file — development history
└── logs/
    └── trading_bot.log    # Runtime audit log
```
