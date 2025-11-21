"""
Portfolio Crusher X2 - Streamlit Web Application

AI-Powered Portfolio Analysis with Hub-and-Spoke Strategy
"""

import streamlit as st
import os
from dotenv import load_dotenv
import yaml
import pandas as pd
from PIL import Image
import io
import base64
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import traceback

# Import all modules
from ocr_processor import extract_positions_from_image
from data_fetcher import enrich_positions
from portfolio_classifier import classify_portfolio, load_config
from theme_analyzer import analyze_all_themes
from tax_loss_harvester import generate_harvest_plan
from rebalancer import calculate_rebalancing_needs, generate_rebalancing_trades
from ai_analyzer import AIAnalyzer

# RAG engine is optional (requires additional packages)
try:
    from rag_engine import initialize_rag_db, query_context
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    initialize_rag_db = None
    query_context = None

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Portfolio Crusher X2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1f77b4, #2ca02c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .position-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ===========================
# SESSION STATE INITIALIZATION
# ===========================

def initialize_session_state():
    """Initialize all session state variables"""
    if 'positions' not in st.session_state:
        st.session_state.positions = []
    if 'classified_portfolio' not in st.session_state:
        st.session_state.classified_portfolio = None
    if 'enriched_positions' not in st.session_state:
        st.session_state.enriched_positions = []
    if 'harvest_plan' not in st.session_state:
        st.session_state.harvest_plan = None
    if 'rebalancing_needs' not in st.session_state:
        st.session_state.rebalancing_needs = None
    if 'rebalancing_trades' not in st.session_state:
        st.session_state.rebalancing_trades = None
    if 'theme_analyses' not in st.session_state:
        st.session_state.theme_analyses = []
    if 'ai_analyzer' not in st.session_state:
        st.session_state.ai_analyzer = None
    if 'rag_db' not in st.session_state:
        st.session_state.rag_db = None
    if 'uploaded_image' not in st.session_state:
        st.session_state.uploaded_image = None
    if 'config' not in st.session_state:
        st.session_state.config = None


# ===========================
# HELPER FUNCTIONS
# ===========================

def format_currency(value: float) -> str:
    """Format value as currency"""
    if value >= 0:
        return f"${value:,.2f}"
    else:
        return f"-${abs(value):,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage"""
    return f"{value:.2f}%"


def get_recommendation_color(action: str) -> str:
    """Get color for recommendation action"""
    colors = {
        'strong_buy': '#2ca02c',
        'buy': '#98df8a',
        'hold': '#ffbb78',
        'sell': '#ff7f0e',
        'strong_sell': '#d62728',
        'add': '#2ca02c',
        'reduce': '#ff7f0e',
        'maintain': '#1f77b4'
    }
    return colors.get(action.lower(), '#1f77b4')


def check_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is set"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    return api_key is not None and len(api_key) > 0


def load_config_file() -> Dict[str, Any]:
    """Load configuration from config.yaml"""
    try:
        return load_config('config.yaml')
    except Exception as e:
        st.error(f"Failed to load config.yaml: {str(e)}")
        return {}


def validate_uploaded_file(uploaded_file) -> tuple[bool, str]:
    """Validate uploaded file"""
    if uploaded_file is None:
        return False, "No file uploaded"

    # Check file size
    file_size_mb = uploaded_file.size / (1024 * 1024)
    max_size_mb = st.session_state.config.get('security', {}).get('max_file_size_mb', 10)

    if file_size_mb > max_size_mb:
        return False, f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)"

    # Check file type
    allowed_types = st.session_state.config.get('security', {}).get('allowed_file_types', [])
    if uploaded_file.type not in allowed_types:
        return False, f"File type {uploaded_file.type} not allowed. Allowed types: {', '.join(allowed_types)}"

    return True, "Valid"


def create_allocation_pie_chart(classified_portfolio: Dict[str, Any]) -> go.Figure:
    """Create pie chart for portfolio allocation"""
    allocations = classified_portfolio['allocations']

    labels = []
    values = []
    colors = []

    if allocations['hub_value'] > 0:
        labels.append(f"Hub (S&P 500)<br>{format_percentage(allocations['hub_pct'])}")
        values.append(allocations['hub_value'])
        colors.append('#1f77b4')

    if allocations['spokes_value'] > 0:
        labels.append(f"Spokes (Themes)<br>{format_percentage(allocations['spokes_pct'])}")
        values.append(allocations['spokes_value'])
        colors.append('#2ca02c')

    if allocations['bonds_value'] > 0:
        labels.append(f"Bonds<br>{format_percentage(allocations['bonds_pct'])}")
        values.append(allocations['bonds_value'])
        colors.append('#ff7f0e')

    if allocations['unclassified_value'] > 0:
        labels.append(f"Unclassified<br>{format_percentage(allocations['unclassified_pct'])}")
        values.append(allocations['unclassified_value'])
        colors.append('#d62728')

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors),
        hole=0.4,
        textposition='inside',
        textinfo='label',
        hovertemplate='%{label}<br>Value: %{value:$,.2f}<extra></extra>'
    )])

    fig.update_layout(
        title="Portfolio Allocation",
        showlegend=True,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )

    return fig


def create_rebalancing_chart(rebalancing_needs: Dict[str, Any]) -> go.Figure:
    """Create bar chart comparing current vs target allocations"""
    categories = []
    current_pcts = []
    target_pcts = []

    for category in ['hub', 'spokes', 'bonds']:
        if category in rebalancing_needs:
            data = rebalancing_needs[category]
            categories.append(category.capitalize())
            current_pcts.append(data.get('current_pct', 0))
            target_pcts.append(data.get('target_pct', 0))

    fig = go.Figure(data=[
        go.Bar(name='Current', x=categories, y=current_pcts, marker_color='#1f77b4'),
        go.Bar(name='Target', x=categories, y=target_pcts, marker_color='#2ca02c')
    ])

    fig.update_layout(
        title="Current vs Target Allocation",
        xaxis_title="Category",
        yaxis_title="Percentage (%)",
        barmode='group',
        height=400,
        showlegend=True
    )

    return fig


def create_theme_allocation_chart(classified_portfolio: Dict[str, Any]) -> go.Figure:
    """Create bar chart for theme allocations"""
    spokes = classified_portfolio.get('spokes', {})
    total_value = classified_portfolio['allocations']['total_value']

    if total_value == 0:
        return go.Figure()

    themes = []
    values = []
    percentages = []

    for theme_name, positions in spokes.items():
        theme_value = sum(pos.get('value', 0) for pos in positions)
        if theme_value > 0:
            themes.append(theme_name.replace('_', ' ').title())
            values.append(theme_value)
            percentages.append((theme_value / total_value) * 100)

    fig = go.Figure(data=[
        go.Bar(
            x=themes,
            y=percentages,
            text=[f"{format_currency(v)}<br>{p:.1f}%" for v, p in zip(values, percentages)],
            textposition='auto',
            marker_color='#2ca02c',
            hovertemplate='%{x}<br>Value: %{text}<extra></extra>'
        )
    ])

    fig.update_layout(
        title="Thematic Spoke Allocation",
        xaxis_title="Theme",
        yaxis_title="Percentage (%)",
        height=400,
        showlegend=False
    )

    return fig


def display_position_card(position: Dict[str, Any], show_recommendation: bool = False):
    """Display a position as a card"""
    ticker = position.get('ticker', 'N/A')
    quantity = position.get('quantity', 0)
    value = position.get('value', position.get('current_value', 0))
    cost_basis = position.get('cost_basis')

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"**{ticker}**")
        stock_info = position.get('stock_info', {})
        if stock_info and 'longName' in stock_info:
            st.caption(stock_info['longName'][:50])

    with col2:
        st.metric("Shares", f"{quantity:.2f}")

    with col3:
        st.metric("Value", format_currency(value))

    if cost_basis and cost_basis > 0:
        gain_loss = value - cost_basis
        gain_loss_pct = ((value - cost_basis) / cost_basis) * 100

        col4, col5 = st.columns(2)
        with col4:
            st.metric(
                "Gain/Loss",
                format_currency(gain_loss),
                delta=f"{gain_loss_pct:.2f}%",
                delta_color="normal" if gain_loss >= 0 else "inverse"
            )

    if show_recommendation and 'ai_recommendation' in position:
        rec = position['ai_recommendation']
        action = rec.get('action', 'hold')
        reasoning = rec.get('reasoning', '')

        color = get_recommendation_color(action)
        st.markdown(f"<div style='background-color: {color}20; padding: 0.5rem; border-radius: 0.3rem; border-left: 3px solid {color};'>"
                   f"<strong>Recommendation:</strong> {action.upper()}<br>"
                   f"<small>{reasoning[:150]}...</small></div>", unsafe_allow_html=True)


# ===========================
# TAB IMPLEMENTATIONS
# ===========================

def render_upload_tab():
    """Render the Portfolio Upload tab"""
    st.header("📤 Upload Portfolio")
    st.markdown("Upload a screenshot of your portfolio from any brokerage platform.")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['jpg', 'jpeg', 'png', 'pdf'],
            help="Upload a clear screenshot of your portfolio holdings"
        )

        if uploaded_file is not None:
            # Validate file
            is_valid, message = validate_uploaded_file(uploaded_file)

            if not is_valid:
                st.error(message)
                return

            # Display image
            if uploaded_file.type.startswith('image/'):
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Portfolio Screenshot", use_column_width=True)
                st.session_state.uploaded_image = uploaded_file

            # Extract positions button
            if st.button("🔍 Extract Positions", type="primary", use_container_width=True):
                with st.spinner("Extracting positions from image using AI..."):
                    try:
                        # Read image data
                        uploaded_file.seek(0)
                        image_data = uploaded_file.read()

                        # Extract positions
                        result = extract_positions_from_image(
                            image_data=image_data,
                            mime_type=uploaded_file.type
                        )

                        if result['success']:
                            st.session_state.positions = result['positions']
                            st.success(f"✅ Successfully extracted {len(result['positions'])} positions!")

                            # Show metadata if available
                            metadata = result.get('metadata', {})
                            if metadata.get('broker'):
                                st.info(f"Detected broker: {metadata['broker']}")
                        else:
                            st.error(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.code(traceback.format_exc())

    with col2:
        st.info("""
        **Tips for best results:**
        - Use a clear, high-resolution screenshot
        - Ensure all position information is visible
        - Include ticker symbols, shares, and values
        - Supported brokers: Robinhood, Fidelity, Schwab, E*TRADE, etc.
        """)

    # Display extracted positions
    if st.session_state.positions:
        st.markdown("---")
        st.subheader("Extracted Positions")

        # Convert to DataFrame for editing
        df = pd.DataFrame(st.session_state.positions)

        # Ensure required columns exist
        if 'ticker' not in df.columns:
            df['ticker'] = ''
        if 'quantity' not in df.columns:
            df['quantity'] = 0.0
        if 'current_value' not in df.columns:
            df['current_value'] = 0.0
        if 'cost_basis' not in df.columns:
            df['cost_basis'] = None

        # Select columns to display
        display_cols = ['ticker', 'quantity', 'current_value', 'cost_basis', 'confidence']
        display_cols = [col for col in display_cols if col in df.columns]

        # Data editor
        edited_df = st.data_editor(
            df[display_cols],
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", width="small", required=True),
                "quantity": st.column_config.NumberColumn("Shares", format="%.2f", required=True),
                "current_value": st.column_config.NumberColumn("Current Value", format="$%.2f"),
                "cost_basis": st.column_config.NumberColumn("Cost Basis", format="$%.2f"),
                "confidence": st.column_config.SelectboxColumn("Confidence", options=["high", "medium", "low"])
            }
        )

        # Update button
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Save Changes", use_container_width=True):
                st.session_state.positions = edited_df.to_dict('records')
                st.success("✅ Positions updated!")

        with col_b:
            if st.button("🚀 Enrich with Market Data", type="primary", use_container_width=True):
                with st.spinner("Fetching current market data..."):
                    try:
                        enriched = enrich_positions(st.session_state.positions)
                        st.session_state.enriched_positions = enriched

                        # Update positions with enriched data
                        st.session_state.positions = enriched

                        successful = sum(1 for p in enriched if p.get('enrichment_status') == 'success')
                        st.success(f"✅ Enriched {successful}/{len(enriched)} positions with market data!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Enrichment failed: {str(e)}")


def render_analysis_tab():
    """Render the Portfolio Analysis tab"""
    st.header("📊 Portfolio Analysis")

    if not st.session_state.positions:
        st.warning("⚠️ Please upload and extract positions first in the Upload tab.")
        return

    # Run analysis button
    if st.button("🔍 Run Full Analysis", type="primary", use_container_width=True):
        with st.spinner("Analyzing portfolio..."):
            try:
                # Classify portfolio
                classified = classify_portfolio(
                    st.session_state.positions,
                    st.session_state.config
                )
                st.session_state.classified_portfolio = classified

                # Analyze themes
                if classified['spokes']:
                    theme_analyses = analyze_all_themes(classified, st.session_state.config)
                    st.session_state.theme_analyses = theme_analyses

                # Initialize AI analyzer if not already done
                if st.session_state.ai_analyzer is None:
                    st.session_state.ai_analyzer = AIAnalyzer(st.session_state.config)

                st.success("✅ Analysis complete!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.code(traceback.format_exc())

    # Display results if analysis has been run
    if st.session_state.classified_portfolio:
        classified = st.session_state.classified_portfolio
        allocations = classified['allocations']

        st.markdown("---")

        # Summary metrics
        st.subheader("Portfolio Overview")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Value", format_currency(allocations['total_value']))
        with col2:
            st.metric("Hub (S&P 500)", format_percentage(allocations['hub_pct']))
        with col3:
            st.metric("Spokes (Themes)", format_percentage(allocations['spokes_pct']))
        with col4:
            st.metric("Bonds", format_percentage(allocations['bonds_pct']))

        # Allocation chart
        st.plotly_chart(create_allocation_pie_chart(classified), use_container_width=True)

        # Theme breakdown
        if classified['spokes']:
            st.plotly_chart(create_theme_allocation_chart(classified), use_container_width=True)

        # Tabs for detailed breakdown
        detail_tabs = st.tabs(["Hub Positions", "Spoke Positions", "Bond Positions", "Unclassified"])

        with detail_tabs[0]:
            st.subheader("Hub (S&P 500 Core)")
            if classified['hub']:
                for position in classified['hub']:
                    with st.container():
                        display_position_card(position)
                        st.markdown("---")
            else:
                st.info("No hub positions found.")

        with detail_tabs[1]:
            st.subheader("Spokes (Thematic Satellites)")
            if classified['spokes']:
                for theme_name, positions in classified['spokes'].items():
                    if positions:
                        st.markdown(f"### {theme_name.replace('_', ' ').title()}")
                        for position in positions:
                            with st.container():
                                display_position_card(position)
                                st.markdown("---")
            else:
                st.info("No spoke positions found.")

        with detail_tabs[2]:
            st.subheader("Bonds")
            if classified['bonds']:
                for position in classified['bonds']:
                    with st.container():
                        display_position_card(position)
                        st.markdown("---")
            else:
                st.info("No bond positions found.")

        with detail_tabs[3]:
            st.subheader("Unclassified Positions")
            if classified['unclassified']:
                st.warning("⚠️ These positions don't match the hub-and-spoke strategy.")
                for position in classified['unclassified']:
                    with st.container():
                        display_position_card(position)
                        st.markdown("---")
            else:
                st.success("✅ All positions are classified!")

        # AI Recommendations Section
        st.markdown("---")
        st.subheader("🤖 AI Recommendations")

        if st.button("Generate AI Recommendations", use_container_width=True):
            with st.spinner("Analyzing positions with AI..."):
                try:
                    if st.session_state.ai_analyzer is None:
                        st.session_state.ai_analyzer = AIAnalyzer(st.session_state.config)

                    analyzer = st.session_state.ai_analyzer

                    # Analyze each position
                    for position in st.session_state.positions:
                        ticker = position.get('ticker')
                        if ticker:
                            # Get relevant context from RAG
                            context = ""
                            if RAG_AVAILABLE and st.session_state.rag_db:
                                rag_results = query_context(
                                    f"Investment outlook for {ticker}",
                                    db_client=st.session_state.rag_db
                                )
                                if rag_results:
                                    context = "\n".join([r.get('content', '') for r in rag_results[:3]])

                            # Analyze position
                            recommendation = analyzer.analyze_position(
                                position=position,
                                portfolio_context=classified,
                                market_context=context
                            )

                            position['ai_recommendation'] = recommendation

                    st.success("✅ AI recommendations generated!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ AI analysis failed: {str(e)}")
                    st.code(traceback.format_exc())


def render_tax_harvesting_tab():
    """Render the Tax Loss Harvesting tab"""
    st.header("💰 Tax Loss Harvesting")

    if not st.session_state.positions:
        st.warning("⚠️ Please upload and extract positions first in the Upload tab.")
        return

    st.markdown("""
    Tax loss harvesting allows you to sell losing positions to offset capital gains,
    while immediately buying similar securities to maintain your market exposure.
    """)

    # Generate harvest plan button
    if st.button("🔍 Generate Harvest Plan", type="primary", use_container_width=True):
        with st.spinner("Analyzing tax loss harvesting opportunities..."):
            try:
                harvest_plan = generate_harvest_plan(
                    st.session_state.positions,
                    st.session_state.config
                )
                st.session_state.harvest_plan = harvest_plan
                st.success("✅ Harvest plan generated!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Failed to generate harvest plan: {str(e)}")
                st.code(traceback.format_exc())

    # Display harvest plan
    if st.session_state.harvest_plan:
        plan = st.session_state.harvest_plan

        st.markdown("---")

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Losses", format_currency(plan.get('total_losses', 0)))
        with col2:
            st.metric("Estimated Tax Benefit", format_currency(plan.get('estimated_tax_benefit', 0)))
        with col3:
            st.metric("Opportunities Found", len(plan.get('harvest_transactions', [])))

        # Harvest transactions
        transactions = plan.get('harvest_transactions', [])

        if transactions:
            st.subheader("Recommended Harvest Transactions")

            for i, tx in enumerate(transactions, 1):
                with st.expander(f"#{i}: Harvest {tx['sell_ticker']} → {tx['buy_ticker']} ({format_currency(tx['loss_amount'])} loss)"):
                    col_a, col_b = st.columns(2)

                    with col_a:
                        st.markdown("**Sell:**")
                        st.write(f"- Ticker: {tx['sell_ticker']}")
                        st.write(f"- Shares: {tx['sell_shares']:.2f}")
                        st.write(f"- Loss: {format_currency(tx['loss_amount'])}")

                    with col_b:
                        st.markdown("**Buy:**")
                        st.write(f"- Ticker: {tx['buy_ticker']}")
                        st.write(f"- Value: {format_currency(tx['buy_value'])}")
                        st.write(f"- Tax Benefit: {format_currency(tx['tax_benefit'])}")

                    # Wash sale warning
                    if not tx.get('wash_sale_safe', True):
                        st.warning("⚠️ **Wash Sale Alert:** This transaction may violate the 30-day wash sale rule!")
                    else:
                        st.success("✅ Wash sale compliant")

                    # Rationale
                    if 'rationale' in tx:
                        st.info(f"**Rationale:** {tx['rationale']}")
        else:
            st.info("No tax loss harvesting opportunities found. Your portfolio positions are currently in positive territory!")

    else:
        st.info("Click 'Generate Harvest Plan' to identify tax loss harvesting opportunities.")


def render_rebalancing_tab():
    """Render the Rebalancing tab"""
    st.header("🔄 Portfolio Rebalancing")

    if not st.session_state.classified_portfolio:
        st.warning("⚠️ Please run portfolio analysis first in the Analysis tab.")
        return

    st.markdown("""
    Rebalancing ensures your portfolio stays aligned with your target allocation.
    Add new cash to maintain your hub-and-spoke strategy.
    """)

    # New cash input
    col1, col2 = st.columns([3, 1])
    with col1:
        new_cash = st.number_input(
            "New Cash to Invest ($)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            help="Enter the amount of new cash you want to add to your portfolio"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🔍 Analyze Rebalancing", type="primary", use_container_width=True)

    # Calculate rebalancing needs
    if analyze_button or st.session_state.rebalancing_needs:
        with st.spinner("Calculating rebalancing needs..."):
            try:
                # Calculate needs
                needs = calculate_rebalancing_needs(
                    st.session_state.classified_portfolio,
                    st.session_state.config
                )
                st.session_state.rebalancing_needs = needs

                # Generate trades
                trades = generate_rebalancing_trades(
                    rebalancing_needs=needs,
                    classified_portfolio=st.session_state.classified_portfolio,
                    config=st.session_state.config,
                    new_cash=new_cash
                )
                st.session_state.rebalancing_trades = trades

                st.success("✅ Rebalancing analysis complete!")

            except Exception as e:
                st.error(f"❌ Rebalancing analysis failed: {str(e)}")
                st.code(traceback.format_exc())
                return

    # Display results
    if st.session_state.rebalancing_needs:
        needs = st.session_state.rebalancing_needs

        st.markdown("---")

        # Rebalancing status
        if needs['needs_rebalancing']:
            st.warning(f"⚠️ **Rebalancing Recommended** - Maximum deviation: {format_percentage(needs['max_deviation'])}")
        else:
            st.success("✅ **Portfolio is well-balanced!**")

        # Allocation comparison chart
        st.plotly_chart(create_rebalancing_chart(needs), use_container_width=True)

        # Detailed breakdown
        st.subheader("Allocation Breakdown")

        categories = ['hub', 'spokes', 'bonds']
        for category in categories:
            if category in needs:
                data = needs[category]

                with st.expander(f"{category.capitalize()} - {data['action'].upper()}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Current", format_percentage(data['current_pct']))
                    with col2:
                        st.metric("Target", format_percentage(data['target_pct']))
                    with col3:
                        deviation = data['deviation']
                        st.metric("Deviation", format_percentage(abs(deviation)),
                                delta=format_percentage(deviation))
                    with col4:
                        amount = data['amount']
                        action_label = "Add" if amount > 0 else "Reduce"
                        st.metric(action_label, format_currency(abs(amount)))

        # Theme-level analysis
        if 'themes' in needs.get('spokes', {}):
            st.subheader("Theme-Level Adjustments")

            themes_data = needs['spokes']['themes']
            for theme_name, theme_data in themes_data.items():
                action = theme_data['action']
                if action != 'maintain':
                    color = get_recommendation_color(action)

                    st.markdown(f"""
                    <div style='background-color: {color}20; padding: 1rem; border-radius: 0.5rem;
                                border-left: 3px solid {color}; margin-bottom: 1rem;'>
                        <h4>{theme_name.replace('_', ' ').title()}</h4>
                        <p><strong>Action:</strong> {action.upper()}</p>
                        <p><strong>Current:</strong> {format_percentage(theme_data['current_pct'])} |
                           <strong>Target:</strong> {format_percentage(theme_data['target_pct'])} |
                           <strong>Deviation:</strong> {format_percentage(theme_data['deviation'])}</p>
                        <p><strong>Amount:</strong> {format_currency(abs(theme_data['amount']))}</p>
                    </div>
                    """, unsafe_allow_html=True)

        # Trade recommendations
        if st.session_state.rebalancing_trades and isinstance(st.session_state.rebalancing_trades, dict):
            st.markdown("---")
            st.subheader("Recommended Trades")

            trades = st.session_state.rebalancing_trades.get('trades', [])

            if trades:
                for trade in trades:
                    action_color = '#2ca02c' if trade['action'] == 'buy' else '#ff7f0e'

                    st.markdown(f"""
                    <div style='background-color: {action_color}20; padding: 1rem; border-radius: 0.5rem;
                                margin-bottom: 1rem; border-left: 3px solid {action_color};'>
                        <h4>{trade['action'].upper()} {trade['ticker']}</h4>
                        <p><strong>Shares:</strong> {trade['shares']:.2f} |
                           <strong>Value:</strong> {format_currency(trade['value'])}</p>
                        <p><strong>Category:</strong> {trade['category'].title()}</p>
                        {f"<p><strong>Rationale:</strong> {trade['rationale']}</p>" if 'rationale' in trade else ''}
                    </div>
                    """, unsafe_allow_html=True)

                # Summary
                total_buys = sum(t['value'] for t in trades if t['action'] == 'buy')
                total_sells = sum(t['value'] for t in trades if t['action'] == 'sell')

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Buys", format_currency(total_buys))
                with col2:
                    st.metric("Total Sells", format_currency(total_sells))
                with col3:
                    st.metric("Net Cash Flow", format_currency(total_buys - total_sells))
            else:
                st.info("No specific trades needed at this time.")


def render_quarterly_review_tab():
    """Render the Quarterly Review tab"""
    st.header("📋 Quarterly Portfolio Review")

    if not st.session_state.classified_portfolio:
        st.warning("⚠️ Please run portfolio analysis first in the Analysis tab.")
        return

    st.markdown("""
    Generate a comprehensive quarterly review report summarizing your portfolio performance,
    allocation status, and actionable recommendations.
    """)

    # Generate report button
    if st.button("📄 Generate Quarterly Report", type="primary", use_container_width=True):
        with st.spinner("Generating comprehensive report..."):
            try:
                # Initialize AI analyzer if needed
                if st.session_state.ai_analyzer is None:
                    st.session_state.ai_analyzer = AIAnalyzer(st.session_state.config)

                analyzer = st.session_state.ai_analyzer

                # Generate portfolio analysis first if not available
                portfolio_analysis = analyzer.analyze_portfolio(
                    classified_portfolio=st.session_state.classified_portfolio,
                    config=st.session_state.config
                )

                # Get theme analyses
                theme_analyses = st.session_state.theme_analyses if st.session_state.theme_analyses else []

                # Get harvest plan (or generate empty one)
                harvest_plan = st.session_state.harvest_plan if st.session_state.harvest_plan else {
                    'total_losses': 0,
                    'estimated_tax_benefit': 0,
                    'harvest_transactions': []
                }

                # Get rebalancing needs (or generate empty one)
                rebalancing_needs = st.session_state.rebalancing_needs
                if not rebalancing_needs:
                    rebalancing_needs = calculate_rebalancing_needs(
                        st.session_state.classified_portfolio,
                        st.session_state.config
                    )
                    st.session_state.rebalancing_needs = rebalancing_needs

                # Generate report using AI
                report = analyzer.generate_quarterly_review(
                    portfolio_analysis=portfolio_analysis,
                    theme_analyses=theme_analyses,
                    harvest_plan=harvest_plan,
                    rebalancing_needs=rebalancing_needs
                )

                st.session_state.quarterly_report = report
                st.success("✅ Report generated!")

            except Exception as e:
                st.error(f"❌ Report generation failed: {str(e)}")
                st.code(traceback.format_exc())
                return

    # Display report
    if hasattr(st.session_state, 'quarterly_report') and st.session_state.quarterly_report:
        report = st.session_state.quarterly_report

        st.markdown("---")

        # Download button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            report_date = datetime.now().strftime("%Y-%m-%d")
            st.download_button(
                label="📥 Download Report (Markdown)",
                data=report,
                file_name=f"portfolio_review_{report_date}.md",
                mime="text/markdown",
                use_container_width=True
            )

        # Display formatted report
        st.markdown("---")
        st.markdown(report, unsafe_allow_html=False)

    else:
        # Show preview of what will be in the report
        st.info("""
        The quarterly report will include:

        - **Executive Summary**: Overall portfolio health and key metrics
        - **Performance Analysis**: Returns, gains/losses, and benchmark comparison
        - **Allocation Review**: Hub-and-spoke alignment vs targets
        - **Theme Analysis**: Performance of thematic satellites
        - **Tax Optimization**: Tax loss harvesting opportunities
        - **Rebalancing Recommendations**: Specific actions to take
        - **Market Outlook**: AI-powered insights on market conditions
        - **Action Items**: Prioritized next steps

        Click "Generate Quarterly Report" to create your personalized review.
        """)


# ===========================
# MAIN APPLICATION
# ===========================

def main():
    """Main application logic"""

    # Initialize session state
    initialize_session_state()

    # Check for API key
    if not check_api_key():
        st.error("""
        ❌ **ANTHROPIC_API_KEY not found!**

        Please set your Anthropic API key in one of these ways:

        1. Create a `.env` file in the project root with:
           ```
           ANTHROPIC_API_KEY=your_key_here
           ```

        2. Set it as an environment variable:
           ```bash
           export ANTHROPIC_API_KEY=your_key_here
           ```

        Get your API key from: https://console.anthropic.com/
        """)
        st.stop()

    # Load configuration
    if st.session_state.config is None:
        config = load_config_file()
        if not config:
            st.error("❌ Failed to load config.yaml. Please check the file exists and is valid.")
            st.stop()
        st.session_state.config = config

    # Header
    st.markdown('<h1 class="main-header">📊 Portfolio Crusher X2</h1>', unsafe_allow_html=True)
    st.markdown("**AI-Powered Portfolio Analysis with Hub-and-Spoke Strategy**")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Portfolio summary
        if st.session_state.classified_portfolio:
            st.subheader("Portfolio Summary")
            allocations = st.session_state.classified_portfolio['allocations']
            st.metric("Total Value", format_currency(allocations['total_value']))
            st.metric("# Positions", len(st.session_state.positions))

            st.markdown("---")

        # Model selection
        st.subheader("AI Settings")
        model_option = st.selectbox(
            "Claude Model",
            ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
            help="Select the Claude model for AI analysis"
        )

        if st.session_state.config:
            st.session_state.config['ai_settings']['model'] = model_option

        st.markdown("---")

        # RAG initialization
        st.subheader("Knowledge Base")
        if RAG_AVAILABLE:
            if st.button("🔄 Initialize RAG Database", use_container_width=True):
                with st.spinner("Initializing knowledge base..."):
                    try:
                        db_client = initialize_rag_db()
                        st.session_state.rag_db = db_client
                        st.success("✅ RAG database initialized!")
                    except Exception as e:
                        st.error(f"❌ RAG initialization failed: {str(e)}")

            if st.session_state.rag_db:
                st.success("✅ Knowledge base active")
        else:
            st.info("ℹ️ Knowledge base feature not available in lite version")

        st.markdown("---")

        # About
        st.subheader("About")
        st.markdown("""
        **Portfolio Crusher X2** uses AI to analyze your portfolio
        against the hub-and-spoke investment strategy.

        Built with Claude, Streamlit, and real-time market data.

        [Documentation](#) | [GitHub](#)
        """)

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📤 Upload",
        "📊 Analysis",
        "💰 Tax Harvesting",
        "🔄 Rebalancing",
        "📋 Quarterly Review"
    ])

    with tab1:
        render_upload_tab()

    with tab2:
        render_analysis_tab()

    with tab3:
        render_tax_harvesting_tab()

    with tab4:
        render_rebalancing_tab()

    with tab5:
        render_quarterly_review_tab()


if __name__ == "__main__":
    main()
