"""
Portfolio Rebalancer Module

Implements hub-and-spoke rebalancing logic for Portfolio Crusher X2.
Compares current allocations vs targets and generates optimal trade instructions
while minimizing tax impact and respecting allocation constraints.
"""

from typing import Dict, List, Any, Tuple, Optional
import copy


def calculate_rebalancing_needs(
    classified_portfolio: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate rebalancing needs by comparing current allocations vs targets.

    This function analyzes the portfolio's hub (S&P 500), spoke (thematic), and bond
    allocations against targets defined in the config. The hub and spokes are calculated
    as percentages of total equity, not total portfolio.

    Args:
        classified_portfolio: Dictionary from portfolio_classifier.classify_portfolio() with:
            - 'hub': List of hub positions
            - 'spokes': Dict of theme -> positions
            - 'bonds': List of bond positions
            - 'allocations': Dict with current allocation percentages and values
        config: Configuration dictionary with equity_allocation and rebalancing settings

    Returns:
        Dictionary containing rebalancing analysis:
        {
            'needs_rebalancing': bool,  # True if any deviation exceeds threshold
            'hub': {
                'current_pct': float,  # Current % of total portfolio
                'target_pct': float,   # Target % of total portfolio
                'equity_current_pct': float,  # Current % of equity only
                'equity_target_pct': float,   # Target % of equity only (60-70%)
                'deviation': float,    # Percentage point deviation
                'action': str,         # 'add', 'reduce', or 'maintain'
                'amount': float,       # Dollar amount to add/reduce
                'value': float         # Current dollar value
            },
            'spokes': {
                'current_pct': float,
                'target_pct': float,
                'equity_current_pct': float,
                'equity_target_pct': float,
                'deviation': float,
                'action': str,
                'amount': float,
                'value': float,
                'themes': {            # Per-theme breakdown
                    'theme_name': {
                        'current_pct': float,
                        'target_pct': float,
                        'deviation': float,
                        'action': str,
                        'amount': float,
                        'value': float,
                        'conviction': str
                    }
                }
            },
            'bonds': {
                'current_pct': float,
                'target_pct': float,
                'deviation': float,
                'action': str,
                'amount': float,
                'value': float
            },
            'equity': {
                'current_pct': float,  # Total equity % of portfolio
                'target_pct': float,   # Target equity % (100% - bonds)
                'total_value': float   # Total equity value
            },
            'total_portfolio_value': float,
            'threshold_pct': float,
            'max_deviation': float
        }

    Raises:
        ValueError: If portfolio value is zero or required data is missing
        KeyError: If required config keys are missing

    Example:
        >>> config = load_config('config.yaml')
        >>> classified = classify_portfolio(positions, config)
        >>> needs = calculate_rebalancing_needs(classified, config)
        >>> if needs['needs_rebalancing']:
        ...     print(f"Hub needs to {needs['hub']['action']} ${needs['hub']['amount']:.2f}")
    """
    # Validate inputs
    if not classified_portfolio:
        raise ValueError("Classified portfolio cannot be empty")

    if not config:
        raise ValueError("Config cannot be empty")

    try:
        allocations = classified_portfolio['allocations']
        total_value = allocations['total_value']
        hub_value = allocations['hub_value']
        spokes_value = allocations['spokes_value']
        bonds_value = allocations['bonds_value']
    except KeyError as e:
        raise KeyError(f"Missing required key in classified_portfolio: {e}")

    if total_value == 0:
        raise ValueError("Total portfolio value cannot be zero")

    # Extract config values
    try:
        hub_config = config['equity_allocation']['hub']
        spokes_config = config['equity_allocation']['spokes']
        bonds_config = config['bonds']
        rebalancing_config = config['rebalancing']
    except KeyError as e:
        raise KeyError(f"Missing required config key: {e}")

    threshold_pct = rebalancing_config.get('threshold_pct', 5)

    # Get targets
    bonds_target_pct = bonds_config.get('target_pct', 30)
    equity_target_pct = 100 - bonds_target_pct

    # Hub and spokes targets are relative to EQUITY, not total portfolio
    hub_equity_target_pct = hub_config.get('target_pct', 65)
    spokes_equity_target_pct = spokes_config.get('total_target_pct', 35)

    # Calculate current equity allocation
    equity_value = hub_value + spokes_value
    equity_current_pct = (equity_value / total_value * 100) if total_value > 0 else 0

    # Calculate hub/spokes as % of total portfolio for target
    hub_target_pct = (equity_target_pct / 100) * hub_equity_target_pct
    spokes_target_pct = (equity_target_pct / 100) * spokes_equity_target_pct

    # Calculate current percentages
    hub_current_pct = (hub_value / total_value * 100) if total_value > 0 else 0
    spokes_current_pct = (spokes_value / total_value * 100) if total_value > 0 else 0
    bonds_current_pct = (bonds_value / total_value * 100) if total_value > 0 else 0

    # Calculate hub/spokes as % of equity
    hub_equity_current_pct = (hub_value / equity_value * 100) if equity_value > 0 else 0
    spokes_equity_current_pct = (spokes_value / equity_value * 100) if equity_value > 0 else 0

    # Calculate deviations
    hub_deviation = hub_current_pct - hub_target_pct
    spokes_deviation = spokes_current_pct - spokes_target_pct
    bonds_deviation = bonds_current_pct - bonds_target_pct
    equity_deviation = equity_current_pct - equity_target_pct

    # Determine actions and amounts
    def get_action_and_amount(deviation: float, threshold: float, current_value: float, target_pct: float, total: float) -> Tuple[str, float]:
        """Helper to determine action and amount based on deviation."""
        if abs(deviation) <= threshold:
            return 'maintain', 0.0
        elif deviation > 0:
            # Overweight - need to reduce
            target_value = (target_pct / 100) * total
            amount = current_value - target_value
            return 'reduce', amount
        else:
            # Underweight - need to add
            target_value = (target_pct / 100) * total
            amount = target_value - current_value
            return 'add', amount

    hub_action, hub_amount = get_action_and_amount(
        hub_deviation, threshold_pct, hub_value, hub_target_pct, total_value
    )
    spokes_action, spokes_amount = get_action_and_amount(
        spokes_deviation, threshold_pct, spokes_value, spokes_target_pct, total_value
    )
    bonds_action, bonds_amount = get_action_and_amount(
        bonds_deviation, threshold_pct, bonds_value, bonds_target_pct, total_value
    )

    # Analyze individual themes
    themes_analysis = {}
    spokes = classified_portfolio.get('spokes', {})

    for theme_category, theme_config in _get_theme_configs(config):
        theme_positions = spokes.get(theme_category, [])
        theme_value = sum(pos.get('value', 0) for pos in theme_positions)
        theme_current_pct = (theme_value / total_value * 100) if total_value > 0 else 0
        theme_target_pct = theme_config.get('target_pct', 0)
        theme_deviation = theme_current_pct - theme_target_pct

        theme_action, theme_amount = get_action_and_amount(
            theme_deviation, threshold_pct, theme_value, theme_target_pct, total_value
        )

        themes_analysis[theme_category] = {
            'current_pct': round(theme_current_pct, 2),
            'target_pct': round(theme_target_pct, 2),
            'deviation': round(theme_deviation, 2),
            'action': theme_action,
            'amount': round(theme_amount, 2),
            'value': round(theme_value, 2),
            'conviction': theme_config.get('conviction', 'medium'),
            'display_name': theme_config.get('name', theme_category)
        }

    # Determine if rebalancing is needed
    max_deviation = max(
        abs(hub_deviation),
        abs(spokes_deviation),
        abs(bonds_deviation),
        max((abs(t['deviation']) for t in themes_analysis.values()), default=0)
    )
    needs_rebalancing = max_deviation > threshold_pct

    return {
        'needs_rebalancing': needs_rebalancing,
        'hub': {
            'current_pct': round(hub_current_pct, 2),
            'target_pct': round(hub_target_pct, 2),
            'equity_current_pct': round(hub_equity_current_pct, 2),
            'equity_target_pct': round(hub_equity_target_pct, 2),
            'deviation': round(hub_deviation, 2),
            'action': hub_action,
            'amount': round(hub_amount, 2),
            'value': round(hub_value, 2)
        },
        'spokes': {
            'current_pct': round(spokes_current_pct, 2),
            'target_pct': round(spokes_target_pct, 2),
            'equity_current_pct': round(spokes_equity_current_pct, 2),
            'equity_target_pct': round(spokes_equity_target_pct, 2),
            'deviation': round(spokes_deviation, 2),
            'action': spokes_action,
            'amount': round(spokes_amount, 2),
            'value': round(spokes_value, 2),
            'themes': themes_analysis
        },
        'bonds': {
            'current_pct': round(bonds_current_pct, 2),
            'target_pct': round(bonds_target_pct, 2),
            'deviation': round(bonds_deviation, 2),
            'action': bonds_action,
            'amount': round(bonds_amount, 2),
            'value': round(bonds_value, 2)
        },
        'equity': {
            'current_pct': round(equity_current_pct, 2),
            'target_pct': round(equity_target_pct, 2),
            'total_value': round(equity_value, 2),
            'deviation': round(equity_deviation, 2)
        },
        'total_portfolio_value': round(total_value, 2),
        'threshold_pct': threshold_pct,
        'max_deviation': round(max_deviation, 2)
    }


def generate_rebalancing_trades(
    rebalancing_needs: Dict[str, Any],
    classified_portfolio: Dict[str, Any],
    config: Dict[str, Any],
    new_cash: float = 0
) -> List[Dict[str, Any]]:
    """
    Generate specific buy/sell trade instructions based on rebalancing needs.

    Prioritizes adding new cash to underweight positions to minimize selling
    (tax-efficient). Generates trades for hub, spokes, and bonds separately.

    Args:
        rebalancing_needs: Dictionary from calculate_rebalancing_needs()
        classified_portfolio: Dictionary from portfolio_classifier.classify_portfolio()
        config: Configuration dictionary
        new_cash: Amount of new cash being added to portfolio (default: 0)

    Returns:
        List of trade dictionaries:
        [
            {
                'action': str,        # 'buy' or 'sell'
                'ticker': str,        # Ticker symbol to trade
                'amount': float,      # Dollar amount to trade
                'rationale': str,     # Human-readable explanation
                'category': str,      # 'hub', 'spoke', or 'bond'
                'theme': str,         # Theme category (only for spokes)
                'priority': int       # 1 (high) to 3 (low)
            }
        ]

        Sorted by priority (high to low), then by amount (large to small).

    Raises:
        ValueError: If inputs are invalid
        KeyError: If required keys are missing

    Example:
        >>> needs = calculate_rebalancing_needs(classified, config)
        >>> trades = generate_rebalancing_trades(needs, classified, config, new_cash=5000)
        >>> for trade in trades:
        ...     print(f"{trade['action'].upper()} ${trade['amount']:.2f} of {trade['ticker']}")
        BUY $3000.00 of VOO
        BUY $2000.00 of BOTZ
    """
    if not rebalancing_needs:
        raise ValueError("Rebalancing needs cannot be empty")

    if not classified_portfolio:
        raise ValueError("Classified portfolio cannot be empty")

    if not config:
        raise ValueError("Config cannot be empty")

    if new_cash < 0:
        raise ValueError("New cash cannot be negative")

    # Extract config values
    try:
        rebalancing_config = config['rebalancing']
        min_trade_size = rebalancing_config.get('min_trade_size', 100)
    except KeyError as e:
        raise KeyError(f"Missing required config key: {e}")

    trades = []
    remaining_cash = new_cash

    # Priority 1: Add cash to underweight positions
    # Priority 2: Rebalance within existing allocations (sell overweight, buy underweight)
    # Priority 3: Minor adjustments

    # If we have new cash, allocate it according to how underweight each category is
    if remaining_cash > 0:
        cash_allocation = _allocate_new_cash(
            rebalancing_needs, remaining_cash, min_trade_size
        )

        # Generate buy trades for cash allocation
        for category, amount in cash_allocation.items():
            if amount < min_trade_size:
                continue

            if category == 'hub':
                ticker = _select_hub_ticker(classified_portfolio, config)
                trades.append({
                    'action': 'buy',
                    'ticker': ticker,
                    'amount': round(amount, 2),
                    'rationale': f'Add new cash to underweight hub position (S&P 500 core)',
                    'category': 'hub',
                    'theme': None,
                    'priority': 1
                })

            elif category == 'bonds':
                ticker = _select_bond_ticker(classified_portfolio, config)
                trades.append({
                    'action': 'buy',
                    'ticker': ticker,
                    'amount': round(amount, 2),
                    'rationale': f'Add new cash to underweight bond allocation',
                    'category': 'bond',
                    'theme': None,
                    'priority': 1
                })

            elif category.startswith('spoke_'):
                theme = category.replace('spoke_', '')
                ticker = _select_spoke_ticker(theme, classified_portfolio, config)
                theme_info = rebalancing_needs['spokes']['themes'].get(theme, {})
                theme_name = theme_info.get('display_name', theme)
                trades.append({
                    'action': 'buy',
                    'ticker': ticker,
                    'amount': round(amount, 2),
                    'rationale': f'Add new cash to underweight {theme_name} theme',
                    'category': 'spoke',
                    'theme': theme,
                    'priority': 1
                })

        remaining_cash = 0

    # Now handle rebalancing without new cash (if still needed)
    if rebalancing_needs['needs_rebalancing']:

        # Handle hub rebalancing
        hub_needs = rebalancing_needs['hub']
        if hub_needs['action'] == 'add' and hub_needs['amount'] >= min_trade_size:
            ticker = _select_hub_ticker(classified_portfolio, config)
            trades.append({
                'action': 'buy',
                'ticker': ticker,
                'amount': round(hub_needs['amount'], 2),
                'rationale': f'Increase hub to target {hub_needs["target_pct"]:.1f}% (currently {hub_needs["current_pct"]:.1f}%)',
                'category': 'hub',
                'theme': None,
                'priority': 2
            })
        elif hub_needs['action'] == 'reduce' and hub_needs['amount'] >= min_trade_size:
            # Select ticker to sell (prefer largest position)
            ticker = _select_hub_position_to_sell(classified_portfolio)
            trades.append({
                'action': 'sell',
                'ticker': ticker,
                'amount': round(hub_needs['amount'], 2),
                'rationale': f'Reduce hub to target {hub_needs["target_pct"]:.1f}% (currently {hub_needs["current_pct"]:.1f}%)',
                'category': 'hub',
                'theme': None,
                'priority': 2
            })

        # Handle individual spoke themes
        for theme, theme_needs in rebalancing_needs['spokes']['themes'].items():
            if theme_needs['action'] == 'add' and theme_needs['amount'] >= min_trade_size:
                ticker = _select_spoke_ticker(theme, classified_portfolio, config)
                conviction = theme_needs.get('conviction', 'medium')
                priority = 1 if conviction == 'high' else 2 if conviction == 'medium' else 3
                trades.append({
                    'action': 'buy',
                    'ticker': ticker,
                    'amount': round(theme_needs['amount'], 2),
                    'rationale': f'Increase {theme_needs["display_name"]} to target {theme_needs["target_pct"]:.1f}% (currently {theme_needs["current_pct"]:.1f}%, {conviction} conviction)',
                    'category': 'spoke',
                    'theme': theme,
                    'priority': priority
                })
            elif theme_needs['action'] == 'reduce' and theme_needs['amount'] >= min_trade_size:
                ticker = _select_spoke_position_to_sell(theme, classified_portfolio)
                conviction = theme_needs.get('conviction', 'medium')
                priority = 3 if conviction == 'high' else 2  # Harder to sell high conviction
                trades.append({
                    'action': 'sell',
                    'ticker': ticker,
                    'amount': round(theme_needs['amount'], 2),
                    'rationale': f'Reduce {theme_needs["display_name"]} to target {theme_needs["target_pct"]:.1f}% (currently {theme_needs["current_pct"]:.1f}%, {conviction} conviction)',
                    'category': 'spoke',
                    'theme': theme,
                    'priority': priority
                })

        # Handle bonds rebalancing
        bonds_needs = rebalancing_needs['bonds']
        if bonds_needs['action'] == 'add' and bonds_needs['amount'] >= min_trade_size:
            ticker = _select_bond_ticker(classified_portfolio, config)
            trades.append({
                'action': 'buy',
                'ticker': ticker,
                'amount': round(bonds_needs['amount'], 2),
                'rationale': f'Increase bonds to target {bonds_needs["target_pct"]:.1f}% (currently {bonds_needs["current_pct"]:.1f}%)',
                'category': 'bond',
                'theme': None,
                'priority': 2
            })
        elif bonds_needs['action'] == 'reduce' and bonds_needs['amount'] >= min_trade_size:
            ticker = _select_bond_position_to_sell(classified_portfolio)
            trades.append({
                'action': 'sell',
                'ticker': ticker,
                'amount': round(bonds_needs['amount'], 2),
                'rationale': f'Reduce bonds to target {bonds_needs["target_pct"]:.1f}% (currently {bonds_needs["current_pct"]:.1f}%)',
                'category': 'bond',
                'theme': None,
                'priority': 2
            })

    # Sort trades: priority (low number = high priority), then amount (large to small)
    trades.sort(key=lambda x: (x['priority'], -x['amount']))

    return trades


def optimize_for_hub_and_spoke(
    equity_positions: List[Dict[str, Any]],
    hub_target: float,
    spokes_target: float,
    theme_analyses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate optimal equity split between hub and spokes.

    Hub should be 60-70% of equity (not total portfolio).
    Spokes should be 30-40% of equity.
    Within spokes, allocate by conviction and theme strength.

    Args:
        equity_positions: List of all equity positions (hub + spokes)
        hub_target: Target percentage for hub (e.g., 65)
        spokes_target: Target percentage for spokes (e.g., 35)
        theme_analyses: List of theme analysis dicts from theme_analyzer.analyze_all_themes()

    Returns:
        Dictionary containing optimization plan:
        {
            'current_equity_value': float,
            'hub': {
                'target_pct': float,
                'target_value': float,
                'current_value': float,
                'adjustment_needed': float  # positive = add, negative = reduce
            },
            'spokes': {
                'target_pct': float,
                'target_value': float,
                'current_value': float,
                'adjustment_needed': float,
                'theme_allocation': {  # Optimal allocation within spokes
                    'theme_name': {
                        'target_pct': float,      # % of total equity
                        'target_value': float,
                        'current_value': float,
                        'adjustment_needed': float,
                        'conviction': str,
                        'priority': int
                    }
                }
            },
            'validation': {
                'total_pct': float,  # Should be 100
                'is_valid': bool
            }
        }

    Raises:
        ValueError: If inputs are invalid or percentages don't sum to 100

    Example:
        >>> equity_positions = hub_positions + spoke_positions
        >>> optimization = optimize_for_hub_and_spoke(
        ...     equity_positions, hub_target=65, spokes_target=35, theme_analyses
        ... )
        >>> print(f"Hub needs adjustment: ${optimization['hub']['adjustment_needed']:.2f}")
    """
    if not equity_positions:
        raise ValueError("Equity positions list cannot be empty")

    if hub_target + spokes_target != 100:
        raise ValueError(f"Hub target ({hub_target}%) + Spokes target ({spokes_target}%) must equal 100%")

    if hub_target < 60 or hub_target > 70:
        raise ValueError(f"Hub target must be 60-70%, got {hub_target}%")

    if spokes_target < 30 or spokes_target > 40:
        raise ValueError(f"Spokes target must be 30-40%, got {spokes_target}%")

    # Calculate total equity value
    total_equity_value = sum(pos.get('value', 0) for pos in equity_positions)

    if total_equity_value == 0:
        raise ValueError("Total equity value cannot be zero")

    # Calculate current values from positions
    hub_current_value = 0
    spokes_current_value = 0
    theme_current_values = {}

    for pos in equity_positions:
        value = pos.get('value', 0)
        category = pos.get('category', '')

        if category == 'hub':
            hub_current_value += value
        elif category == 'spoke':
            spokes_current_value += value
            theme = pos.get('theme', 'unknown')
            theme_current_values[theme] = theme_current_values.get(theme, 0) + value

    # Calculate target values
    hub_target_value = (hub_target / 100) * total_equity_value
    spokes_target_value = (spokes_target / 100) * total_equity_value

    # Calculate adjustments needed
    hub_adjustment = hub_target_value - hub_current_value
    spokes_adjustment = spokes_target_value - spokes_current_value

    # Allocate spokes target across themes based on conviction and analysis
    theme_allocation = _allocate_spokes_by_conviction(
        theme_analyses, spokes_target_value, total_equity_value, theme_current_values
    )

    # Validation
    total_pct = hub_target + spokes_target
    is_valid = abs(total_pct - 100) < 0.01

    return {
        'current_equity_value': round(total_equity_value, 2),
        'hub': {
            'target_pct': round(hub_target, 2),
            'target_value': round(hub_target_value, 2),
            'current_value': round(hub_current_value, 2),
            'adjustment_needed': round(hub_adjustment, 2)
        },
        'spokes': {
            'target_pct': round(spokes_target, 2),
            'target_value': round(spokes_target_value, 2),
            'current_value': round(spokes_current_value, 2),
            'adjustment_needed': round(spokes_adjustment, 2),
            'theme_allocation': theme_allocation
        },
        'validation': {
            'total_pct': round(total_pct, 2),
            'is_valid': is_valid
        }
    }


def calculate_efficient_trades(
    current_positions: List[Dict[str, Any]],
    target_positions: Dict[str, float],
    min_trade_size: float = 100
) -> List[Dict[str, Any]]:
    """
    Find minimal number of trades to reach target positions.

    Combines small adjustments, filters trades below minimum size,
    and prefers buys over sells for tax efficiency.

    Args:
        current_positions: List of current position dicts with 'ticker' and 'value'
        target_positions: Dict mapping ticker -> target value
        min_trade_size: Minimum trade size in dollars (default: 100)

    Returns:
        List of efficient trade dictionaries:
        [
            {
                'action': str,   # 'buy' or 'sell'
                'ticker': str,
                'amount': float,
                'current_value': float,
                'target_value': float,
                'priority': int  # 1 (buy) or 2 (sell) for tax efficiency
            }
        ]

        Sorted by priority (buys first), then by amount (largest first).

    Raises:
        ValueError: If inputs are invalid

    Example:
        >>> current = [
        ...     {'ticker': 'VOO', 'value': 10000},
        ...     {'ticker': 'BOTZ', 'value': 2000}
        ... ]
        >>> target = {'VOO': 11000, 'BOTZ': 1800, 'ICLN': 500}
        >>> trades = calculate_efficient_trades(current, target, min_trade_size=100)
        >>> for trade in trades:
        ...     print(f"{trade['action']} {trade['ticker']}: ${trade['amount']:.2f}")
        buy VOO: $1000.00
        buy ICLN: $500.00
        sell BOTZ: $200.00
    """
    if current_positions is None:
        current_positions = []

    if not target_positions:
        raise ValueError("Target positions cannot be empty")

    if min_trade_size < 0:
        raise ValueError("Minimum trade size cannot be negative")

    # Build current position map
    current_map = {}
    for pos in current_positions:
        ticker = pos.get('ticker', '').upper()
        value = pos.get('value', 0)
        if ticker:
            current_map[ticker] = current_map.get(ticker, 0) + value

    # Calculate differences
    all_tickers = set(current_map.keys()) | set(target_positions.keys())
    trades = []

    for ticker in all_tickers:
        current_value = current_map.get(ticker, 0)
        target_value = target_positions.get(ticker, 0)
        difference = target_value - current_value

        # Skip if difference is below minimum trade size
        if abs(difference) < min_trade_size:
            continue

        if difference > 0:
            # Need to buy
            trades.append({
                'action': 'buy',
                'ticker': ticker,
                'amount': round(difference, 2),
                'current_value': round(current_value, 2),
                'target_value': round(target_value, 2),
                'priority': 1  # Buys have higher priority (tax efficient)
            })
        else:
            # Need to sell
            trades.append({
                'action': 'sell',
                'ticker': ticker,
                'amount': round(abs(difference), 2),
                'current_value': round(current_value, 2),
                'target_value': round(target_value, 2),
                'priority': 2  # Sells have lower priority
            })

    # Sort by priority (buys first), then by amount (largest first)
    trades.sort(key=lambda x: (x['priority'], -x['amount']))

    return trades


# ============================================================================
# Helper Functions
# ============================================================================


def _get_theme_configs(config: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Extract theme configurations from config.

    Returns:
        List of tuples: (theme_category, theme_config_dict)
    """
    try:
        themes = config['equity_allocation']['spokes']['themes']
        return [(theme['category'], theme) for theme in themes]
    except (KeyError, TypeError):
        return []


def _allocate_new_cash(
    rebalancing_needs: Dict[str, Any],
    new_cash: float,
    min_trade_size: float
) -> Dict[str, float]:
    """
    Allocate new cash to underweight positions proportionally.

    Returns:
        Dict mapping category name -> allocated amount
    """
    # Calculate total shortfall across all underweight positions
    shortfalls = {}

    if rebalancing_needs['hub']['action'] == 'add':
        shortfalls['hub'] = rebalancing_needs['hub']['amount']

    if rebalancing_needs['bonds']['action'] == 'add':
        shortfalls['bonds'] = rebalancing_needs['bonds']['amount']

    for theme, theme_needs in rebalancing_needs['spokes']['themes'].items():
        if theme_needs['action'] == 'add':
            shortfalls[f'spoke_{theme}'] = theme_needs['amount']

    if not shortfalls:
        # No underweight positions, allocate to maintain current ratios
        # Default: put it all in hub
        return {'hub': new_cash}

    total_shortfall = sum(shortfalls.values())

    # Allocate proportionally to shortfalls
    allocation = {}
    for category, shortfall in shortfalls.items():
        if total_shortfall > 0:
            proportion = shortfall / total_shortfall
            allocated = min(new_cash * proportion, shortfall)
            if allocated >= min_trade_size:
                allocation[category] = allocated

    return allocation


def _select_hub_ticker(
    classified_portfolio: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    Select hub ticker to buy. Prefers ticker with smallest position or VOO as default.
    """
    try:
        hub_positions = classified_portfolio.get('hub', [])
        allowed_tickers = [etf['ticker'] for etf in config['equity_allocation']['hub']['allowed_etfs']]

        if hub_positions:
            # Find existing position with smallest value to balance
            min_position = min(hub_positions, key=lambda x: x.get('value', 0))
            return min_position.get('ticker', 'VOO').upper()
        else:
            # No existing positions, default to VOO (Vanguard S&P 500)
            return 'VOO'
    except (KeyError, ValueError):
        return 'VOO'


def _select_hub_position_to_sell(classified_portfolio: Dict[str, Any]) -> str:
    """
    Select hub position to sell. Prefers largest position.
    """
    try:
        hub_positions = classified_portfolio.get('hub', [])
        if hub_positions:
            max_position = max(hub_positions, key=lambda x: x.get('value', 0))
            return max_position.get('ticker', 'VOO').upper()
        else:
            return 'VOO'
    except (ValueError, KeyError):
        return 'VOO'


def _select_spoke_ticker(
    theme: str,
    classified_portfolio: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    Select spoke ticker to buy for a given theme.
    Prefers existing positions (to add to them) or first ticker in theme config.
    """
    try:
        spokes = classified_portfolio.get('spokes', {})
        theme_positions = spokes.get(theme, [])

        if theme_positions:
            # Prefer adding to smallest existing position
            min_position = min(theme_positions, key=lambda x: x.get('value', 0))
            return min_position.get('ticker', '').upper()
        else:
            # No existing positions, select from config
            themes = config['equity_allocation']['spokes']['themes']
            for theme_config in themes:
                if theme_config['category'] == theme:
                    etfs = theme_config.get('etfs', [])
                    if etfs:
                        return etfs[0].upper()

        # Fallback
        return 'SPY'
    except (KeyError, ValueError, IndexError):
        return 'SPY'


def _select_spoke_position_to_sell(
    theme: str,
    classified_portfolio: Dict[str, Any]
) -> str:
    """
    Select spoke position to sell for a given theme.
    Prefers largest position.
    """
    try:
        spokes = classified_portfolio.get('spokes', {})
        theme_positions = spokes.get(theme, [])

        if theme_positions:
            max_position = max(theme_positions, key=lambda x: x.get('value', 0))
            return max_position.get('ticker', '').upper()
        else:
            return 'SPY'
    except (ValueError, KeyError):
        return 'SPY'


def _select_bond_ticker(
    classified_portfolio: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    Select bond ticker to buy. Prefers smallest position or BND as default.
    """
    try:
        bond_positions = classified_portfolio.get('bonds', [])
        allowed_tickers = config['bonds']['allowed_etfs']

        if bond_positions:
            min_position = min(bond_positions, key=lambda x: x.get('value', 0))
            return min_position.get('ticker', 'BND').upper()
        else:
            return 'BND'
    except (KeyError, ValueError):
        return 'BND'


def _select_bond_position_to_sell(classified_portfolio: Dict[str, Any]) -> str:
    """
    Select bond position to sell. Prefers largest position.
    """
    try:
        bond_positions = classified_portfolio.get('bonds', [])
        if bond_positions:
            max_position = max(bond_positions, key=lambda x: x.get('value', 0))
            return max_position.get('ticker', 'BND').upper()
        else:
            return 'BND'
    except (ValueError, KeyError):
        return 'BND'


def _allocate_spokes_by_conviction(
    theme_analyses: List[Dict[str, Any]],
    spokes_target_value: float,
    total_equity_value: float,
    theme_current_values: Dict[str, float]
) -> Dict[str, Dict[str, Any]]:
    """
    Allocate spokes budget across themes based on conviction levels.

    High conviction themes get larger allocations.
    """
    if not theme_analyses:
        return {}

    theme_allocation = {}

    # Weight by conviction: high=3, medium=2, low=1
    conviction_weights = {'high': 3, 'medium': 2, 'low': 1}

    for analysis in theme_analyses:
        theme = analysis.get('theme', 'unknown')
        conviction = analysis.get('conviction', 'medium')
        target_pct = analysis.get('target_pct', 0)
        current_value = theme_current_values.get(theme, 0)

        # Calculate target value as % of total equity
        target_value = (target_pct / 100) * total_equity_value
        adjustment = target_value - current_value

        weight = conviction_weights.get(conviction, 2)
        priority = 1 if conviction == 'high' else 2 if conviction == 'medium' else 3

        theme_allocation[theme] = {
            'target_pct': round(target_pct, 2),
            'target_value': round(target_value, 2),
            'current_value': round(current_value, 2),
            'adjustment_needed': round(adjustment, 2),
            'conviction': conviction,
            'priority': priority,
            'weight': weight
        }

    return theme_allocation
