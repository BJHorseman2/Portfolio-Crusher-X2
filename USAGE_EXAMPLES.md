# Portfolio Crusher X2 - Usage Examples

Real-world examples and workflows for using Portfolio Crusher X2.

## Table of Contents

1. [Basic Portfolio Analysis](#basic-portfolio-analysis)
2. [Tax Loss Harvesting Scenario](#tax-loss-harvesting-scenario)
3. [Quarterly Rebalancing](#quarterly-rebalancing)
4. [Adding New Cash](#adding-new-cash)
5. [Theme Rotation](#theme-rotation)
6. [Custom Investment Philosophy](#custom-investment-philosophy)

---

## Basic Portfolio Analysis

### Scenario: First-Time User

**Your Portfolio:**
- $50,000 in VOO (S&P 500)
- $8,000 in ARKK (AI/Innovation)
- $5,000 in ICLN (Clean Energy)
- $7,000 in ARKG (Genomics)
- $30,000 in BND (Bonds)

**Total: $100,000**

### Step-by-Step

#### 1. Upload Portfolio Screenshot

Take screenshot from your brokerage showing these positions and upload to Tab 1.

#### 2. OCR Extraction Results

```
Ticker  | Shares | Current Value
--------|--------|---------------
VOO     | 100    | $50,000
ARKK    | 160    | $8,000
ICLN    | 250    | $5,000
ARKG    | 140    | $7,000
BND     | 400    | $30,000
```

#### 3. Portfolio Classification (Tab 2)

**Hub (S&P 500): $50,000 (50% of total)**
- VOO: $50,000

**Spokes (Themes): $20,000 (20% of total)**
- AI Theme: $8,000 (ARKK)
- Clean Energy: $5,000 (ICLN)
- Genomics: $7,000 (ARKG)

**Bonds: $30,000 (30% of total)**
- BND: $30,000

#### 4. Analysis Results

**Overall Health: GOOD**

**Hub Analysis:**
- Status: ✓ Balanced
- Target: 65% of equity (60-70% range)
- Current: 71% of equity ($50k / $70k equity)
- Recommendation: Slightly overweight, consider adding to spokes

**Spokes Analysis:**
- AI Theme (ARKK): ⚠️ Underperforming, high volatility
  - Recommendation: REDUCE or rotate to QTEC
  - Conviction: Medium → Low

- Clean Energy (ICLN): ✓ Strong thesis
  - Recommendation: HOLD
  - Consider adding if conviction remains

- Genomics (ARKG): ⚠️ Theme has cooled
  - Recommendation: REDUCE to 5% or less

**Bonds:**
- Status: ✓ Well-positioned at 30%

### Expected Actions

1. Reduce ARKG from $7,000 to $3,500
2. Rotate ARKK to QTEC if loss harvesting available
3. Add $3,500 to hub (VOO) to maintain balance

---

## Tax Loss Harvesting Scenario

### Scenario: Year-End Tax Planning

**Your Situation:**
- Purchased ARKK at $80/share in January
- Current price: $50/share
- 100 shares = $3,000 loss
- Looking to harvest losses before Dec 31

### Step 1: Navigate to Tax Harvesting Tab

Click "Generate Harvest Plan"

### Step 2: Review Opportunities

**Harvestable Positions Found:**

```
Position: ARKK
Purchase Date: 2024-01-15
Cost Basis: $80/share × 100 shares = $8,000
Current Value: $50/share × 100 shares = $5,000
Unrealized Loss: -$3,000 ✓ Harvestable

Wash Sale Check: ✓ Safe (purchased >30 days ago)
Replacement Security: QTEC (similar AI/tech exposure)
```

### Step 3: Execute Harvest

**Recommended Transaction:**
1. Sell: 100 shares ARKK @ $50 = $5,000
2. Buy: ~62 shares QTEC @ $80 = $5,000
3. Tax Benefit: $3,000 × 25% = $750 (assuming 25% tax rate)

**Important:**
- Don't buy ARKK again for 30 days (wash sale rule)
- QTEC provides similar AI/tech exposure
- Harvest loss to offset capital gains or income

### Step 4: Wait Period

**Calendar:**
- Dec 15: Sell ARKK, Buy QTEC
- Jan 15 (30 days later): Can buy ARKK again if desired

**During Wait:**
- Hold QTEC to maintain market exposure
- Monitor both ARKK and QTEC performance
- Decide if QTEC is better long-term hold

---

## Quarterly Rebalancing

### Scenario: Q4 Portfolio Review

**Current Allocation:**
- Hub: 72% of equity (target: 65%)
- Spokes: 28% of equity (target: 35%)
- Bonds: 30% of portfolio (target: 30%)

**Drift Detected: Hub overweight, Spokes underweight**

### Step 1: Navigate to Rebalancing Tab

View current vs target allocation chart.

### Step 2: Generate Rebalancing Trades

Click "Generate Rebalancing Trades" (no new cash)

### Step 3: Review Recommendations

**Trades to Execute:**

```
SELL (Reduce Hub):
- Sell $4,900 of VOO
  Rationale: Reduce hub from 72% to 65% of equity

BUY (Increase Spokes):
- Buy $2,000 of ICLN (Clean Energy)
  Rationale: High conviction theme, underweight

- Buy $1,500 of WCLD (Cloud Computing)
  Rationale: Strong theme, add new spoke

- Buy $1,400 of VOO
  Rationale: Rounding / maintain exposure
```

**Net Result:**
- Sold VOO: -$4,900
- Bought back: +$1,400
- Net VOO reduction: -$3,500
- Added to spokes: +$3,500
- New hub allocation: 65% ✓
- New spokes allocation: 35% ✓

### Step 4: Execute Trades

Use your brokerage to execute these trades within a few days.

---

## Adding New Cash

### Scenario: Bonus or Regular Contribution

**Situation:**
- Received $10,000 bonus
- Want to invest following hub-and-spoke strategy
- Current portfolio: $100,000

### Step 1: Enter New Cash

In Rebalancing Tab, enter: `10000`

### Step 2: Generate Allocation Plan

Click "Generate Rebalancing Trades"

### Step 3: Review Suggested Allocation

**Recommended Deployment:**

```
Hub (65% of equity → $6,500):
- Buy $6,500 of VOO
  Rationale: Maintain core S&P 500 position

Spokes (35% of equity → $3,500):
- Buy $1,200 of QTEC (AI)
  Rationale: High conviction theme

- Buy $1,000 of ICLN (Clean Energy)
  Rationale: Long-term tailwinds

- Buy $700 of WCLD (Cloud)
  Rationale: Structural growth theme

- Buy $600 of ARKG (Genomics)
  Rationale: Increase underweight theme

Bonds (Consider separately):
- Could allocate $3,000 to BND to maintain 30%
- Or keep in equity if risk tolerance allows
```

### Step 4: Customize if Desired

**Option A: More Conservative**
- $6,000 to hub
- $1,000 to spokes
- $3,000 to bonds

**Option B: More Aggressive**
- $7,000 to hub
- $3,000 to spokes
- $0 to bonds (stay equity-heavy)

---

## Theme Rotation

### Scenario: Rotating Out of Weak Theme

**Situation:**
- Genomics theme (ARKG) has underperformed
- Conviction dropped from High → Low
- Want to rotate into stronger theme

### Current Position
- ARKG: $7,000 (10% of equity)
- Unrealized: -$500 (down 7%)

### Step 1: Tax Harvest First

Check Tax Harvesting tab:
```
ARKG: -$500 loss ✓ Harvestable
Replacement: XBI (similar biotech exposure)
Action: Sell ARKG, Buy XBI
```

**Execute:**
- Sell ARKG: $7,000
- Buy XBI: $7,000
- Tax benefit: $125 (if 25% rate)

### Step 2: Wait 31 Days

During wait period, XBI maintains biotech exposure.

### Step 3: Rotate Theme (After 31 Days)

**Decision:** Exit genomics entirely, rotate to cybersecurity

**Execute:**
- Sell XBI: $7,000 (approx)
- Buy HACK (cybersecurity ETF): $7,000

**Update config.yaml:**
```yaml
spokes:
  themes:
    # Remove or lower conviction:
    # - name: "Genomics"
    #   conviction: "low"
    #   target_pct: 0

    # Add new theme:
    - name: "Cybersecurity"
      category: "cybersecurity"
      conviction: "high"
      target_pct: 10
      etfs:
        - "HACK"
        - "CIBR"
        - "BUG"
```

### Result

**Before:**
- Genomics: $7,000 (weak theme)

**After:**
- Cybersecurity: $7,000 (strong theme)
- Tax benefit: $125
- Updated conviction alignment

---

## Custom Investment Philosophy

### Scenario: Dividend-Focused Hub-and-Spoke

**Your Philosophy:**
- Prefer dividend income
- Still want thematic upside
- More conservative approach

### Step 1: Modify config.yaml

```yaml
equity_allocation:
  hub:
    target_pct: 70  # Higher hub allocation
    allowed_etfs:
      - ticker: "SCHD"  # High dividend ETF
        name: "Schwab US Dividend Equity ETF"
        provider: "Schwab"
      - ticker: "VYM"   # Vanguard High Dividend
        name: "Vanguard High Dividend Yield ETF"
        provider: "Vanguard"

  spokes:
    total_target_pct: 30  # Lower spoke allocation
    themes:
      - name: "Dividend Growth"
        category: "dividend_growth"
        conviction: "high"
        target_pct: 10
        etfs:
          - "VIG"   # Dividend Appreciation
          - "DGRW"  # Dividend Growth

      - name: "REITs"
        category: "reits"
        conviction: "medium"
        target_pct: 10
        etfs:
          - "VNQ"   # Real Estate
          - "REET"  # iShares Global REIT

      - name: "Utilities"
        category: "utilities"
        conviction: "medium"
        target_pct: 10
        etfs:
          - "VPU"   # Utilities
          - "XLU"   # Utilities Select

bonds:
  target_pct: 40  # Higher bond allocation
```

### Step 2: Add Dividend-Focused Knowledge

**YouTube sources to add:**
- Dividend investing strategy videos
- REIT analysis channels
- Income investing philosophy

### Step 3: Portfolio Construction

**Target Portfolio ($100k):**

**Hub (42%): $42,000**
- SCHD: $42,000 (high dividend S&P alternative)

**Spokes (18%): $18,000**
- VIG (Dividend Growth): $6,000
- VNQ (REITs): $6,000
- VPU (Utilities): $6,000

**Bonds (40%): $40,000**
- BND: $40,000

**Expected Annual Dividend Yield: ~3.5-4%**

---

## Pro Tips

### 1. Regular Review Schedule

**Monthly:**
- Check market data is up-to-date
- Review any new positions

**Quarterly:**
- Full portfolio analysis
- Tax loss harvesting review
- Rebalancing if >5% drift
- Update conviction levels

**Annually:**
- Comprehensive review
- Update investment themes
- Refresh knowledge base
- Review tax strategy

### 2. Maximizing Tax Efficiency

**Harvest Losses Strategically:**
- Q4: Harvest to offset current year gains
- Any time: If loss >10% and conviction changed
- Pair with sales: Offset gains from rebalancing

**Replacement Pairs:**
- Always wait 31 days (not just 30)
- Track calendar carefully
- Use similar but not identical ETFs

### 3. Theme Research

**Before Adding a Theme:**
1. Research ETF holdings overlap
2. Check expense ratios
3. Review historical performance
4. Understand thesis
5. Set realistic conviction level

**Red Flags:**
- Too much overlap with hub
- Very high expense ratio (>0.75%)
- Extreme concentration (<15 holdings)
- Purely momentum-driven

### 4. Using RAG Effectively

**Best Sources:**
- Long-form investment theses
- Sector deep-dives
- Macro trend analysis
- Your own research notes

**Less Useful:**
- Daily market commentary
- Short news articles
- Purely technical analysis
- Promotional content

---

## Common Questions

**Q: How often should I rebalance?**
A: Quarterly is recommended, or when allocation drifts >5% from target.

**Q: Should I always follow AI recommendations?**
A: No - use as input, but make your own decisions based on your situation.

**Q: Can I use this for retirement accounts?**
A: Yes! Tax harvesting is especially useful in taxable accounts, but analysis works for all account types.

**Q: What if I don't have cost basis data?**
A: Tax harvesting won't work, but analysis and rebalancing still valuable.

**Q: How do I handle fractional shares?**
A: Round to whole shares for trading, or use brokerages that support fractional shares.

---

**Happy investing! 📈**
