"""
Theme Analyzer Module

Analyzes thematic spoke positions to determine if they are overweight, underweight,
or properly balanced relative to target allocations defined in the investment philosophy.
"""

from typing import Dict, List, Any, Optional
import yaml


def analyze_theme(
    theme_name: str,
    positions: List[Dict[str, Any]],
    config: Dict[str, Any],
    total_portfolio_value: Optional[float] = None
) -> Dict[str, Any]:
    """
    Analyze a specific thematic spoke for allocation status and recommendations.

    Args:
        theme_name: Theme category identifier (e.g., 'ai', 'clean_energy')
        positions: List of positions in this theme
        config: Configuration dictionary loaded from config.yaml
        total_portfolio_value: Total portfolio value for percentage calculations.
            If None, calculates from positions in the theme only.

    Returns:
        Dictionary containing theme analysis:
        {
            'theme': str,
            'theme_display_name': str,
            'total_value': float,
            'position_count': int,
            'target_pct': float,
            'current_pct': float,
            'status': str,  # 'overweight', 'underweight', 'balanced'
            'deviation_pct': float,
            'positions': list,
            'recommendation': str,  # 'add', 'reduce', 'maintain'
            'target_value': float,
            'difference_value': float
        }

    Raises:
        ValueError: If theme_name is not found in config or positions is invalid
        KeyError: If required config keys are missing
    """
    if not theme_name:
        raise ValueError("Theme name cannot be empty")

    if positions is None:
        positions = []

    # Find theme configuration
    theme_config = None
    try:
        themes = config['equity_allocation']['spokes']['themes']
        for theme in themes:
            if theme['category'] == theme_name:
                theme_config = theme
                break

        if theme_config is None:
            raise ValueError(f"Theme '{theme_name}' not found in configuration")

    except KeyError as e:
        raise KeyError(f"Missing required config key: {e}")

    # Calculate theme value
    total_value = sum(pos.get('value', 0) for pos in positions)
    position_count = len(positions)

    # Get target percentage
    target_pct = theme_config.get('target_pct', 0)

    # Calculate current percentage
    if total_portfolio_value is None or total_portfolio_value == 0:
        # If no portfolio value provided, use theme value as 100%
        current_pct = 100 if total_value > 0 else 0
        total_portfolio_value = total_value
    else:
        current_pct = (total_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0

    # Calculate deviation
    deviation_pct = current_pct - target_pct

    # Determine status and recommendation
    # Use rebalancing threshold from config if available
    try:
        threshold = config.get('rebalancing', {}).get('threshold_pct', 5)
    except (KeyError, AttributeError):
        threshold = 5  # Default threshold

    # Determine status
    if abs(deviation_pct) <= threshold * 0.3:  # Within 30% of threshold
        status = 'balanced'
        recommendation = 'maintain'
    elif deviation_pct > 0:
        status = 'overweight'
        recommendation = 'reduce'
    else:
        status = 'underweight'
        recommendation = 'add'

    # Calculate target value and difference
    target_value = (target_pct / 100) * total_portfolio_value
    difference_value = total_value - target_value

    # Get conviction level
    conviction = theme_config.get('conviction', 'medium')

    return {
        'theme': theme_name,
        'theme_display_name': theme_config.get('name', theme_name),
        'total_value': round(total_value, 2),
        'position_count': position_count,
        'target_pct': round(target_pct, 2),
        'current_pct': round(current_pct, 2),
        'status': status,
        'deviation_pct': round(deviation_pct, 2),
        'positions': positions,
        'recommendation': recommendation,
        'target_value': round(target_value, 2),
        'difference_value': round(difference_value, 2),
        'conviction': conviction,
        'tickers': [pos.get('ticker', '') for pos in positions]
    }


def analyze_all_themes(
    classified_portfolio: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Analyze all thematic spokes in the classified portfolio.

    Args:
        classified_portfolio: Classified portfolio from portfolio_classifier.classify_portfolio()
        config: Configuration dictionary loaded from config.yaml

    Returns:
        List of theme analysis dictionaries, sorted by deviation (most overweight first)

    Raises:
        ValueError: If classified_portfolio is invalid
        KeyError: If required keys are missing
    """
    if not classified_portfolio:
        raise ValueError("Classified portfolio cannot be empty")

    try:
        spokes = classified_portfolio['spokes']
        total_value = classified_portfolio['allocations']['total_value']
    except KeyError as e:
        raise KeyError(f"Missing required key in classified_portfolio: {e}")

    if total_value == 0:
        raise ValueError("Total portfolio value cannot be zero")

    # Analyze each theme
    theme_analyses = []

    for theme_name, positions in spokes.items():
        try:
            analysis = analyze_theme(
                theme_name=theme_name,
                positions=positions,
                config=config,
                total_portfolio_value=total_value
            )
            theme_analyses.append(analysis)
        except (ValueError, KeyError) as e:
            # Log error but continue with other themes
            print(f"Warning: Could not analyze theme '{theme_name}': {e}")
            continue

    # Sort by deviation (most overweight first, then most underweight)
    theme_analyses.sort(key=lambda x: x['deviation_pct'], reverse=True)

    return theme_analyses


def get_rebalancing_recommendations(
    theme_analyses: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate specific rebalancing recommendations based on theme analyses.

    Args:
        theme_analyses: List of theme analysis dictionaries from analyze_all_themes()
        config: Configuration dictionary

    Returns:
        Dictionary containing rebalancing recommendations:
        {
            'needs_rebalancing': bool,
            'themes_to_reduce': list,
            'themes_to_add': list,
            'balanced_themes': list,
            'total_adjustments': float,
            'summary': str
        }
    """
    if not theme_analyses:
        return {
            'needs_rebalancing': False,
            'themes_to_reduce': [],
            'themes_to_add': [],
            'balanced_themes': [],
            'total_adjustments': 0,
            'summary': 'No themes to analyze'
        }

    # Get rebalancing threshold
    try:
        threshold = config.get('rebalancing', {}).get('threshold_pct', 5)
    except (AttributeError, TypeError):
        threshold = 5

    themes_to_reduce = []
    themes_to_add = []
    balanced_themes = []

    for analysis in theme_analyses:
        if analysis['status'] == 'overweight' and abs(analysis['deviation_pct']) > threshold * 0.3:
            themes_to_reduce.append({
                'theme': analysis['theme_display_name'],
                'category': analysis['theme'],
                'deviation_pct': analysis['deviation_pct'],
                'excess_value': analysis['difference_value'],
                'conviction': analysis['conviction']
            })
        elif analysis['status'] == 'underweight' and abs(analysis['deviation_pct']) > threshold * 0.3:
            themes_to_add.append({
                'theme': analysis['theme_display_name'],
                'category': analysis['theme'],
                'deviation_pct': analysis['deviation_pct'],
                'shortfall_value': abs(analysis['difference_value']),
                'conviction': analysis['conviction']
            })
        else:
            balanced_themes.append({
                'theme': analysis['theme_display_name'],
                'category': analysis['theme'],
                'current_pct': analysis['current_pct']
            })

    needs_rebalancing = len(themes_to_reduce) > 0 or len(themes_to_add) > 0

    # Calculate total adjustment needed
    total_adjustments = sum(abs(t['excess_value']) for t in themes_to_reduce)
    total_adjustments += sum(t['shortfall_value'] for t in themes_to_add)

    # Generate summary
    summary_lines = []
    if needs_rebalancing:
        summary_lines.append(f"Rebalancing recommended: {len(themes_to_reduce)} themes to reduce, {len(themes_to_add)} themes to add")
        if themes_to_reduce:
            summary_lines.append("\nReduce:")
            for t in themes_to_reduce:
                summary_lines.append(f"  - {t['theme']}: -{t['deviation_pct']:.2f}% (${t['excess_value']:,.2f})")
        if themes_to_add:
            summary_lines.append("\nAdd:")
            for t in themes_to_add:
                summary_lines.append(f"  - {t['theme']}: +{abs(t['deviation_pct']):.2f}% (${t['shortfall_value']:,.2f})")
    else:
        summary_lines.append("Portfolio is well-balanced. No rebalancing needed.")

    return {
        'needs_rebalancing': needs_rebalancing,
        'themes_to_reduce': themes_to_reduce,
        'themes_to_add': themes_to_add,
        'balanced_themes': balanced_themes,
        'total_adjustments': round(total_adjustments, 2),
        'summary': '\n'.join(summary_lines)
    }


def get_theme_summary(analysis: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary for a single theme analysis.

    Args:
        analysis: Theme analysis dictionary from analyze_theme()

    Returns:
        Formatted string summary
    """
    summary_lines = [
        f"Theme: {analysis['theme_display_name']} ({analysis['theme']})",
        "=" * 60,
        f"Conviction Level: {analysis['conviction'].upper()}",
        f"Current Value:    ${analysis['total_value']:,.2f} ({analysis['current_pct']:.2f}%)",
        f"Target:           {analysis['target_pct']:.2f}%",
        f"Status:           {analysis['status'].upper()}",
        f"Deviation:        {analysis['deviation_pct']:+.2f}%",
        f"Recommendation:   {analysis['recommendation'].upper()}",
        f"Positions:        {analysis['position_count']}"
    ]

    if analysis['tickers']:
        summary_lines.append(f"Tickers:          {', '.join(analysis['tickers'])}")

    if analysis['difference_value'] != 0:
        action = "reduce" if analysis['difference_value'] > 0 else "add"
        summary_lines.append(f"Action:           {action.capitalize()} ${abs(analysis['difference_value']):,.2f}")

    return "\n".join(summary_lines)


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
