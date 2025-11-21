"""
AI Analysis Engine for Portfolio Crusher X2
Uses Claude API with ReAct pattern for portfolio analysis
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI-powered portfolio analyzer using Claude API"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI analyzer

        Args:
            config: Configuration dictionary containing AI settings
        """
        self.config = config
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = Anthropic(api_key=api_key)

        # AI settings from config
        self.ai_settings = config.get('ai_settings', {})
        self.model = self.ai_settings.get('model', 'claude-3-opus-20240229')
        self.max_tokens = self.ai_settings.get('max_tokens', 4096)
        self.temperature = self.ai_settings.get('temperature', 0.7)
        self.max_retries = self.ai_settings.get('max_retries', 3)
        self.retry_delay = self.ai_settings.get('retry_delay', 1.0)

    def _call_claude(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Internal helper to call Claude API with retry logic

        Args:
            prompt: User prompt for Claude
            system_prompt: Optional system prompt to set context

        Returns:
            Claude's response text

        Raises:
            Exception: If all retry attempts fail
        """
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )

                # Extract text from response
                return response.content[0].text

            except Exception as e:
                logger.error(f"Claude API call failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("All retry attempts failed")
                    raise

    def _get_default_system_prompt(self) -> str:
        """
        Get default system prompt for portfolio analysis

        Returns:
            System prompt string
        """
        return """You are a financial analyst specializing in hub-and-spoke portfolio strategies.

Investment Philosophy:
- Hub: S&P 500 core (60-70% of equity) - stable, low-cost, diversified
- Spokes: Thematic satellites (30-40% of equity) - conviction-based themes
- Bonds: Risk management (20-40% of portfolio)

Analyze positions based on:
1. Position type (hub/spoke/bond)
2. Theme strength (for spokes)
3. Market conditions
4. Conviction level
5. Tax implications

Provide clear, actionable recommendations."""

    def analyze_position(
        self,
        position: Dict[str, Any],
        market_data: Dict[str, Any],
        context: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a single position and generate recommendation

        Args:
            position: Position data (ticker, shares, cost_basis, type, theme, etc.)
            market_data: Current market data for the position
            context: Additional context (RAG data, market conditions, etc.)
            config: Configuration dictionary

        Returns:
            Dictionary containing:
                - ticker: Stock ticker
                - recommendation: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell'
                - conviction_score: float (-2 to +2)
                - rationale: Explanation of recommendation
                - key_points: List of key points
                - risks: List of identified risks
                - opportunities: List of opportunities
        """
        ticker = position.get('ticker', 'UNKNOWN')
        position_type = position.get('type', 'unknown')
        theme = position.get('theme', 'N/A')

        logger.info(f"Analyzing position: {ticker} ({position_type})")

        # Build analysis prompt
        prompt = self._build_position_prompt(position, market_data, context, config)

        # Call Claude API
        try:
            response_text = self._call_claude(prompt)

            # Parse response into structured format
            analysis = self._parse_position_analysis(response_text, ticker)

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze position {ticker}: {str(e)}")
            # Return default hold recommendation on failure
            return {
                'ticker': ticker,
                'recommendation': 'hold',
                'conviction_score': 0.0,
                'rationale': f'Analysis failed: {str(e)}',
                'key_points': ['Unable to complete analysis'],
                'risks': ['Analysis error'],
                'opportunities': []
            }

    def _build_position_prompt(
        self,
        position: Dict[str, Any],
        market_data: Dict[str, Any],
        context: Dict[str, Any],
        config: Dict[str, Any]
    ) -> str:
        """
        Build detailed prompt for position analysis

        Args:
            position: Position data
            market_data: Market data
            context: Additional context
            config: Configuration

        Returns:
            Formatted prompt string
        """
        ticker = position.get('ticker', 'UNKNOWN')
        position_type = position.get('type', 'unknown')
        theme = position.get('theme', 'N/A')
        shares = position.get('shares', 0)
        cost_basis = position.get('cost_basis', 0)
        current_price = market_data.get('current_price', 0)
        market_value = shares * current_price
        gain_loss = market_value - (shares * cost_basis)
        gain_loss_pct = (gain_loss / (shares * cost_basis) * 100) if cost_basis > 0 else 0

        prompt = f"""Analyze the following investment position and provide a detailed recommendation.

**Position Details:**
- Ticker: {ticker}
- Position Type: {position_type.upper()}
- Theme: {theme}
- Shares: {shares}
- Cost Basis: ${cost_basis:.2f}
- Current Price: ${current_price:.2f}
- Market Value: ${market_value:,.2f}
- Gain/Loss: ${gain_loss:,.2f} ({gain_loss_pct:+.2f}%)

**Market Data:**
"""

        # Add market data details
        for key, value in market_data.items():
            if key != 'current_price':
                prompt += f"- {key}: {value}\n"

        prompt += "\n**Additional Context:**\n"

        # Add context from RAG or other sources
        if context:
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    prompt += f"- {key}: {value}\n"
                elif isinstance(value, list):
                    prompt += f"- {key}: {', '.join(map(str, value[:3]))}\n"

        prompt += f"""
**Analysis Guidelines:**
"""

        if position_type == 'hub':
            prompt += """
- Hub positions (S&P 500 core) should generally be held
- Check if position is overweight relative to target allocation (60-70% of equity)
- Recommend rebalancing only if significantly out of target range
"""
        elif position_type == 'spoke':
            prompt += """
- Evaluate theme strength and conviction level
- Consider current market trends and theme relevance
- Assess if theme thesis remains intact
- Recommend sell if theme has deteriorated or conviction has weakened
"""
        else:  # bonds
            prompt += """
- Assess bond allocation relative to target (20-40% of portfolio)
- Consider interest rate environment
- Evaluate credit quality and duration
"""

        prompt += """
**Required Output Format:**
Provide your analysis in the following JSON format:

{
  "recommendation": "<strong_buy|buy|hold|sell|strong_sell>",
  "conviction_score": <float between -2.0 and +2.0>,
  "rationale": "<2-3 sentence explanation>",
  "key_points": ["<point 1>", "<point 2>", "<point 3>"],
  "risks": ["<risk 1>", "<risk 2>"],
  "opportunities": ["<opportunity 1>", "<opportunity 2>"]
}

Provide ONLY the JSON response, no additional text."""

        return prompt

    def _parse_position_analysis(self, response_text: str, ticker: str) -> Dict[str, Any]:
        """
        Parse Claude's response into structured analysis

        Args:
            response_text: Raw response from Claude
            ticker: Stock ticker for error handling

        Returns:
            Structured analysis dictionary
        """
        try:
            # Try to extract JSON from response
            # Look for JSON block in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                analysis_data = json.loads(json_text)

                # Validate and structure the response
                analysis = {
                    'ticker': ticker,
                    'recommendation': analysis_data.get('recommendation', 'hold'),
                    'conviction_score': float(analysis_data.get('conviction_score', 0.0)),
                    'rationale': analysis_data.get('rationale', ''),
                    'key_points': analysis_data.get('key_points', []),
                    'risks': analysis_data.get('risks', []),
                    'opportunities': analysis_data.get('opportunities', [])
                }

                # Validate conviction score range
                analysis['conviction_score'] = max(-2.0, min(2.0, analysis['conviction_score']))

                # Validate recommendation
                valid_recommendations = ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell']
                if analysis['recommendation'] not in valid_recommendations:
                    analysis['recommendation'] = 'hold'

                return analysis
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            logger.error(f"Failed to parse analysis for {ticker}: {str(e)}")
            logger.debug(f"Response text: {response_text}")

            # Return fallback analysis
            return {
                'ticker': ticker,
                'recommendation': 'hold',
                'conviction_score': 0.0,
                'rationale': 'Unable to parse analysis response',
                'key_points': [response_text[:200] if response_text else 'No response'],
                'risks': ['Parse error'],
                'opportunities': []
            }

    def analyze_portfolio(
        self,
        classified_portfolio: Dict[str, Any],
        config: Dict[str, Any],
        rag_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze entire portfolio with all positions

        Args:
            classified_portfolio: Portfolio classified into hub/spokes/bonds
            config: Configuration dictionary
            rag_context: Optional RAG context for theme analysis

        Returns:
            Dictionary containing:
                - overall_health: 'excellent' | 'good' | 'fair' | 'needs_attention'
                - hub_analysis: Analysis of hub positions
                - spokes_analysis: Analysis of spoke positions
                - bonds_analysis: Analysis of bond positions
                - position_recommendations: List of all position recommendations
        """
        logger.info("Starting portfolio analysis...")

        position_recommendations = []
        hub_positions = []
        spoke_positions = []
        bond_positions = []

        # Analyze each position
        for position in classified_portfolio.get('positions', []):
            # Get market data for position (mock data for now)
            market_data = self._get_market_data(position)

            # Get context for position (use RAG if available)
            context = self._get_position_context(position, rag_context)

            # Analyze position
            analysis = self.analyze_position(position, market_data, context, config)
            position_recommendations.append(analysis)

            # Categorize by type
            position_type = position.get('type', 'unknown')
            if position_type == 'hub':
                hub_positions.append(analysis)
            elif position_type == 'spoke':
                spoke_positions.append(analysis)
            elif position_type == 'bond':
                bond_positions.append(analysis)

        # Aggregate analyses by category
        hub_analysis = self._aggregate_category_analysis(hub_positions, 'hub')
        spokes_analysis = self._aggregate_category_analysis(spoke_positions, 'spokes')
        bonds_analysis = self._aggregate_category_analysis(bond_positions, 'bonds')

        # Determine overall portfolio health
        overall_health = self._determine_overall_health(
            hub_analysis, spokes_analysis, bonds_analysis, position_recommendations
        )

        return {
            'overall_health': overall_health,
            'hub_analysis': hub_analysis,
            'spokes_analysis': spokes_analysis,
            'bonds_analysis': bonds_analysis,
            'position_recommendations': position_recommendations
        }

    def _get_market_data(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get market data for a position (placeholder for actual market data integration)

        Args:
            position: Position data

        Returns:
            Market data dictionary
        """
        # This would integrate with real market data APIs
        # For now, return mock data
        ticker = position.get('ticker', 'UNKNOWN')

        return {
            'current_price': position.get('current_price', 100.0),
            '52_week_high': 120.0,
            '52_week_low': 80.0,
            'avg_volume': 1000000,
            'market_cap': '100B',
            'pe_ratio': 25.0,
            'dividend_yield': 2.0
        }

    def _get_position_context(
        self,
        position: Dict[str, Any],
        rag_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get additional context for position analysis

        Args:
            position: Position data
            rag_context: RAG context if available

        Returns:
            Context dictionary
        """
        context = {}

        if rag_context:
            ticker = position.get('ticker', '')
            theme = position.get('theme', '')

            # Extract relevant RAG data
            if ticker in rag_context.get('ticker_data', {}):
                context['rag_insights'] = rag_context['ticker_data'][ticker]

            if theme in rag_context.get('theme_data', {}):
                context['theme_insights'] = rag_context['theme_data'][theme]

        # Add market conditions
        context['market_condition'] = 'neutral'  # This would come from market data

        return context

    def _aggregate_category_analysis(
        self,
        positions: List[Dict[str, Any]],
        category: str
    ) -> Dict[str, Any]:
        """
        Aggregate analysis for a category of positions

        Args:
            positions: List of position analyses
            category: Category name (hub/spokes/bonds)

        Returns:
            Aggregated analysis dictionary
        """
        if not positions:
            return {
                'count': 0,
                'avg_conviction': 0.0,
                'recommendations_summary': {},
                'top_risks': [],
                'top_opportunities': []
            }

        # Calculate average conviction
        avg_conviction = sum(p['conviction_score'] for p in positions) / len(positions)

        # Count recommendations
        recommendations_summary = {}
        for pos in positions:
            rec = pos['recommendation']
            recommendations_summary[rec] = recommendations_summary.get(rec, 0) + 1

        # Aggregate risks and opportunities
        all_risks = []
        all_opportunities = []

        for pos in positions:
            all_risks.extend(pos.get('risks', []))
            all_opportunities.extend(pos.get('opportunities', []))

        # Get top risks and opportunities (by frequency)
        from collections import Counter
        risk_counter = Counter(all_risks)
        opp_counter = Counter(all_opportunities)

        top_risks = [risk for risk, _ in risk_counter.most_common(5)]
        top_opportunities = [opp for opp, _ in opp_counter.most_common(5)]

        return {
            'count': len(positions),
            'avg_conviction': round(avg_conviction, 2),
            'recommendations_summary': recommendations_summary,
            'top_risks': top_risks,
            'top_opportunities': top_opportunities,
            'positions': positions
        }

    def _determine_overall_health(
        self,
        hub_analysis: Dict[str, Any],
        spokes_analysis: Dict[str, Any],
        bonds_analysis: Dict[str, Any],
        position_recommendations: List[Dict[str, Any]]
    ) -> str:
        """
        Determine overall portfolio health

        Args:
            hub_analysis: Hub category analysis
            spokes_analysis: Spokes category analysis
            bonds_analysis: Bonds category analysis
            position_recommendations: All position recommendations

        Returns:
            Health rating: 'excellent' | 'good' | 'fair' | 'needs_attention'
        """
        # Calculate average conviction across all positions
        if position_recommendations:
            avg_conviction = sum(
                p['conviction_score'] for p in position_recommendations
            ) / len(position_recommendations)
        else:
            avg_conviction = 0.0

        # Count sell recommendations
        sell_count = sum(
            1 for p in position_recommendations
            if p['recommendation'] in ['sell', 'strong_sell']
        )

        total_positions = len(position_recommendations)
        sell_ratio = sell_count / total_positions if total_positions > 0 else 0

        # Determine health based on metrics
        if avg_conviction > 1.0 and sell_ratio < 0.1:
            return 'excellent'
        elif avg_conviction > 0.5 and sell_ratio < 0.2:
            return 'good'
        elif avg_conviction > 0.0 and sell_ratio < 0.3:
            return 'fair'
        else:
            return 'needs_attention'

    def generate_quarterly_review(
        self,
        portfolio_analysis: Dict[str, Any],
        theme_analyses: List[Dict[str, Any]],
        harvest_plan: Dict[str, Any],
        rebalancing_needs: Dict[str, Any]
    ) -> str:
        """
        Generate comprehensive quarterly review report

        Args:
            portfolio_analysis: Complete portfolio analysis
            theme_analyses: List of theme-specific analyses
            harvest_plan: Tax loss harvesting plan
            rebalancing_needs: Rebalancing recommendations

        Returns:
            Formatted markdown report
        """
        logger.info("Generating quarterly review report...")

        report = "# Portfolio Crusher X2 - Quarterly Review\n\n"
        report += f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # Overview Section
        report += "## Executive Summary\n\n"
        report += f"**Overall Portfolio Health:** {portfolio_analysis['overall_health'].upper()}\n\n"

        total_positions = len(portfolio_analysis['position_recommendations'])
        hub_count = portfolio_analysis['hub_analysis']['count']
        spoke_count = portfolio_analysis['spokes_analysis']['count']
        bond_count = portfolio_analysis['bonds_analysis']['count']

        report += f"- Total Positions: {total_positions}\n"
        report += f"- Hub Positions: {hub_count}\n"
        report += f"- Spoke Positions: {spoke_count}\n"
        report += f"- Bond Positions: {bond_count}\n\n"

        # Hub Status Section
        report += "## Hub Analysis (Core S&P 500)\n\n"
        hub_analysis = portfolio_analysis['hub_analysis']
        report += f"**Average Conviction Score:** {hub_analysis['avg_conviction']:.2f}\n\n"

        if hub_analysis['recommendations_summary']:
            report += "**Recommendations Distribution:**\n"
            for rec, count in hub_analysis['recommendations_summary'].items():
                report += f"- {rec.replace('_', ' ').title()}: {count}\n"
            report += "\n"

        if hub_analysis.get('top_risks'):
            report += "**Key Risks:**\n"
            for risk in hub_analysis['top_risks'][:3]:
                report += f"- {risk}\n"
            report += "\n"

        # Spoke Themes Section
        report += "## Spoke Themes Analysis\n\n"
        spokes_analysis = portfolio_analysis['spokes_analysis']
        report += f"**Average Conviction Score:** {spokes_analysis['avg_conviction']:.2f}\n\n"

        if spokes_analysis['recommendations_summary']:
            report += "**Recommendations Distribution:**\n"
            for rec, count in spokes_analysis['recommendations_summary'].items():
                report += f"- {rec.replace('_', ' ').title()}: {count}\n"
            report += "\n"

        # Theme-by-theme breakdown
        if theme_analyses:
            report += "### Theme Breakdown\n\n"
            for theme_analysis in theme_analyses:
                theme_name = theme_analysis.get('theme', 'Unknown')
                report += f"#### {theme_name}\n\n"
                report += f"{theme_analysis.get('summary', 'No summary available')}\n\n"

        if spokes_analysis.get('top_opportunities'):
            report += "**Key Opportunities:**\n"
            for opp in spokes_analysis['top_opportunities'][:3]:
                report += f"- {opp}\n"
            report += "\n"

        # Bonds Section
        report += "## Bonds Analysis\n\n"
        bonds_analysis = portfolio_analysis['bonds_analysis']
        report += f"**Average Conviction Score:** {bonds_analysis['avg_conviction']:.2f}\n\n"

        if bonds_analysis['recommendations_summary']:
            report += "**Recommendations Distribution:**\n"
            for rec, count in bonds_analysis['recommendations_summary'].items():
                report += f"- {rec.replace('_', ' ').title()}: {count}\n"
            report += "\n"

        # Tax Harvesting Section
        report += "## Tax Loss Harvesting Opportunities\n\n"

        if harvest_plan and harvest_plan.get('harvest_transactions'):
            total_losses = harvest_plan.get('total_losses', 0)
            tax_benefit = harvest_plan.get('estimated_tax_benefit', 0)
            report += f"**Total Harvestable Losses:** ${abs(total_losses):,.2f}\n"
            report += f"**Estimated Tax Benefit:** ${tax_benefit:,.2f}\n\n"

            report += "**Harvesting Opportunities:**\n\n"
            for txn in harvest_plan['harvest_transactions'][:5]:
                sell_ticker = txn.get('sell_ticker', 'N/A')
                buy_ticker = txn.get('buy_ticker', 'N/A')
                loss = txn.get('loss_amount', 0)
                benefit = txn.get('tax_benefit', 0)
                report += f"- **{sell_ticker}** → **{buy_ticker}**: ${abs(loss):,.2f} loss (${benefit:,.2f} benefit)\n"
            report += "\n"
        else:
            report += "No tax loss harvesting opportunities identified.\n\n"

        # Rebalancing Section
        report += "## Rebalancing Recommendations\n\n"

        if rebalancing_needs and rebalancing_needs.get('needs_rebalancing'):
            report += "**Portfolio requires rebalancing:**\n\n"

            # Hub rebalancing
            hub_rebal = rebalancing_needs.get('hub', {})
            if hub_rebal.get('action') != 'maintain':
                report += f"**Hub (S&P 500):** {hub_rebal.get('action', 'N/A').title()} "
                report += f"${abs(hub_rebal.get('amount', 0)):,.2f}\n"

            # Spoke rebalancing
            spokes_rebal = rebalancing_needs.get('spokes', {})
            if spokes_rebal.get('themes'):
                report += "\n**Spokes (Themes):**\n"
                for theme, theme_data in spokes_rebal['themes'].items():
                    if theme_data.get('action') != 'maintain':
                        report += f"- {theme}: {theme_data.get('action', 'N/A').title()} "
                        report += f"${abs(theme_data.get('amount', 0)):,.2f}\n"
            report += "\n"
        else:
            report += "Portfolio is well-balanced. No immediate rebalancing needed.\n\n"

        # Position-by-Position Details
        report += "## Detailed Position Recommendations\n\n"

        for pos in portfolio_analysis['position_recommendations']:
            ticker = pos['ticker']
            rec = pos['recommendation'].replace('_', ' ').title()
            conviction = pos['conviction_score']
            rationale = pos['rationale']

            report += f"### {ticker}\n\n"
            report += f"**Recommendation:** {rec} (Conviction: {conviction:+.2f})\n\n"
            report += f"**Rationale:** {rationale}\n\n"

            if pos.get('key_points'):
                report += "**Key Points:**\n"
                for point in pos['key_points']:
                    report += f"- {point}\n"
                report += "\n"

        # Footer
        report += "---\n\n"
        report += "*This report was generated by Portfolio Crusher X2 AI Analysis Engine*\n"

        return report


# Convenience functions for direct use

def analyze_position(
    position: Dict[str, Any],
    market_data: Dict[str, Any],
    context: Dict[str, Any],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze a single position

    Args:
        position: Position data
        market_data: Current market data
        context: Additional context
        config: Configuration dictionary

    Returns:
        Position analysis dictionary
    """
    analyzer = AIAnalyzer(config)
    return analyzer.analyze_position(position, market_data, context, config)


def analyze_portfolio(
    classified_portfolio: Dict[str, Any],
    config: Dict[str, Any],
    rag_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze entire portfolio

    Args:
        classified_portfolio: Classified portfolio data
        config: Configuration dictionary
        rag_context: Optional RAG context

    Returns:
        Portfolio analysis dictionary
    """
    analyzer = AIAnalyzer(config)
    return analyzer.analyze_portfolio(classified_portfolio, config, rag_context)


def generate_quarterly_review(
    portfolio_analysis: Dict[str, Any],
    theme_analyses: List[Dict[str, Any]],
    harvest_plan: Dict[str, Any],
    rebalancing_needs: Dict[str, Any]
) -> str:
    """
    Generate quarterly review report

    Args:
        portfolio_analysis: Portfolio analysis
        theme_analyses: Theme analyses
        harvest_plan: Tax harvesting plan
        rebalancing_needs: Rebalancing needs

    Returns:
        Markdown formatted report
    """
    # Create temporary analyzer instance with minimal config
    config = {'ai_settings': {}}
    analyzer = AIAnalyzer(config)
    return analyzer.generate_quarterly_review(
        portfolio_analysis, theme_analyses, harvest_plan, rebalancing_needs
    )
