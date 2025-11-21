# Portfolio Crusher X2 - Setup Guide

Complete step-by-step guide to get Portfolio Crusher X2 running on your machine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Using the Application](#using-the-application)
6. [Adding Knowledge Base Content](#adding-knowledge-base-content)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.9 or higher**
  - Check version: `python --version` or `python3 --version`
  - Download: [python.org](https://www.python.org/downloads/)

- **Anthropic API Key**
  - Sign up: [console.anthropic.com](https://console.anthropic.com/)
  - Create API key in your account settings
  - Free tier available, Claude 3.5 Sonnet recommended

### Optional (for enhanced features)

- **Git** (for cloning the repository)
- **Virtual environment tool** (venv, conda, etc.)

---

## Installation

### Step 1: Clone or Download the Repository

**Option A: Using Git**
```bash
git clone https://github.com/BJHorseman2/Portfolio-Crusher-X2.git
cd Portfolio-Crusher-X2
```

**Option B: Download ZIP**
- Download ZIP from GitHub
- Extract to a folder
- Open terminal in that folder

### Step 2: Create Virtual Environment (Recommended)

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages:
- Streamlit (web interface)
- Anthropic (Claude API)
- ChromaDB (knowledge base)
- yfinance (market data)
- Plotly (visualizations)
- And more...

**Installation time:** ~2-5 minutes depending on your internet speed.

---

## Configuration

### Step 1: Set Up Environment Variables

**Create `.env` file:**
```bash
cp .env.template .env
```

**Edit `.env` file:**
```bash
# On macOS/Linux
nano .env

# On Windows
notepad .env
```

**Add your API key:**
```
ANTHROPIC_API_KEY=sk-ant-api03-...your-key-here...
```

**Save and close the file.**

### Step 2: Customize Investment Strategy (Optional)

Edit `config.yaml` to match your investment preferences:

```yaml
equity_allocation:
  hub:
    target_pct: 65  # Change to your target hub %

  spokes:
    themes:
      - name: "Artificial Intelligence"
        conviction: "high"  # high, medium, or low
        target_pct: 10
      # Add or remove themes as needed
```

**Key settings to review:**

1. **Hub Target:** Default 65% of equity in S&P 500
2. **Spoke Themes:** Add/remove themes based on your interests
3. **Conviction Levels:** Set to high/medium/low per theme
4. **Tax Harvesting Thresholds:** Minimum loss to harvest
5. **Rebalancing Frequency:** Quarterly by default

---

## Running the Application

### Start the Application

```bash
streamlit run app.py
```

**What happens:**
- Streamlit server starts
- Browser opens automatically to `http://localhost:8501`
- If browser doesn't open, click the URL in terminal

**Expected output:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.1.x:8501
```

### Stop the Application

Press `Ctrl+C` in the terminal.

---

## Using the Application

### 1. Portfolio Upload Tab

**Step-by-step:**

1. Take a screenshot of your portfolio from your brokerage
   - Include: ticker symbols, quantities, current values
   - Optional: cost basis if visible

2. Click "Browse files" or drag-and-drop the image

3. Click "Extract Positions" button
   - AI will process the image (~10-30 seconds)
   - Positions will appear in a table

4. Review and edit if needed
   - Click cells to edit values
   - Verify ticker symbols are correct

5. Click "Enrich with Market Data"
   - Fetches current prices from Yahoo Finance
   - Adds sector, market cap, etc.

### 2. Portfolio Analysis Tab

**What you'll see:**

- **Overall Health Score:** Excellent / Good / Fair / Needs Attention
- **Allocation Pie Chart:** Visual breakdown of hub/spokes/bonds
- **Theme Breakdown:** Bar chart of thematic allocations
- **Position Cards:** Each position with:
  - Current value and gain/loss
  - AI recommendation (Buy/Hold/Sell)
  - Rationale and key points

**AI Analysis:**
- Runs automatically when you have enriched positions
- Analyzes each position individually
- Considers hub-and-spoke strategy
- Evaluates theme strength for spokes

### 3. Tax Loss Harvesting Tab

**How it works:**

1. Click "Generate Harvest Plan"
2. System identifies positions with losses
3. Finds replacement securities to avoid wash sales
4. Calculates tax benefits (assumes 25% tax rate)

**What you'll see:**

- **Total Harvestable Losses:** Sum of all losses
- **Estimated Tax Benefit:** Losses × tax rate
- **Harvest Transactions:** Specific sell/buy pairs
  - Sell ticker → Buy ticker
  - Loss amount and tax benefit
  - Wash sale safety check

**Example:**
```
Sell ARKK (loss: $1,000) → Buy QTEC
Tax Benefit: $250
Wash Sale Safe: ✓
```

### 4. Rebalancing Tab

**Using the rebalancer:**

1. View current vs target allocations
2. (Optional) Enter new cash to invest: `$5000`
3. Click "Generate Rebalancing Trades"

**Output:**

- **Trades to Execute:** Buy/sell recommendations
- **Rationale:** Why each trade is suggested
- **Summary Metrics:**
  - Total to buy: $X,XXX
  - Total to sell: $X,XXX
  - Net cash flow: $XXX

**Strategy:**
- Prioritizes adding new cash over selling
- Maintains hub at 60-70% of equity
- Adjusts spokes based on conviction
- Minimizes tax impact

### 5. Quarterly Review Tab

**Generate comprehensive report:**

1. Click "Generate Quarterly Review Report"
2. AI creates detailed markdown report
3. Review sections:
   - Executive Summary
   - Hub Analysis
   - Spoke Themes
   - Tax Harvesting Opportunities
   - Rebalancing Recommendations
   - Position-by-Position Details

4. Click "Download Report" to save as .md file

---

## Adding Knowledge Base Content

Enhance AI recommendations with your investment philosophy.

### Add YouTube Videos

**Edit `config.yaml`:**

```yaml
data_sources:
  content_sources:
    youtube:
      enabled: true
      videos:
        - video_id: "dQw4w9WgXcQ"  # Extract from YouTube URL
          name: "Investment Strategy Overview"
          topics: ["investing", "strategy"]
```

**Get video ID from URL:**
- URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- ID: `dQw4w9WgXcQ` (after `v=`)

### Add Custom Articles/URLs

```yaml
custom_sources:
  urls:
    - "https://example.com/article-about-ai-investing"
    - "https://example.com/clean-energy-thesis"
```

### Initialize Knowledge Base

**In the Streamlit app sidebar:**
1. Click "Initialize RAG Database"
2. Wait for ingestion to complete
3. Status will show: "✓ RAG DB Connected"

**Or via command line:**
```python
from rag_engine import initialize_rag_db, batch_ingest_sources
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)

db_client = initialize_rag_db()
batch_ingest_sources(config, db_client)
```

---

## Troubleshooting

### Error: "ANTHROPIC_API_KEY environment variable not set"

**Solution:**
1. Check `.env` file exists
2. Verify API key is correct
3. Restart the application
4. If using IDE, check it loads `.env` files

### Error: "No module named 'streamlit'"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### OCR Extraction Returns Empty Results

**Possible causes:**
1. Image quality too low
2. Text is handwritten
3. Screenshot doesn't contain expected data

**Solutions:**
- Use higher resolution screenshot
- Ensure text is clear and readable
- Try different portfolio view from brokerage
- Manually enter positions in editable table

### Market Data Fetch Fails

**Common causes:**
- Invalid ticker symbol
- Yahoo Finance API down
- Network connectivity issues

**Solutions:**
- Verify ticker symbols (e.g., "SPY" not "sp500")
- Check internet connection
- Try again later if API is down
- Use manual entry for problematic tickers

### ChromaDB Initialization Fails

**Solution:**
```bash
# Remove existing database
rm -rf chroma_db/

# Restart application
streamlit run app.py
```

### Application is Slow

**Performance tips:**
1. Close unused browser tabs
2. Process smaller portfolios first
3. Reduce number of themes in config
4. Use Claude Haiku model for faster responses:
   ```yaml
   ai_settings:
     model: "claude-3-haiku-20240307"
   ```

### API Rate Limits

If you hit Claude API rate limits:
1. Wait a few minutes
2. Reduce frequency of analysis runs
3. Upgrade to higher API tier
4. Use caching for repeated queries

---

## Next Steps

### Recommended Workflow

**First Time:**
1. Upload portfolio image
2. Verify OCR extraction
3. Enrich with market data
4. Review AI analysis
5. Explore tax harvesting opportunities

**Quarterly:**
1. Re-upload current portfolio
2. Generate quarterly review report
3. Review rebalancing recommendations
4. Execute trades if needed
5. Update knowledge base with new content

### Customization Ideas

1. **Adjust Themes:**
   - Add emerging sector themes
   - Remove themes you don't believe in
   - Change conviction levels

2. **Modify Allocations:**
   - Increase/decrease hub percentage
   - Adjust spoke percentages
   - Change bond allocation

3. **Add Your Research:**
   - Ingest your favorite YouTube channels
   - Add blog posts and articles
   - Include custom investment theses

4. **Tune Tax Harvesting:**
   - Change minimum loss threshold
   - Adjust tax rate assumption
   - Customize replacement pairs

---

## Getting Help

**Documentation:**
- Main README: [README.md](README.md)
- Configuration: Review `config.yaml` comments

**Common Resources:**
- Anthropic Claude: [docs.anthropic.com](https://docs.anthropic.com/)
- Streamlit: [docs.streamlit.io](https://docs.streamlit.io/)
- yfinance: [github.com/ranaroussi/yfinance](https://github.com/ranaroussi/yfinance)

**Found a bug?**
- Check GitHub issues
- Create new issue with:
  - Steps to reproduce
  - Error messages
  - Your environment (OS, Python version)

---

## Security Best Practices

1. **Never commit `.env` file** to git (already in `.gitignore`)
2. **Rotate API keys** periodically
3. **Don't share screenshots** containing account numbers
4. **Review extracted data** before analysis
5. **Keep dependencies updated:** `pip install --upgrade -r requirements.txt`

---

**You're ready to crush your portfolio! 🚀📊**
