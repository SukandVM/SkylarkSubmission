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

## Data Preprocessing Steps

### Raw Data Issues Found

#### Work Orders (176 rows × 38 columns)

| Issue | Severity | Detail | Resolution |
|---|---|---|---|
| Extra blank header row | High | Row 0 is all NaN; pandas reads it as column headers creating `Unnamed: 0`, `Unnamed: 1`, etc. | Exported with `header=1` to skip blank row |
| 100% null columns (4) | High | `Expected Billing Month`, `Actual Collection Month`, `Collection Status`, `Collection Date` — all 176 rows null | Dropped from DataFrame after loading |
| Billing Status typo | Medium | `"BIlled"` (capital I) is a valid status label in the Monday.com board | Normalized to `"Billed"` in `data_processor.py` via `BILLING_STATUS_CANONICAL` mapping |
| Mixed quantity format | Low | `Quantity by Ops` contains `"5360 HA"` (unit suffix) alongside pure numbers like `"4"` | Parsed with regex to extract numeric value: `"5360 HA"` → `5360.0` |
| 84% null Billing Status | Medium | Only 28/176 rows have a billing status value | Agent flags this in data quality notes |
| 94% null AR Priority | Medium | Almost entirely empty | Agent flags this in data quality notes |

#### Deals (346 rows × 12 columns)

| Issue | Severity | Detail | Resolution |
|---|---|---|---|
| Header-as-data rows | High | `"Close Date (A)"`, `"Deal Stage"`, `"Sector/service"`, `"Product deal"`, `"Closure Probability"`, `"Deal Status"` appear as data values in their respective columns | Filtered out: `df = df[df[col] != col]` for each affected column |
| 92% null Close Date | High | Only 26 real dates out of 346 rows | Agent notes this; Tentative Close Date used as fallback |
| 75% null Closure Probability | High | 258/346 rows missing | Agent flags in every response |
| 52% null Deal Value | High | 181/346 rows missing | Agent flags; `top_deals` filters to non-null values |
| 49% null Product deal | Medium | 170/346 rows missing | Not used in BI computations |
| 52 duplicate rows | Medium | Same (Deal Name, Client Code, Deal Status) — some are legitimately different stages, some are true duplicates | Deduplicated by (Deal Name, Client Code), keeping row with most non-null values |
| Monday.com status label | Low | Board has `"BIlled"` as a valid status label (typo baked into board config) | Cannot change via API; `data_processor.py` normalizes when reading CSV |

### Preprocessing Applied

1. **CSV Export Fix**: Work Orders exported with `header=1` to skip blank row 0
2. **Header Artifact Removal**: Deals CSV filtered to remove rows where column value equals its own header text
3. **Null Column Drop**: 4 all-null columns removed from Work Orders (`expected_billing_month`, `actual_collection_month`, `collection_status`, `collection_date`)
4. **Typo Normalization**: `"BIlled"` → `"Billed"` via `BILLING_STATUS_CANONICAL` mapping in data processor
5. **Quantity Parsing**: Non-numeric suffixes stripped from `quantity_by_ops` (e.g., `"5360 HA"` → `5360.0`)
6. **Deal Deduplication**: Deals deduplicated by (Deal Name, Client Code) keeping the row with most non-null values
7. **Monday.com Cleanup Script**: `scripts/cleanup_monday.py` — discovers boards, fetches all items, identifies and deletes header-artifact items, attempts to fix typos
8. **Data Quality Report Upgrade**: Threshold lowered from >80% to >=70% for "data gap" warnings; added "critical" (>=90%) and "partial" (>=50%) severity levels

### How Agent Communicates Data Quality

Every response from the AI agent includes a `data_quality_notes` array with messages like:
- "Work Orders data has ~34% overall missing values"
- "Deal values are missing for ~52% of deals"
- "Closure probability is missing for ~75% of deals"

The Streamlit **Data Quality** dashboard shows per-column null rates with color-coded severity. The agent also proactively mentions data gaps when relevant to the query (e.g., "Note: 3 deals have missing close dates, estimates used").

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
