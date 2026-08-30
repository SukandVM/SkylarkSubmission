import json
import logging
from typing import Optional
from backend.config import settings
from backend.services.bi_engine import bi_engine
from backend.services.data_processor import processor

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a business intelligence agent for Skylark Drones, a drone services company.

You have access to two datasets:
1. WORK ORDERS - Project execution data with columns: deal_name, customer, serial_number, nature_of_work, execution_status, sector, type_of_work, amount_excl_gst, amount_incl_gst, billed_value_excl_gst, billed_value_incl_gst, collected_amount, amount_receivable, billing_status, wo_status, probable_start_date, probable_end_date, date_of_po_loi, document_type, bd_personnel, and more.

2. DEALS - Sales pipeline data with columns: Deal Name, Owner code, Client Code, Deal Status (Open/On Hold/Dead/Won), Deal Stage (Lead Generated through Won/Lost), Closure Probability (High/Medium/Low), Masked Deal value, Tentative Close Date, Created Date, Sector/service, Product deal.

SECTORS: Mining, Powerline, Renewables, Railways, Construction, Tender, DSP, Security & Surveillance, Aviation, Manufacturing, Others

DEAL STAGES (in order): Lead Generated → Sales Qualified → Demo Done → Feasibility → Proposal Sent → Negotiations → Won → WO Received → POC → Invoice Sent → Accrued. Also: Lost, On Hold, Not Relevant.

INSTRUCTIONS:
- Answer the user's business question using the provided data
- Always cite specific numbers and data points
- When data is missing or incomplete, acknowledge it clearly
- Provide insights and context, not just raw numbers
- If the query is ambiguous, ask a clarifying question
- Format financial values in Indian Rupees (₹) with appropriate abbreviations (K, L, Cr)
- Compare across time periods, sectors, or stages when relevant
- Highlight trends, risks, and opportunities

You have access to these pre-computed functions. Use them when relevant:
- revenue_summary(sector, year): Contract values, billing, collection data
- pipeline_health(sector): Deal pipeline by stage, open/won/dead counts
- sector_performance(sector): Breakdown by industry sector
- operational_metrics(): Project execution status, billing status
- top_deals(n): Top N deals by value
- deal_conversion_funnel(): Deal flow through pipeline stages
- quarterly_comparison(): Quarter-over-quarter trends
"""

CLARIFYING_QUESTIONS = {
    "pipeline": "Would you like me to focus on a specific sector or the overall pipeline?",
    "revenue": "Should I look at total revenue, or filter by a specific sector or time period?",
    "performance": "Are you interested in sector performance, team performance, or overall operational metrics?",
    "deals": "Would you like to see all deals, or filter by status (Open, Won, Lost)?",
    "projects": "Should I look at all projects or a specific sector?",
}


class AIAgent:
    def __init__(self):
        self.model = None
        self._init_gemini()

    def _init_gemini(self):
        try:
            import google.generativeai as genai
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(
                    model_name=settings.AI_MODEL,
                    system_instruction=SYSTEM_PROMPT,
                )
                logger.info("Gemini model initialized: %s", settings.AI_MODEL)
            else:
                logger.warning("No GEMINI_API_KEY set, using rule-based fallback")
        except ImportError:
            logger.warning("google-generativeai not installed, using rule-based fallback")
        except Exception as e:
            logger.error("Failed to init Gemini: %s", e)

    def _build_context(self, query: str) -> str:
        summary = bi_engine.get_summary_for_agent()
        context_parts = []
        for key, data in summary.items():
            context_parts.append(f"=== {key.upper()} ===")
            context_parts.append(json.dumps(data, indent=2, default=str))
        return "\n".join(context_parts)

    def _detect_clarifying_needed(self, query: str) -> Optional[str]:
        q = query.lower()
        if any(w in q for w in ["how", "what", "show", "tell", "give"]):
            if not any(w in q for w in ["sector", "mining", "powerline", "renewable", "railway",
                                          "construction", "energy", "aviation", "manufacturing",
                                          "deal", "project", "revenue", "pipeline", "billing",
                                          "collection", "status", "quarter", "month", "year",
                                          "top", "best", "worst", "total", "count", "how many",
                                          "how much", "which"]):
                return CLARIFYING_QUESTIONS.get("performance")
        return None

    async def process_query(self, query: str) -> dict:
        clarifying = self._detect_clarifying_needed(query)
        context = self._build_context(query)
        if self.model:
            try:
                prompt = f"Context data:\n{context}\n\nUser query: {query}"
                response = self.model.generate_content(prompt)
                answer = response.text
                return {
                    "answer": answer,
                    "data_quality_notes": self._get_data_notes(),
                    "sources": ["Work Orders Board", "Deals Board"],
                    "clarifying_question": clarifying,
                }
            except Exception as e:
                logger.error("Gemini error: %s", e)
                return self._rule_based_response(query, context, clarifying)
        return self._rule_based_response(query, context, clarifying)

    def _rule_based_response(self, query: str, context: str, clarifying: Optional[str]) -> dict:
        q = query.lower()
        parts = []
        if "pipeline" in q or "deal" in q:
            pipeline = bi_engine.pipeline_health()
            parts.append(self._format_pipeline(pipeline, q))
        if "revenue" in q or "income" in q or "billing" in q or "collection" in q:
            revenue = bi_engine.revenue_summary()
            parts.append(self._format_revenue(revenue, q))
        if "sector" in q or "mining" in q or "powerline" in q or "renewable" in q:
            sector_q = None
            for s in ["mining", "powerline", "renewable", "railway", "construction", "aviation", "manufacturing"]:
                if s in q:
                    sector_q = s.title()
                    break
            sector = bi_engine.sector_performance(sector_q)
            parts.append(self._format_sector(sector, sector_q))
        if "project" in q or "operation" in q or "status" in q:
            ops = bi_engine.operational_metrics()
            parts.append(self._format_operations(ops))
        if "top" in q and "deal" in q:
            top = bi_engine.top_deals(5)
            parts.append(self._format_top_deals(top))
        if "funnel" in q or "conversion" in q:
            funnel = bi_engine.deal_conversion_funnel()
            parts.append(self._format_funnel(funnel))
        if "quarter" in q:
            quarterly = bi_engine.quarterly_comparison()
            parts.append(self._format_quarterly(quarterly))
        if not parts:
            summary = bi_engine.get_summary_for_agent()
            parts.append("Here's an overview of your business:\n")
            parts.append(self._format_revenue(summary["revenue"], q))
            parts.append(self._format_pipeline(summary["pipeline"], q))
            parts.append(self._format_operations(summary["operations"]))
        answer = "\n\n".join(parts)
        if clarifying:
            answer = f"{clarifying}\n\n{answer}"
        return {
            "answer": answer,
            "data_quality_notes": self._get_data_notes(),
            "sources": ["Work Orders Board", "Deals Board"],
            "clarifying_question": clarifying,
        }

    def _format_currency(self, value: float) -> str:
        if value >= 1e7:
            return f"₹{value/1e7:.2f} Cr"
        elif value >= 1e5:
            return f"₹{value/1e5:.2f} L"
        elif value >= 1e3:
            return f"₹{value/1e3:.1f}K"
        return f"₹{value:.0f}"

    def _format_pipeline(self, data: dict, query: str) -> str:
        if "error" in data:
            return data["error"]
        lines = ["**Pipeline Health:**\n"]
        lines.append(f"- Total pipeline value: **{self._format_currency(data['total_pipeline_value'])}**")
        lines.append(f"- Open deals: **{data['open_deals_count']}**")
        lines.append(f"- Won deals: **{data['won_deals_count']}** ({self._format_currency(data['won_value'])})")
        lines.append(f"- Dead deals: **{data['dead_deals_count']}**")
        lines.append(f"- On hold: **{data['on_hold_count']}**")
        if data.get("by_stage"):
            lines.append("\n**By Stage:**")
            for stage, info in sorted(data["by_stage"].items(), key=lambda x: x[1]["count"], reverse=True):
                lines.append(f"  - {stage}: {info['count']} deals ({self._format_currency(info['value'])})")
        return "\n".join(lines)

    def _format_revenue(self, data: dict, query: str) -> str:
        if "error" in data:
            return data["error"]
        lines = ["**Revenue Summary:**\n"]
        lines.append(f"- Total contract value: **{self._format_currency(data['total_contract_value'])}**")
        lines.append(f"- Total billed: **{self._format_currency(data['total_billed'])}** ({data['billing_ratio']}%)")
        lines.append(f"- Total collected: **{self._format_currency(data['total_collected'])}** ({data['collection_ratio']}%)")
        lines.append(f"- Amount receivable: **{self._format_currency(data['total_receivable'])}**")
        lines.append(f"- Total projects: **{data['project_count']}**")
        return "\n".join(lines)

    def _format_sector(self, data: dict, sector: str = None) -> str:
        if "error" in data:
            return data["error"]
        lines = [f"**Sector Performance{' — ' + sector if sector else ''}:**\n"]
        if "deals_by_sector" in data:
            lines.append("Deals by sector:")
            for s in data["deals_by_sector"]:
                name = s.get("sector_clean") or "Unknown"
                lines.append(f"  - {name}: {s['deal_count']} deals, {self._format_currency(s['total_value'])}")
        if "work_orders_by_sector" in data:
            lines.append("\nWork orders by sector:")
            for s in data["work_orders_by_sector"]:
                name = s.get("sector") or "Unknown"
                lines.append(f"  - {name}: {s['project_count']} projects, {self._format_currency(s['total_value'])}")
        return "\n".join(lines)

    def _format_operations(self, data: dict) -> str:
        if "error" in data:
            return data["error"]
        lines = ["**Operational Metrics:**\n"]
        lines.append(f"- Total projects: **{data['total_projects']}**")
        lines.append(f"- Overdue projects: **{data['overdue_projects']}**")
        if data.get("by_status"):
            lines.append("\nBy execution status:")
            for status, count in data["by_status"].items():
                lines.append(f"  - {status}: {count}")
        if data.get("by_billing_status"):
            lines.append("\nBy billing status:")
            for status, count in data["by_billing_status"].items():
                lines.append(f"  - {status}: {count}")
        return "\n".join(lines)

    def _format_top_deals(self, data: dict) -> str:
        if "error" in data:
            return data["error"]
        lines = ["**Top Deals by Value:**\n"]
        for i, deal in enumerate(data["deals"], 1):
            lines.append(f"{i}. **{deal['name']}** — {self._format_currency(deal['value'])}")
            lines.append(f"   Stage: {deal['stage']} | Sector: {deal['sector']} | Status: {deal['status']}")
        return "\n".join(lines)

    def _format_funnel(self, data: dict) -> str:
        if "error" in data:
            return data["error"]
        lines = ["**Deal Conversion Funnel:**\n"]
        for stage in data["funnel"]:
            bar = "█" * min(stage["count"], 30)
            lines.append(f"  {stage['stage']}: {bar} {stage['count']} ({self._format_currency(stage['value'])})")
        return "\n".join(lines)

    def _format_quarterly(self, data: dict) -> str:
        if "error" in data:
            return data["error"]
        if not data.get("data"):
            return "No quarterly data available."
        lines = ["**Quarterly Comparison:**\n"]
        for q in data["data"]:
            lines.append(f"  Q{q['quarter']} {q['year']}: {q['deal_count']} deals, {self._format_currency(q['total_value'])} (Won: {q['won_count']})")
        return "\n".join(lines)

    def _get_data_notes(self) -> list[str]:
        notes = []
        wo = processor.get_work_orders()
        deals = processor.get_deals()
        if not wo.empty:
            null_pct = wo.isnull().mean().mean() * 100
            if null_pct > 30:
                notes.append(f"Work Orders data has ~{null_pct:.0f}% overall missing values")
        if not deals.empty:
            deal_value_null = deals["deal_value"].isnull().mean() * 100
            if deal_value_null > 20:
                notes.append(f"Deal values are missing for ~{deal_value_null:.0f}% of deals")
            prob_null = deals["Closure Probability"].isnull().mean() * 100
            if prob_null > 20:
                notes.append(f"Closure probability is missing for ~{prob_null:.0f}% of deals")
        return notes


ai_agent = AIAgent()
