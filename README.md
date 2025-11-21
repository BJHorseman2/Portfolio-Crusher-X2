# Portfolio Crusher X2

AI-powered portfolio analysis tool with tax loss harvesting and rebalancing recommendations using a hub-and-spoke investment strategy.

## Features

- 📸 **Image Upload & OCR**: Upload portfolio screenshots and extract positions automatically
- 🎯 **Hub & Spoke Strategy**: S&P 500 core (60-70%) with thematic satellite positions
- 🤖 **AI-Powered Analysis**: Claude-powered recommendations for each position
- 💰 **Tax Loss Harvesting**: Identify opportunities with wash sale rule compliance
- 🔄 **Quarterly Rebalancing**: Smart rebalancing suggestions aligned with your strategy
- 📊 **Theme Analysis**: Evaluate thematic spoke strength with market context

## Investment Philosophy

**Hub (Core)**: 60-70% in S&P 500 ETFs (SPY, VOO, or IVV)

**Spokes (Satellites)**: 30-40% in thematic ETFs:
- Artificial Intelligence
- Clean Energy
- Genomics & Biotech
- FinTech
- Cloud Computing

**Bonds**: 20-40% based on risk tolerance

## Documentation

📚 **[Complete Setup Guide](SETUP_GUIDE.md)** - Detailed installation and configuration instructions
💡 **[Usage Examples](USAGE_EXAMPLES.md)** - Real-world scenarios and workflows
⚙️ **Configuration**: Edit `config.yaml` for your investment strategy

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/BJHorseman2/Portfolio-Crusher-X2.git
cd Portfolio-Crusher-X2
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.template .env
# Edit .env and add your ANTHROPIC_API_KEY
```

5. **Run the application**
```bash
streamlit run app.py
```

## Configuration

Edit `config.yaml` to customize:
- Target allocations for hub and spokes
- Theme conviction levels
- Tax loss harvesting thresholds
- Rebalancing frequency

## Usage

1. **Upload Portfolio Image**: Take a screenshot of your portfolio and upload it
2. **Review Extraction**: Verify OCR extracted positions correctly
3. **Get Analysis**: View AI-powered recommendations for each position
4. **Tax Harvesting**: See tax loss harvesting opportunities
5. **Rebalancing**: Get quarterly rebalancing suggestions

## Security

- ✅ API keys stored in `.env` (never committed to git)
- ✅ No personal data stored by default
- ✅ Image uploads not retained (configurable)
- ✅ Local processing only

## Tech Stack

- **Frontend**: Streamlit
- **AI/ML**: Anthropic Claude (Vision + Analysis)
- **Market Data**: Yahoo Finance (free)
- **Vector DB**: ChromaDB (embedded)
- **Data Processing**: Pandas, NumPy

## Project Structure

```
Portfolio-Crusher-X2/
├── app.py                      # Main Streamlit application
├── ocr_processor.py            # Claude Vision for image → positions
├── portfolio_classifier.py     # Hub/spoke/bonds classification
├── theme_analyzer.py           # Thematic spoke evaluation
├── tax_loss_harvester.py       # Tax loss harvesting engine
├── rebalancer.py               # Portfolio rebalancing logic
├── ai_analyzer.py              # AI recommendation engine
├── data_fetcher.py             # Market data integration
├── rag_engine.py               # RAG for Economist/YouTube context
├── config.yaml                 # Investment strategy configuration
└── requirements.txt            # Python dependencies
```

## Cost Estimates

- **Anthropic API**: ~$20-50/month (based on usage)
- **Market Data**: Free (Yahoo Finance)
- **Hosting**: Free (run locally) or $5/month (Streamlit Cloud)

**Total**: ~$20-55/month

## Contributing

This is a personal portfolio management tool. Feel free to fork and customize for your own use.

## Disclaimer

This tool provides informational analysis only and does not constitute financial advice. Always consult with a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built with inspiration from:
- [danguetta/rebalancer](https://github.com/danguetta/rebalancer) - Tax loss harvesting algorithms
- [shiv-rna/Investment-Portfolio-AI-Agent](https://github.com/shiv-rna/Investment-Portfolio-AI-Agent) - ReAct AI framework
- [williamgilpin/portbalance](https://github.com/williamgilpin/portbalance) - Portfolio rebalancing

---

**Version**: 1.0.0
**Status**: Production Ready ✅

Made with ❤️ for smarter portfolio management
