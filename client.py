"""
Binance Futures Testnet REST API client.

Handles authentication (HMAC-SHA256 signing), HTTP transport, and raw
response parsing.  Contains NO business logic.
"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from logging_config import get_logger, sanitize_params

logger = get_logger("client")

# ---------------------------------------------------------------------------
# Default Testnet base URL
# ---------------------------------------------------------------------------
DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class BinanceAPIError(Exception):
    """Raised when Binance returns a recognised error response.

    Attributes:
        code    -- Binance error code (e.g. -1121)
        message -- Binance error message
        http_status -- HTTP status code of the response
    """

    def __init__(self, code: int, message: str, http_status: int = 0):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"Binance API error {code}: {message}")


class NetworkError(Exception):
    """Raised on transport-level failures (timeout, DNS, SSL, etc.)."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class BinanceClient:
    """Low-level wrapper for the Binance USDT-M Futures REST API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 10,
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self._api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def place_order(self, params: dict) -> dict:
        """Send a signed POST to ``/fapi/v1/order`` and return the JSON body.

        Raises:
            BinanceAPIError -- on a structured error from the exchange
            NetworkError    -- on a transport-level failure
        """
        endpoint = "/fapi/v1/order"
        return self._signed_request("POST", endpoint, params)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _signed_request(self, method: str, endpoint: str, params: dict) -> dict:
        """Add timestamp + signature, send the request, return JSON."""
        params = dict(params)  # shallow copy — don't mutate caller's dict
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000

        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature

        url = f"{self._base_url}{endpoint}"

        logger.debug(
            "API request  — %s %s params=%s",
            method, url, sanitize_params(params),
        )

        start = time.monotonic()
        try:
            response = self._session.request(
                method, url, params=params, timeout=self._timeout,
            )
            elapsed_ms = (time.monotonic() - start) * 1000
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error — %s %s — %s", method, url, exc)
            raise NetworkError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timeout — %s %s — %s", method, url, exc)
            raise NetworkError(f"Request timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Request error — %s %s — %s", method, url, exc)
            raise NetworkError(f"Request failed: {exc}") from exc

        logger.debug(
            "API response — %s %s — HTTP %d (%.0f ms) body=%s",
            method, url, response.status_code, elapsed_ms, response.text,
        )

        # Parse JSON
        try:
            data = response.json()
        except ValueError:
            logger.error(
                "Non-JSON response — HTTP %d body=%s",
                response.status_code, response.text,
            )
            raise BinanceAPIError(
                code=-1,
                message=f"Unexpected non-JSON response: {response.text[:200]}",
                http_status=response.status_code,
            )

        # Check for Binance-level error
        if "code" in data and data["code"] != 200:
            raise BinanceAPIError(
                code=data["code"],
                message=data.get("msg", "Unknown error"),
                http_status=response.status_code,
            )

        return data
