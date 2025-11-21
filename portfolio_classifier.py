"""
Portfolio Classifier Module

Classifies portfolio positions into hub (S&P 500 core), spoke (thematic satellites),
and bond allocations based on the Portfolio Crusher X2 investment philosophy.
"""

from typing import Dict, List, Any, Optional
import yaml


def classify_portfolio(positions: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify portfolio positions into hub, spoke, and bond categories.

    Args:
        positions: List of position dictionaries. Each position should contain:
            - ticker (str): Stock/ETF ticker symbol
            - value (float): Market value of the position
            - shares (float): Number of shares held
            Additional fields are preserved in the output.
        config: Configuration dictionary loaded from config.yaml

    Returns:
        Dictionary containing classified positions:
        {
            'hub': [positions],
            'spokes': {'ai': [positions], 'clean_energy': [positions], ...},
            'bonds': [positions],
            'unclassified': [positions],
            'allocations': {
                'hub_pct': float,
                'spokes_pct': float,
                'bonds_pct': float,
                'unclassified_pct': float,
                'total_value': float
            }
        }

    Raises:
        ValueError: If positions list is empty or config is invalid
        KeyError: If required config keys are missing
    """
    if not positions:
        raise ValueError("Positions list cannot be empty")

    if not config:
        raise ValueError("Config dictionary cannot be empty")

    # Validate required config structure
    try:
        hub_config = config['equity_allocation']['hub']
        spokes_config = config['equity_allocation']['spokes']
        bonds_config = config['bonds']
    except KeyError as e:
        raise KeyError(f"Missing required config key: {e}")

    # Extract hub ETF tickers
    hub_tickers = {etf['ticker'].upper() for etf in hub_config['allowed_etfs']}

    # Extract bond ETF tickers
    bond_tickers = {ticker.upper() for ticker in bonds_config['allowed_etfs']}

    # Build spoke theme mapping: ticker -> theme_category
    spoke_mapping = {}
    theme_categories = []

    for theme in spokes_config['themes']:
        category = theme['category']
        theme_categories.append(category)
        for ticker in theme['etfs']:
            spoke_mapping[ticker.upper()] = category

    # Initialize classification structure
    classified = {
        'hub': [],
        'spokes': {category: [] for category in theme_categories},
        'bonds': [],
        'unclassified': []
    }

    # Calculate total portfolio value
    total_value = sum(position.get('value', 0) for position in positions)

    if total_value == 0:
        raise ValueError("Total portfolio value cannot be zero")

    # Classify each position
    for position in positions:
        if 'ticker' not in position:
            raise ValueError(f"Position missing required 'ticker' field: {position}")

        ticker = position['ticker'].upper()

        if ticker in hub_tickers:
            classified['hub'].append(position)
        elif ticker in spoke_mapping:
            theme = spoke_mapping[ticker]
            classified['spokes'][theme].append(position)
        elif ticker in bond_tickers:
            classified['bonds'].append(position)
        else:
            classified['unclassified'].append(position)

    # Calculate allocation percentages
    hub_value = sum(pos.get('value', 0) for pos in classified['hub'])
    bonds_value = sum(pos.get('value', 0) for pos in classified['bonds'])
    unclassified_value = sum(pos.get('value', 0) for pos in classified['unclassified'])

    # Calculate total spokes value across all themes
    spokes_value = 0
    for theme_positions in classified['spokes'].values():
        spokes_value += sum(pos.get('value', 0) for pos in theme_positions)

    classified['allocations'] = {
        'hub_pct': round((hub_value / total_value) * 100, 2) if total_value > 0 else 0,
        'spokes_pct': round((spokes_value / total_value) * 100, 2) if total_value > 0 else 0,
        'bonds_pct': round((bonds_value / total_value) * 100, 2) if total_value > 0 else 0,
        'unclassified_pct': round((unclassified_value / total_value) * 100, 2) if total_value > 0 else 0,
        'total_value': round(total_value, 2),
        'hub_value': round(hub_value, 2),
        'spokes_value': round(spokes_value, 2),
        'bonds_value': round(bonds_value, 2),
        'unclassified_value': round(unclassified_value, 2)
    }

    return classified


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml file (default: 'config.yaml')

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}")


def get_theme_config(config: Dict[str, Any], theme_category: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific theme category.

    Args:
        config: Configuration dictionary
        theme_category: Theme category identifier (e.g., 'ai', 'clean_energy')

    Returns:
        Theme configuration dictionary or None if not found
    """
    try:
        themes = config['equity_allocation']['spokes']['themes']
        for theme in themes:
            if theme['category'] == theme_category:
                return theme
        return None
    except KeyError:
        return None


def get_classification_summary(classified: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of portfolio classification.

    Args:
        classified: Classified portfolio dictionary from classify_portfolio()

    Returns:
        Formatted string summary
    """
    allocations = classified['allocations']

    summary_lines = [
        "Portfolio Classification Summary",
        "=" * 50,
        f"Total Portfolio Value: ${allocations['total_value']:,.2f}",
        "",
        f"Hub (S&P 500):        {allocations['hub_pct']:>6.2f}% (${allocations['hub_value']:,.2f})",
        f"Spokes (Thematic):    {allocations['spokes_pct']:>6.2f}% (${allocations['spokes_value']:,.2f})",
        f"Bonds:                {allocations['bonds_pct']:>6.2f}% (${allocations['bonds_value']:,.2f})",
        f"Unclassified:         {allocations['unclassified_pct']:>6.2f}% (${allocations['unclassified_value']:,.2f})",
        "",
        "Spoke Breakdown:"
    ]

    for theme, positions in classified['spokes'].items():
        if positions:
            theme_value = sum(pos.get('value', 0) for pos in positions)
            theme_pct = (theme_value / allocations['total_value']) * 100 if allocations['total_value'] > 0 else 0
            summary_lines.append(f"  {theme:20s} {theme_pct:>6.2f}% (${theme_value:,.2f})")

    return "\n".join(summary_lines)
