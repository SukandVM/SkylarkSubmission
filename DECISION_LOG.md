# Decision Log — Skylark Drones BI Agent

## Key Assumptions

### 1. Data Access
- **Assumption**: Monday.com API access may not be available during demo. Built a dual-mode system that reads from local CSV files by default, with Monday.com API as an optional enhancement.
- **Rationale**: The assignment requires the agent to query Monday.com dynamically, but API keys may not be provisioned in time. The local CSV fallback ensures the prototype works immediately.

### 2. LLM Choice — Google Gemini 2.5 Flash
- **Assumption**: Gemini's free tier is sufficient for the demo. Falls back to rule-based responses if API key is unavailable.
- **Rationale**: Fast inference, good at structured data reasoning, free tier available, and consistent with the Spritle OneAI Tool stack.

### 3. Frontend — Streamlit over React
- **Assumption**: A Streamlit app is sufficient for the 6-hour timeline. The assignment asks for a "conversational interface" not a production UI.
- **Rationale**: Streamlit provides chat UI, data tables, and charts in ~200 lines. React would take 3+ hours for equivalent functionality.

### 4. Messy Data Handling
- **Assumption**: The real-world messy data has specific patterns: inconsistent sector names, missing financial values, duplicate header rows in the source Excel, and varied date formats.
- **Rationale**: Built a dedicated `DataProcessor` class that normalizes sectors via a canonical mapping, parses currencies with regex, and handles null values gracefully. Every response includes data quality notes.

### 5. Architecture Mirroring Spritle OneAI
- **Assumption**: Following the Spritle OneAI Tool's structure (FastAPI routers, services layer, schemas) makes the codebase familiar and maintainable.
- **Rationale**: The assignment evaluates engineering quality. A clean, modular architecture demonstrates production thinking.

---

## Trade-offs

### 1. Local CSV vs Live Monday.com API
- **Chose**: Local CSV as primary, Monday.com API as optional enhancement
- **Why**: Ensures the demo works without API provisioning. The `monday_client.py` is fully implemented and ready to use once an API key is provided.
- **Alternative**: Require Monday.com API key upfront — risky if key isn't available.

### 2. Streamlit vs React Frontend
- **Chose**: Streamlit (single `app.py`, ~300 lines)
- **Why**: 10x faster to build. Provides chat, data explorer, charts, and data quality dashboard in one file.
- **Trade-off**: Less polished UI, no custom theming. Acceptable for a 6-hour prototype.

### 3. Gemini AI vs Rule-based Fallback
- **Chose**: Gemini with automatic rule-based fallback
- **Why**: If Gemini API key is set, get intelligent natural language responses. If not, the rule-based engine still provides structured answers using pre-built BI functions.
- **Trade-off**: Rule-based responses are less conversational but still accurate.

### 4. In-memory Cache vs Redis
- **Chose**: In-memory TTL cache
- **Why**: Single-server deployment, no external dependencies. Cache TTL of 5 minutes balances freshness with performance.
- **Trade-off**: Cache lost on restart. Acceptable for demo.

### 5. No Database
- **Chose**: No database — data loaded from CSV at startup
- **Why**: The assignment is read-only on Monday.com data. No need to persist user sessions or query history.
- **Trade-off**: No conversation history across page reloads.

---

## "Leadership Updates" Interpretation

The assignment mentions: *"The agent should help prepare data for leadership updates."*

**My interpretation**: Leadership updates typically involve:
1. **Pipeline health snapshot** — Open deals, conversion rates, deal stage distribution
2. **Revenue summary** — Total contract value, billed vs collected, receivables
3. **Sector breakdown** — Which industries are performing best
4. **Operational status** — Projects on track vs delayed, billing status
5. **Key deal highlights** — Top deals to watch, at-risk deals

**Implementation**: The BI agent can answer all of these queries. Additionally, the Streamlit sidebar has "Quick Queries" buttons that match common leadership update questions:
- "How's our pipeline looking?"
- "What's our total revenue?"
- "Show me top 5 deals"
- "Which sectors are we strongest in?"

A future enhancement could be a "Generate Leadership Report" button that compiles these into a PDF/DOCX summary.

---

## What I'd Do Differently With More Time

1. **Monday.com live sync** — Periodic background sync from Monday.com boards to keep data fresh
2. **Conversation history** — Persist chat history in SQLite for continuity across sessions
3. **PDF report generation** — One-click "Generate Leadership Report" that compiles insights into a formatted PDF
4. **React frontend** — Polished UI with Mermaid diagrams for pipeline visualization, TipTap for report editing
5. **Authentication** — JWT-based auth so multiple users can use the agent
6. **More BI functions** — YoY comparison, forecast projections, anomaly detection
7. **Streaming responses** — SSE-based streaming for real-time AI response rendering
8. **Automated data quality alerts** — Proactive notifications when data quality degrades
