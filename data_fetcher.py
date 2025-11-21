"""
Market Data Fetcher for Portfolio Crusher X2

Fetches real-time and historical market data from Yahoo Finance.
Includes caching to avoid rate limits and improve performance.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DURATION_SECONDS = 60 * 60  # 1 hour default
_price_cache: Dict[str, Dict[str, Any]] = {}
_info_cache: Dict[str, Dict[str, Any]] = {}


def _is_cache_valid(cache_entry: Dict[str, Any], duration_seconds: int = CACHE_DURATION_SECONDS) -> bool:
    """
    Check if a cache entry is still valid.

    Args:
        cache_entry: Cache entry with 'timestamp' key
        duration_seconds: How long cache should be valid

    Returns:
        True if cache is still valid, False otherwise
    """
    if not cache_entry or 'timestamp' not in cache_entry:
        return False

    cache_age = time.time() - cache_entry['timestamp']
    return cache_age < duration_seconds


def validate_ticker(ticker: str) -> str:
    """
    Validate and normalize a ticker symbol.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Normalized ticker symbol (uppercase, stripped)

    Raises:
        ValueError: If ticker is invalid

    Example:
        >>> validate_ticker("  aapl  ")
        'AAPL'
    """
    if not ticker:
        raise ValueError("Ticker symbol cannot be empty")

    if not isinstance(ticker, str):
        raise ValueError("Ticker must be a string")

    normalized = ticker.strip().upper()

    if len(normalized) == 0:
        raise ValueError("Ticker symbol cannot be empty after normalization")

    if len(normalized) > 10:
        raise ValueError(f"Ticker symbol '{normalized}' is too long (max 10 characters)")

    # Basic validation - alphanumeric plus dots and hyphens
    if not all(c.isalnum() or c in '.-' for c in normalized):
        raise ValueError(f"Ticker symbol '{normalized}' contains invalid characters")

    return normalized


def get_current_price(
    ticker: str,
    use_cache: bool = True,
    cache_duration: int = CACHE_DURATION_SECONDS
) -> Optional[float]:
    """
    Get the current price for a stock ticker.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "SPY")
        use_cache: Whether to use cached data if available
        cache_duration: How long to cache data in seconds

    Returns:
        Current price as float, or None if lookup failed

    Example:
        >>> price = get_current_price("AAPL")
        >>> if price:
        ...     print(f"AAPL is trading at ${price:.2f}")
        >>> else:
        ...     print("Failed to fetch price")
    """
    try:
        ticker_normalized = validate_ticker(ticker)

        # Check cache
        if use_cache and ticker_normalized in _price_cache:
            cache_entry = _price_cache[ticker_normalized]
            if _is_cache_valid(cache_entry, cache_duration):
                logger.info(f"Using cached price for {ticker_normalized}: ${cache_entry['price']:.2f}")
                return cache_entry['price']

        logger.info(f"Fetching current price for {ticker_normalized} from Yahoo Finance")

        # Fetch from yfinance
        stock = yf.Ticker(ticker_normalized)

        # Try to get current price from different sources
        price = None

        # Method 1: Try fast_info (fastest)
        try:
            if hasattr(stock, 'fast_info'):
                price = stock.fast_info.get('lastPrice')
        except Exception as e:
            logger.debug(f"fast_info failed for {ticker_normalized}: {e}")

        # Method 2: Try info dict
        if price is None:
            try:
                info = stock.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
            except Exception as e:
                logger.debug(f"info failed for {ticker_normalized}: {e}")

        # Method 3: Try history (most reliable but slower)
        if price is None:
            try:
                hist = stock.history(period='1d')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            except Exception as e:
                logger.debug(f"history failed for {ticker_normalized}: {e}")

        if price is None or price <= 0:
            logger.warning(f"Could not fetch valid price for {ticker_normalized}")
            return None

        price = float(price)

        # Cache the result
        _price_cache[ticker_normalized] = {
            'price': price,
            'timestamp': time.time()
        }

        logger.info(f"Successfully fetched price for {ticker_normalized}: ${price:.2f}")
        return price

    except ValueError as e:
        logger.error(f"Validation error for ticker '{ticker}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}", exc_info=True)
        return None


def get_stock_info(
    ticker: str,
    use_cache: bool = True,
    cache_duration: int = CACHE_DURATION_SECONDS
) -> Optional[Dict[str, Any]]:
    """
    Get detailed stock information including name, sector, market cap, etc.

    Args:
        ticker: Stock ticker symbol
        use_cache: Whether to use cached data if available
        cache_duration: How long to cache data in seconds

    Returns:
        Dictionary with stock information:
        {
            "ticker": str,
            "name": str,
            "sector": str,
            "industry": str,
            "market_cap": float,
            "currency": str,
            "exchange": str,
            "current_price": float,
            "52_week_high": float,
            "52_week_low": float,
            "avg_volume": int,
            "pe_ratio": float,
            "dividend_yield": float
        }
        Returns None if lookup failed.

    Example:
        >>> info = get_stock_info("AAPL")
        >>> if info:
        ...     print(f"{info['name']} ({info['ticker']})")
        ...     print(f"Sector: {info['sector']}")
        ...     print(f"Market Cap: ${info['market_cap']:,.0f}")
    """
    try:
        ticker_normalized = validate_ticker(ticker)

        # Check cache
        if use_cache and ticker_normalized in _info_cache:
            cache_entry = _info_cache[ticker_normalized]
            if _is_cache_valid(cache_entry, cache_duration):
                logger.info(f"Using cached info for {ticker_normalized}")
                return cache_entry['info']

        logger.info(f"Fetching stock info for {ticker_normalized} from Yahoo Finance")

        # Fetch from yfinance
        stock = yf.Ticker(ticker_normalized)
        raw_info = stock.info

        if not raw_info or len(raw_info) == 0:
            logger.warning(f"No information found for {ticker_normalized}")
            return None

        # Extract and normalize data
        stock_info = {
            "ticker": ticker_normalized,
            "name": raw_info.get('longName') or raw_info.get('shortName') or ticker_normalized,
            "sector": raw_info.get('sector'),
            "industry": raw_info.get('industry'),
            "market_cap": raw_info.get('marketCap'),
            "currency": raw_info.get('currency') or 'USD',
            "exchange": raw_info.get('exchange'),
            "current_price": raw_info.get('currentPrice') or raw_info.get('regularMarketPrice'),
            "52_week_high": raw_info.get('fiftyTwoWeekHigh'),
            "52_week_low": raw_info.get('fiftyTwoWeekLow'),
            "avg_volume": raw_info.get('averageVolume'),
            "pe_ratio": raw_info.get('trailingPE') or raw_info.get('forwardPE'),
            "dividend_yield": raw_info.get('dividendYield'),
            "beta": raw_info.get('beta'),
            "description": raw_info.get('longBusinessSummary'),
        }

        # Cache the result
        _info_cache[ticker_normalized] = {
            'info': stock_info,
            'timestamp': time.time()
        }

        logger.info(f"Successfully fetched info for {ticker_normalized}: {stock_info['name']}")
        return stock_info

    except ValueError as e:
        logger.error(f"Validation error for ticker '{ticker}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching info for {ticker}: {e}", exc_info=True)
        return None


def enrich_positions(
    positions: List[Dict[str, Any]],
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Enrich a list of portfolio positions with current market data.

    Takes positions extracted from OCR or manual input and adds current prices,
    market data, and calculated metrics like gain/loss.

    Args:
        positions: List of position dictionaries with at least 'ticker' and 'quantity'
        use_cache: Whether to use cached market data

    Returns:
        Enriched list of positions with market data added:
        - Adds 'current_price' from market data
        - Adds 'stock_info' with detailed information
        - Calculates 'current_value' if not present
        - Calculates 'gain_loss' and 'gain_loss_pct' if cost_basis available
        - Adds 'enrichment_status' ('success' or 'failed')

    Example:
        >>> positions = [
        ...     {"ticker": "AAPL", "quantity": 10, "cost_basis": 1500},
        ...     {"ticker": "SPY", "quantity": 5, "cost_basis": 2000}
        ... ]
        >>> enriched = enrich_positions(positions)
        >>> for pos in enriched:
        ...     if pos['enrichment_status'] == 'success':
        ...         print(f"{pos['ticker']}: ${pos['current_value']:.2f}")
    """
    if not positions:
        logger.warning("No positions provided to enrich")
        return []

    if not isinstance(positions, list):
        logger.error("Positions must be a list")
        return []

    enriched_positions = []

    for pos in positions:
        if not isinstance(pos, dict):
            logger.warning(f"Skipping invalid position (not a dict): {pos}")
            continue

        if 'ticker' not in pos:
            logger.warning(f"Skipping position without ticker: {pos}")
            continue

        ticker = pos['ticker']
        enriched_pos = pos.copy()

        try:
            # Get current price
            current_price = get_current_price(ticker, use_cache=use_cache)

            if current_price is None:
                logger.warning(f"Failed to fetch price for {ticker}, marking as failed")
                enriched_pos['enrichment_status'] = 'failed'
                enriched_pos['enrichment_error'] = 'Could not fetch current price'
                enriched_positions.append(enriched_pos)
                continue

            enriched_pos['current_price'] = current_price

            # Calculate current value if quantity is available
            if 'quantity' in pos and pos['quantity']:
                quantity = float(pos['quantity'])
                enriched_pos['current_value'] = quantity * current_price
                enriched_pos['value'] = enriched_pos['current_value']  # Add 'value' field for compatibility
            elif 'value' in pos and pos['value']:
                # If value already exists, keep it
                enriched_pos['current_value'] = float(pos['value'])

            # Calculate gain/loss if cost basis is available
            if 'cost_basis' in pos and pos['cost_basis']:
                cost_basis = float(pos['cost_basis'])
                current_val = enriched_pos.get('current_value', 0)

                enriched_pos['gain_loss'] = current_val - cost_basis

                if cost_basis > 0:
                    enriched_pos['gain_loss_pct'] = (
                        (current_val - cost_basis) / cost_basis * 100
                    )

            # Get detailed stock info
            stock_info = get_stock_info(ticker, use_cache=use_cache)

            if stock_info:
                enriched_pos['stock_info'] = stock_info
            else:
                logger.warning(f"Could not fetch detailed info for {ticker}")

            enriched_pos['enrichment_status'] = 'success'
            enriched_pos['enriched_at'] = datetime.now().isoformat()

            logger.info(f"Successfully enriched position: {ticker}")

        except Exception as e:
            logger.error(f"Error enriching position {ticker}: {e}", exc_info=True)
            enriched_pos['enrichment_status'] = 'failed'
            enriched_pos['enrichment_error'] = str(e)

        enriched_positions.append(enriched_pos)

    success_count = sum(1 for p in enriched_positions if p.get('enrichment_status') == 'success')
    logger.info(f"Enriched {success_count}/{len(enriched_positions)} positions successfully")

    return enriched_positions


def clear_cache() -> None:
    """
    Clear all cached market data.

    Useful for forcing fresh data fetches or managing memory.

    Example:
        >>> clear_cache()
        >>> price = get_current_price("AAPL")  # Will fetch fresh data
    """
    global _price_cache, _info_cache
    _price_cache.clear()
    _info_cache.clear()
    logger.info("Cleared all market data cache")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the current cache.

    Returns:
        Dictionary with cache statistics

    Example:
        >>> stats = get_cache_stats()
        >>> print(f"Price cache: {stats['price_cache_size']} entries")
    """
    return {
        "price_cache_size": len(_price_cache),
        "info_cache_size": len(_info_cache),
        "price_tickers": list(_price_cache.keys()),
        "info_tickers": list(_info_cache.keys()),
    }


if __name__ == "__main__":
    # Example usage / testing
    import sys

    print("\n📊 Market Data Fetcher - Test Mode\n")

    # Test tickers
    test_tickers = ["AAPL", "SPY", "TSLA", "INVALID123"]

    if len(sys.argv) > 1:
        test_tickers = sys.argv[1:]

    print(f"Testing with tickers: {', '.join(test_tickers)}\n")

    # Test get_current_price
    print("=" * 60)
    print("Testing get_current_price()")
    print("=" * 60)

    for ticker in test_tickers:
        price = get_current_price(ticker)
        if price:
            print(f"✅ {ticker}: ${price:.2f}")
        else:
            print(f"❌ {ticker}: Failed to fetch price")

    print()

    # Test get_stock_info
    print("=" * 60)
    print("Testing get_stock_info()")
    print("=" * 60)

    for ticker in test_tickers[:2]:  # Only test first 2 to avoid rate limits
        info = get_stock_info(ticker)
        if info:
            print(f"\n✅ {info['ticker']}: {info['name']}")
            print(f"   Sector: {info.get('sector', 'N/A')}")
            print(f"   Market Cap: ${info.get('market_cap', 0):,.0f}")
            print(f"   Current Price: ${info.get('current_price', 0):.2f}")
        else:
            print(f"\n❌ {ticker}: Failed to fetch info")

    print()

    # Test enrich_positions
    print("=" * 60)
    print("Testing enrich_positions()")
    print("=" * 60)

    sample_positions = [
        {
            "ticker": "AAPL",
            "quantity": 10,
            "cost_basis": 1500.00
        },
        {
            "ticker": "SPY",
            "quantity": 5,
            "cost_basis": 2000.00
        }
    ]

    print(f"\nEnriching {len(sample_positions)} sample positions...\n")
    enriched = enrich_positions(sample_positions)

    for pos in enriched:
        if pos.get('enrichment_status') == 'success':
            print(f"✅ {pos['ticker']}")
            print(f"   Quantity: {pos['quantity']}")
            print(f"   Current Price: ${pos['current_price']:.2f}")
            print(f"   Current Value: ${pos['current_value']:.2f}")
            if 'gain_loss' in pos:
                print(f"   Gain/Loss: ${pos['gain_loss']:.2f} ({pos['gain_loss_pct']:+.2f}%)")
            print()
        else:
            print(f"❌ {pos['ticker']}: {pos.get('enrichment_error', 'Unknown error')}\n")

    # Show cache stats
    print("=" * 60)
    print("Cache Statistics")
    print("=" * 60)

    stats = get_cache_stats()
    print(f"Price cache entries: {stats['price_cache_size']}")
    print(f"Info cache entries: {stats['info_cache_size']}")
    print()
