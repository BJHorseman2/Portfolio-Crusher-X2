"""
Tax Loss Harvesting Module for Portfolio Crusher X2

Implements tax loss harvesting strategies to optimize portfolio tax efficiency.
Based on algorithms from https://github.com/danguetta/rebalancer

Identifies unrealized losses, finds replacement securities to maintain portfolio
allocation while avoiding wash sale rules.
"""

import logging
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        raise


def check_wash_sale_violation(
    ticker: str,
    transaction_date: datetime,
    transaction_history: List[Dict[str, Any]],
    wash_sale_days: int = 30
) -> bool:
    """
    Check if a transaction would trigger a wash sale violation.

    A wash sale occurs when you sell a security at a loss and purchase the same
    or substantially identical security within 30 days before or after the sale.

    Args:
        ticker: Stock ticker symbol to check
        transaction_date: Date of the proposed sale
        transaction_history: List of past transactions with 'ticker', 'date',
                           'action' (buy/sell) fields
        wash_sale_days: Number of days for wash sale window (default 30)

    Returns:
        True if wash sale violation would occur, False if safe to harvest

    Example:
        >>> history = [
        ...     {"ticker": "SPY", "date": datetime(2024, 1, 1), "action": "buy"},
        ...     {"ticker": "VOO", "date": datetime(2024, 1, 15), "action": "sell"}
        ... ]
        >>> check_wash_sale_violation("SPY", datetime(2024, 1, 20), history)
        True
    """
    if not transaction_history:
        logger.info(f"No transaction history provided for {ticker}, no wash sale risk")
        return False

    ticker_normalized = ticker.upper().strip()
    wash_sale_window_start = transaction_date - timedelta(days=wash_sale_days)
    wash_sale_window_end = transaction_date + timedelta(days=wash_sale_days)

    logger.debug(
        f"Checking wash sale for {ticker_normalized} on {transaction_date.date()}, "
        f"window: {wash_sale_window_start.date()} to {wash_sale_window_end.date()}"
    )

    for transaction in transaction_history:
        if not isinstance(transaction, dict):
            logger.warning(f"Skipping invalid transaction: {transaction}")
            continue

        trans_ticker = transaction.get('ticker', '').upper().strip()
        trans_date = transaction.get('date')
        trans_action = transaction.get('action', '').lower()

        if not trans_date or not trans_ticker:
            logger.warning(f"Skipping transaction with missing data: {transaction}")
            continue

        # Convert to datetime if needed
        if isinstance(trans_date, str):
            try:
                trans_date = datetime.fromisoformat(trans_date.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid date format in transaction: {trans_date}")
                continue

        # Check if same ticker and within wash sale window
        if trans_ticker == ticker_normalized:
            if wash_sale_window_start <= trans_date <= wash_sale_window_end:
                # Don't count the sale transaction itself
                if trans_date != transaction_date:
                    logger.warning(
                        f"Wash sale violation detected: {ticker_normalized} was "
                        f"{trans_action} on {trans_date.date()}, within window"
                    )
                    return True

    logger.info(f"No wash sale violation for {ticker_normalized}")
    return False


def identify_tax_loss_opportunities(
    positions: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Identify positions with harvestable tax losses.

    Finds positions with unrealized losses that exceed configured thresholds
    and are not subject to wash sale restrictions.

    Args:
        positions: List of position dictionaries with keys:
            - ticker: str
            - current_value: float
            - cost_basis: float
            - quantity: float
            - purchase_date: datetime or str (ISO format)
        config: Configuration dictionary with tax_loss_harvesting settings

    Returns:
        List of harvestable positions with additional fields:
            - loss_amount: float (unrealized loss in dollars)
            - loss_pct: float (unrealized loss as percentage)
            - harvestable: bool
            - harvest_exclusion_reason: str (if not harvestable)

    Example:
        >>> config = load_config()
        >>> positions = [
        ...     {
        ...         "ticker": "ARKK",
        ...         "quantity": 100,
        ...         "cost_basis": 8000,
        ...         "current_value": 7000,
        ...         "purchase_date": datetime(2024, 1, 1)
        ...     }
        ... ]
        >>> opportunities = identify_tax_loss_opportunities(positions, config)
        >>> for opp in opportunities:
        ...     if opp['harvestable']:
        ...         print(f"{opp['ticker']}: ${opp['loss_amount']:.2f} loss")
    """
    if not positions:
        logger.warning("No positions provided for tax loss harvesting")
        return []

    tax_config = config.get('tax_loss_harvesting', {})
    min_loss_threshold = tax_config.get('min_loss_threshold', 100)
    min_loss_pct = tax_config.get('min_loss_pct', 3)
    wash_sale_days = tax_config.get('wash_sale_days', 30)

    logger.info(
        f"Identifying tax loss opportunities with thresholds: "
        f"${min_loss_threshold} or {min_loss_pct}%"
    )

    harvestable_positions = []
    current_date = datetime.now()

    for position in positions:
        if not isinstance(position, dict):
            logger.warning(f"Skipping invalid position: {position}")
            continue

        ticker = position.get('ticker')
        current_value = position.get('current_value')
        cost_basis = position.get('cost_basis')
        purchase_date = position.get('purchase_date')

        # Create enriched position copy
        enriched_position = position.copy()
        enriched_position['harvestable'] = False

        # Validation checks
        if not ticker:
            logger.warning("Skipping position without ticker")
            enriched_position['harvest_exclusion_reason'] = 'Missing ticker'
            harvestable_positions.append(enriched_position)
            continue

        if current_value is None or cost_basis is None:
            logger.info(f"Skipping {ticker}: missing current_value or cost_basis")
            enriched_position['harvest_exclusion_reason'] = 'Missing value/basis data'
            harvestable_positions.append(enriched_position)
            continue

        # Convert to float
        try:
            current_value = float(current_value)
            cost_basis = float(cost_basis)
        except (ValueError, TypeError):
            logger.warning(f"Skipping {ticker}: invalid value/basis format")
            enriched_position['harvest_exclusion_reason'] = 'Invalid value/basis format'
            harvestable_positions.append(enriched_position)
            continue

        # Calculate loss
        loss_amount = current_value - cost_basis
        enriched_position['loss_amount'] = loss_amount

        if cost_basis > 0:
            loss_pct = (loss_amount / cost_basis) * 100
            enriched_position['loss_pct'] = loss_pct
        else:
            enriched_position['loss_pct'] = 0

        # Check if position has a loss
        if loss_amount >= 0:
            logger.debug(f"{ticker}: No loss (${loss_amount:.2f})")
            enriched_position['harvest_exclusion_reason'] = 'No unrealized loss'
            harvestable_positions.append(enriched_position)
            continue

        # Check if loss exceeds thresholds
        abs_loss = abs(loss_amount)
        abs_loss_pct = abs(enriched_position['loss_pct'])

        if abs_loss < min_loss_threshold and abs_loss_pct < min_loss_pct:
            logger.debug(
                f"{ticker}: Loss ${abs_loss:.2f} ({abs_loss_pct:.2f}%) "
                f"below thresholds"
            )
            enriched_position['harvest_exclusion_reason'] = 'Loss below threshold'
            harvestable_positions.append(enriched_position)
            continue

        # Check wash sale restriction (30-day rule)
        if purchase_date:
            # Convert to datetime if string
            if isinstance(purchase_date, str):
                try:
                    purchase_date = datetime.fromisoformat(
                        purchase_date.replace('Z', '+00:00')
                    )
                except ValueError:
                    logger.warning(f"{ticker}: Invalid purchase_date format")
                    purchase_date = None

            if purchase_date:
                days_held = (current_date - purchase_date).days

                if days_held < wash_sale_days:
                    logger.info(
                        f"{ticker}: Purchased {days_held} days ago, "
                        f"within {wash_sale_days}-day wash sale window"
                    )
                    enriched_position['harvest_exclusion_reason'] = (
                        f'Purchased within {wash_sale_days} days'
                    )
                    enriched_position['days_held'] = days_held
                    harvestable_positions.append(enriched_position)
                    continue

        # Position is harvestable
        enriched_position['harvestable'] = True
        logger.info(
            f"✅ {ticker}: Harvestable loss ${abs_loss:.2f} ({abs_loss_pct:.2f}%)"
        )
        harvestable_positions.append(enriched_position)

    harvestable_count = sum(1 for p in harvestable_positions if p.get('harvestable'))
    logger.info(
        f"Found {harvestable_count}/{len(harvestable_positions)} "
        f"harvestable positions"
    )

    return harvestable_positions


def find_replacement_security(
    ticker: str,
    config: Dict[str, Any],
    recent_sales: Optional[List[str]] = None
) -> Optional[str]:
    """
    Find a replacement security for tax loss harvesting.

    Looks up suitable replacement tickers from configuration to maintain
    portfolio allocation while avoiding wash sale violations.

    Args:
        ticker: Ticker symbol to find replacement for
        config: Configuration dictionary with replacement_pairs
        recent_sales: List of tickers sold in last 30 days (to avoid wash sales)

    Returns:
        Replacement ticker symbol, or None if no suitable replacement found

    Example:
        >>> config = load_config()
        >>> replacement = find_replacement_security("SPY", config)
        >>> print(f"Replace SPY with {replacement}")
        Replace SPY with VOO

        >>> # With recent sales to avoid
        >>> replacement = find_replacement_security(
        ...     "SPY",
        ...     config,
        ...     recent_sales=["VOO"]
        ... )
        >>> print(f"Replace SPY with {replacement}")
        Replace SPY with IVV
    """
    ticker_normalized = ticker.upper().strip()

    tax_config = config.get('tax_loss_harvesting', {})
    replacement_pairs = tax_config.get('replacement_pairs', {})

    if ticker_normalized not in replacement_pairs:
        logger.warning(
            f"No replacement pairs configured for {ticker_normalized}"
        )
        return None

    candidates = replacement_pairs[ticker_normalized]

    if not candidates:
        logger.warning(f"Empty replacement list for {ticker_normalized}")
        return None

    # Normalize recent sales list
    recent_sales_normalized = []
    if recent_sales:
        recent_sales_normalized = [s.upper().strip() for s in recent_sales]

    logger.info(
        f"Finding replacement for {ticker_normalized}, "
        f"candidates: {candidates}, recent sales: {recent_sales_normalized}"
    )

    # Find first candidate not in recent sales
    for candidate in candidates:
        candidate_normalized = candidate.upper().strip()

        if candidate_normalized not in recent_sales_normalized:
            logger.info(
                f"Selected replacement: {ticker_normalized} -> {candidate_normalized}"
            )
            return candidate_normalized

    # All candidates were recently sold
    logger.warning(
        f"All replacement candidates for {ticker_normalized} were recently sold: "
        f"{candidates}"
    )
    return None


def generate_harvest_plan(
    positions: List[Dict[str, Any]],
    config: Dict[str, Any],
    transaction_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate a complete tax loss harvesting plan.

    Combines position analysis, replacement security selection, and tax benefit
    calculation into a comprehensive harvest plan.

    Args:
        positions: List of portfolio positions
        config: Configuration dictionary
        transaction_history: Optional list of past transactions for wash sale checking

    Returns:
        Dictionary with harvest plan:
        {
            'total_losses': float,
            'estimated_tax_benefit': float,
            'harvest_transactions': [
                {
                    'action': 'harvest',
                    'sell_ticker': str,
                    'sell_shares': float,
                    'buy_ticker': str,
                    'buy_value': float,
                    'loss_amount': float,
                    'tax_benefit': float,
                    'wash_sale_safe': bool
                }
            ]
        }

    Example:
        >>> config = load_config()
        >>> positions = [
        ...     {
        ...         "ticker": "ARKK",
        ...         "quantity": 100,
        ...         "cost_basis": 8000,
        ...         "current_value": 7000,
        ...         "purchase_date": datetime(2024, 1, 1)
        ...     }
        ... ]
        >>> plan = generate_harvest_plan(positions, config)
        >>> print(f"Total tax benefit: ${plan['estimated_tax_benefit']:.2f}")
        >>> for tx in plan['harvest_transactions']:
        ...     print(f"Sell {tx['sell_ticker']}, buy {tx['buy_ticker']}")
    """
    logger.info("Generating tax loss harvest plan")

    if transaction_history is None:
        transaction_history = []

    # Get configuration
    tax_config = config.get('tax_loss_harvesting', {})
    assumed_tax_rate = tax_config.get('assumed_tax_rate', 0.25)  # 25% default
    wash_sale_days = tax_config.get('wash_sale_days', 30)

    # Identify harvestable positions
    harvestable_positions = identify_tax_loss_opportunities(positions, config)

    # Filter to only harvestable ones
    eligible_positions = [
        p for p in harvestable_positions if p.get('harvestable', False)
    ]

    logger.info(f"Processing {len(eligible_positions)} eligible positions for harvesting")

    # Generate harvest transactions
    harvest_transactions = []
    total_losses = 0.0
    current_date = datetime.now()

    # Build list of recently sold tickers from transaction history
    cutoff_date = current_date - timedelta(days=wash_sale_days)
    recent_sales = []

    for transaction in transaction_history:
        if not isinstance(transaction, dict):
            continue

        trans_date = transaction.get('date')
        trans_action = transaction.get('action', '').lower()
        trans_ticker = transaction.get('ticker')

        if not trans_date or not trans_ticker:
            continue

        # Convert to datetime if string
        if isinstance(trans_date, str):
            try:
                trans_date = datetime.fromisoformat(
                    trans_date.replace('Z', '+00:00')
                )
            except ValueError:
                continue

        if trans_date >= cutoff_date and trans_action == 'sell':
            recent_sales.append(trans_ticker.upper().strip())

    logger.info(f"Recently sold tickers (last {wash_sale_days} days): {recent_sales}")

    # Process each harvestable position
    for position in eligible_positions:
        ticker = position.get('ticker')
        quantity = position.get('quantity')
        loss_amount = position.get('loss_amount')
        current_value = position.get('current_value')

        if not ticker or quantity is None or loss_amount is None:
            logger.warning(f"Skipping position with missing data: {position}")
            continue

        # Find replacement security
        replacement_ticker = find_replacement_security(
            ticker,
            config,
            recent_sales=recent_sales
        )

        if not replacement_ticker:
            logger.warning(
                f"No suitable replacement found for {ticker}, skipping harvest"
            )
            continue

        # Check for wash sale violation
        wash_sale_violation = check_wash_sale_violation(
            replacement_ticker,
            current_date,
            transaction_history,
            wash_sale_days
        )

        # Calculate tax benefit
        abs_loss = abs(loss_amount)
        tax_benefit = abs_loss * assumed_tax_rate

        # Create harvest transaction
        harvest_tx = {
            'action': 'harvest',
            'sell_ticker': ticker,
            'sell_shares': float(quantity),
            'buy_ticker': replacement_ticker,
            'buy_value': float(current_value),
            'loss_amount': abs_loss,
            'tax_benefit': tax_benefit,
            'wash_sale_safe': not wash_sale_violation
        }

        harvest_transactions.append(harvest_tx)
        total_losses += abs_loss

        # Add replacement to recent sales to avoid circular swaps
        recent_sales.append(ticker)

        logger.info(
            f"Harvest plan: Sell {ticker} ({quantity:.4f} shares), "
            f"buy {replacement_ticker} (${current_value:.2f}), "
            f"loss: ${abs_loss:.2f}, tax benefit: ${tax_benefit:.2f}, "
            f"wash sale safe: {not wash_sale_violation}"
        )

    # Calculate total tax benefit
    estimated_tax_benefit = total_losses * assumed_tax_rate

    plan = {
        'total_losses': total_losses,
        'estimated_tax_benefit': estimated_tax_benefit,
        'assumed_tax_rate': assumed_tax_rate,
        'harvest_transactions': harvest_transactions,
        'generated_at': current_date.isoformat(),
        'positions_analyzed': len(positions),
        'positions_harvestable': len(eligible_positions),
        'transactions_generated': len(harvest_transactions)
    }

    logger.info(
        f"Harvest plan complete: {len(harvest_transactions)} transactions, "
        f"${total_losses:.2f} losses, ${estimated_tax_benefit:.2f} tax benefit"
    )

    return plan


if __name__ == "__main__":
    # Example usage and testing
    import sys

    print("\n📊 Tax Loss Harvester - Test Mode\n")

    # Load configuration
    try:
        config = load_config('config.yaml')
        print("✅ Configuration loaded successfully\n")
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)

    # Sample positions for testing
    sample_positions = [
        {
            "ticker": "ARKK",
            "quantity": 100,
            "cost_basis": 8000.00,
            "current_value": 7000.00,
            "purchase_date": datetime(2024, 1, 1)
        },
        {
            "ticker": "ICLN",
            "quantity": 50,
            "cost_basis": 2500.00,
            "current_value": 2200.00,
            "purchase_date": datetime(2024, 2, 15)
        },
        {
            "ticker": "SPY",
            "quantity": 20,
            "cost_basis": 9000.00,
            "current_value": 9500.00,  # Gain, not harvestable
            "purchase_date": datetime(2024, 1, 10)
        },
        {
            "ticker": "ARKG",
            "quantity": 75,
            "cost_basis": 3000.00,
            "current_value": 2900.00,  # Small loss
            "purchase_date": datetime(2024, 3, 1)
        },
        {
            "ticker": "TAN",
            "quantity": 30,
            "cost_basis": 1500.00,
            "current_value": 1200.00,
            "purchase_date": datetime.now() - timedelta(days=15)  # Too recent
        }
    ]

    # Sample transaction history
    sample_history = [
        {
            "ticker": "VOO",
            "date": datetime.now() - timedelta(days=10),
            "action": "sell",
            "shares": 10
        },
        {
            "ticker": "QTEC",
            "date": datetime.now() - timedelta(days=45),
            "action": "buy",
            "shares": 20
        }
    ]

    print("=" * 70)
    print("Test 1: Identify Tax Loss Opportunities")
    print("=" * 70)

    opportunities = identify_tax_loss_opportunities(sample_positions, config)

    print(f"\nAnalyzed {len(opportunities)} positions:\n")
    for opp in opportunities:
        ticker = opp.get('ticker')
        harvestable = opp.get('harvestable', False)
        loss = opp.get('loss_amount', 0)
        loss_pct = opp.get('loss_pct', 0)
        reason = opp.get('harvest_exclusion_reason', 'N/A')

        if harvestable:
            print(f"✅ {ticker}: ${abs(loss):.2f} loss ({abs(loss_pct):.2f}%)")
        else:
            print(f"❌ {ticker}: {reason}")

    print("\n" + "=" * 70)
    print("Test 2: Find Replacement Securities")
    print("=" * 70)

    test_tickers = ["SPY", "ARKK", "ICLN", "INVALID"]

    for ticker in test_tickers:
        replacement = find_replacement_security(ticker, config)
        if replacement:
            print(f"✅ {ticker} -> {replacement}")
        else:
            print(f"❌ {ticker}: No replacement found")

    print("\n" + "=" * 70)
    print("Test 3: Check Wash Sale Violations")
    print("=" * 70)

    test_date = datetime.now()
    test_checks = [
        ("VOO", test_date),  # Recently sold, should violate
        ("SPY", test_date),  # Not in history, should be safe
        ("QTEC", test_date)  # Sold > 30 days ago, should be safe
    ]

    for ticker, date in test_checks:
        violation = check_wash_sale_violation(ticker, date, sample_history)
        status = "⚠️  VIOLATION" if violation else "✅ SAFE"
        print(f"{status}: {ticker}")

    print("\n" + "=" * 70)
    print("Test 4: Generate Complete Harvest Plan")
    print("=" * 70)

    plan = generate_harvest_plan(sample_positions, config, sample_history)

    print(f"\n📋 Harvest Plan Summary:")
    print(f"   Positions analyzed: {plan['positions_analyzed']}")
    print(f"   Positions harvestable: {plan['positions_harvestable']}")
    print(f"   Transactions generated: {plan['transactions_generated']}")
    print(f"   Total losses: ${plan['total_losses']:.2f}")
    print(f"   Estimated tax benefit: ${plan['estimated_tax_benefit']:.2f}")
    print(f"   Assumed tax rate: {plan['assumed_tax_rate']*100:.0f}%")

    if plan['harvest_transactions']:
        print(f"\n📝 Harvest Transactions:\n")
        for i, tx in enumerate(plan['harvest_transactions'], 1):
            print(f"   {i}. {tx['action'].upper()}")
            print(f"      Sell: {tx['sell_shares']:.4f} shares of {tx['sell_ticker']}")
            print(f"      Buy:  ${tx['buy_value']:.2f} of {tx['buy_ticker']}")
            print(f"      Loss: ${tx['loss_amount']:.2f}")
            print(f"      Tax benefit: ${tx['tax_benefit']:.2f}")
            print(f"      Wash sale safe: {'✅ Yes' if tx['wash_sale_safe'] else '⚠️  No'}")
            print()
    else:
        print("\n   No harvest transactions generated")

    print("=" * 70)
    print("✅ All tests completed")
    print("=" * 70)
