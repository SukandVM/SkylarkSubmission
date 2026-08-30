# Skylark Drones — Business Intelligence Agent

AI-powered conversational agent that answers founder-level business intelligence queries by integrating with monday.com boards containing work orders and deals data.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                     │
│  (Chat UI + Data Explorer + Pipeline + Revenue + Ops)    │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│                     FastAPI Backend                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  /api/   │  │  /api/   │  │  /api/   │              │
│  │  chat    │  │  boards  │  │  health  │              │
│  └────┬─────┘  └────┬─────┘  └──────────┘              │
│       │              │                                   │
│  ┌────▼──────────────▼─────────────────────────────┐   │
│  │              Services Layer                       │   │
│  │                                                   │   │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────────┐  │   │
│  │  │ AI Agent│  │BI Engine │  │Data Processor │  │   │
│  │  │(Gemini) │  │(Pandas)  │  │(Normalizer)   │  │   │
│  │  └────┬────┘  └────┬─────┘  └──────┬───────┘  │   │
│  │       │             │               │            │   │
│  │  ┌────▼─────────────▼───────────────▼───────┐  │   │
│  │  │         Monday.com Client (GraphQL)       │  │   │
│  │  │         OR Local CSV Fallback             │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI |
| AI Agent | Google Gemini 2.5 Flash (with rule-based fallback) |
| Data Processing | pandas, custom normalizer |
| Monday.com | GraphQL API (read-only) |
| Frontend | Streamlit |
| Deployment | Docker on Render |

## Project Structure

```
skylark-bi-agent/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Environment settings
│   ├── schemas.py              # Pydantic models
│   ├── routers/
│   │   ├── chat.py             # POST /api/chat
│   │   ├── boards.py           # GET /api/boards
│   │   └── health.py           # GET /api/health
│   ├── services/
│   │   ├── monday_client.py    # Monday.com GraphQL client
│   │   ├── data_processor.py   # Messy data normalizer
│   │   ├── ai_agent.py         # Gemini AI agent
│   │   ├── bi_engine.py        # Pre-built BI computations
│   │   └── cache_service.py    # In-memory TTL cache
│   └── requirements.txt
├── app.py                      # Streamlit frontend
├── data/
│   ├── work_orders.csv         # Work order data
│   └── deals.csv               # Deals pipeline data
├── scripts/
│   └── import_to_monday.py     # Import CSVs into Monday.com
├── Dockerfile
├── render.yaml
├── DECISION_LOG.md
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.10+
- Monday.com API key (optional — app works with local CSVs)
- Google Gemini API key (optional — falls back to rule-based responses)

### Local Development

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd SkylarkSubmission
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

5. Or run the FastAPI backend:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

### Monday.com Configuration

1. Get your Monday.com API key from Admin → Connections → API
2. Set `MONDAY_API_KEY` in your `.env` file
3. Run the import script to create boards:
   ```bash
   python scripts/import_to_monday.py
   ```
4. The script will create two boards and import all data

### Docker Deployment

```bash
docker build -t skylark-bi-agent .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key skylark-bi-agent
```

### Render Deployment

1. Push to GitHub
2. Connect to Render
3. Set environment variables in Render dashboard
4. Deploy — `render.yaml` handles the rest

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/chat` | Ask a business question |
| GET | `/api/boards` | List available boards |
| GET | `/api/boards/{id}/items` | Get board items |
| GET | `/api/data-quality` | Data quality report |
| GET | `/api/health` | Health check |

## Sample Queries

- "How's our pipeline looking for energy sector this quarter?"
- "What's our total revenue this year?"
- "Show me the top 5 deals by value"
- "Which sectors are we strongest in?"
- "Any data quality issues I should know about?"
- "What's our deal conversion funnel?"
- "How many projects are overdue?"
- "What's the collection ratio on billed amounts?"
