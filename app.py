import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import json
import asyncio
from backend.services.data_processor import processor
from backend.services.bi_engine import bi_engine
from backend.services.ai_agent import ai_agent

st.set_page_config(
    page_title="Skylark Drones - BI Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color constants ──
C_PRIMARY = "#818CF8"
C_PRIMARY_LIGHT = "#A5B4FC"
C_SECONDARY = "#38BDF8"
C_SUCCESS = "#34D399"
C_WARNING = "#FBBF24"
C_DANGER = "#F87171"
C_BG = "#0F172A"
C_BG2 = "#1E293B"
C_CARD = "#1E293B"
C_TEXT = "#F1F5F9"
C_MUTED = "#94A3B8"
C_BORDER = "#334155"
C_SHADOW = "0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)"

# ──────────────────────────────────────────────
# GLOBAL CSS (only targets Streamlit internals)
# ──────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
.stApp {{ font-family: 'Inter', sans-serif; background: {C_BG} !important; color: {C_TEXT} !important; }}
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {C_BG2} 0%, {C_BG} 100%) !important; border-right: 1px solid {C_BORDER} !important; }}
.block-container {{ padding-top: 2rem !important; }}
[data-testid="stHeader"] {{ background: {C_BG} !important; }}
[data-testid="stToolbar"] {{ background: {C_BG} !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; background: {C_BG2}; border-radius: 10px; padding: 4px; }}
.stTabs [data-baseweb="tab"] {{ padding: 10px 20px; border-radius: 8px; font-weight: 500; font-size: 0.88rem; color: {C_MUTED}; background: transparent; }}
.stTabs [aria-selected="true"] {{ background: {C_PRIMARY} !important; color: white !important; }}
div[data-testid="stMetric"] {{ background: {C_CARD}; padding: 12px 16px; border-radius: 12px; box-shadow: {C_SHADOW}; border: 1px solid {C_BORDER}; }}
div[data-testid="stMetric"] label {{ font-size: 0.78rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em; color: {C_MUTED} !important; }}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; font-weight: 700 !important; color: {C_TEXT} !important; }}
.stChatInput textarea {{ background: {C_CARD} !important; color: {C_TEXT} !important; border-radius: 12px !important; }}
.stAlert {{ border-radius: 12px !important; }}
.stDataFrame {{ border-radius: 12px !important; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def format_currency(value):
    if pd.isna(value) or value is None:
        return "N/A"
    if value >= 1e7:
        return f"₹{value/1e7:.2f} Cr"
    elif value >= 1e5:
        return f"₹{value/1e5:.2f} L"
    elif value >= 1e3:
        return f"₹{value/1e3:.1f}K"
    return f"₹{value:.0f}"


def kpi_card(container, label, value, icon, color):
    color_map = {
        "indigo": C_PRIMARY,
        "blue":   C_SECONDARY,
        "green":  C_SUCCESS,
        "amber":  C_WARNING,
        "red":    C_DANGER,
    }
    border = color_map.get(color, C_PRIMARY)
    container.markdown(f'<div style="border-top:3px solid {border}; padding-top:4px;"></div>', unsafe_allow_html=True)
    container.metric(label=f"{icon}  {label}", value=str(value))


def progress_bar(label, pct, color=""):
    fills = {
        "":    f"background:linear-gradient(90deg, {C_PRIMARY}, {C_SECONDARY});",
        "green": f"background:linear-gradient(90deg, #059669, {C_SUCCESS});",
        "amber": f"background:linear-gradient(90deg, #D97706, {C_WARNING});",
        "red":   f"background:linear-gradient(90deg, #DC2626, {C_DANGER});",
    }
    fill_style = fills.get(color, fills[""])
    return f"""
<div style="margin:8px 0;">
  <div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-bottom:4px; color:{C_TEXT};">
    <span>{label}</span><span style="font-weight:600;">{pct}%</span>
  </div>
  <div style="height:10px; background:{C_BORDER}; border-radius:10px; overflow:hidden;">
    <div style="height:100%; border-radius:10px; width:{pct}%; {fill_style}"></div>
  </div>
</div>"""


def section_header(text):
    return f'<p style="font-size:1.1rem; font-weight:700; color:{C_TEXT}; padding-bottom:8px; margin-bottom:1rem; border-bottom:2px solid {C_PRIMARY}; display:inline-block;">{text}</p>'


def stat_badge(icon, label, count):
    return f'<div style="display:inline-flex; align-items:center; gap:6px; background:rgba(255,255,255,0.08); border-radius:20px; padding:5px 12px; font-size:0.78rem; font-weight:500; color:{C_MUTED}; margin:3px 0; border:1px solid rgba(255,255,255,0.06);">{icon} {label} <span style="color:{C_PRIMARY_LIGHT}; font-weight:700;">{count}</span></div>'


def badge_html(text, severity):
    styles = {
        "critical": f"background:rgba(248,113,113,0.15); color:#F87171; border:1px solid rgba(248,113,113,0.3);",
        "gap":      f"background:rgba(251,191,36,0.15); color:#FBBF24; border:1px solid rgba(251,191,36,0.3);",
        "partial":  f"background:rgba(251,191,36,0.1); color:#FCD34D; border:1px solid rgba(251,191,36,0.2);",
        "ok":       f"background:rgba(52,211,153,0.15); color:#34D399; border:1px solid rgba(52,211,153,0.3);",
    }
    s = styles.get(severity, styles["ok"])
    return f'<span style="display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; {s}">{text}</span>'


def source_pill(name):
    return f'<span style="display:inline-block; background:rgba(255,255,255,0.08); color:{C_MUTED}; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:500; margin:2px; border:1px solid rgba(255,255,255,0.06);">{name}</span>'


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
<div style="text-align:center; padding:1.5rem 0 1rem 0; background:linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #2563EB 100%); border-radius:16px; margin:0 0.5rem 1rem 0.5rem; color:white; box-shadow:0 4px 15px rgba(79,70,229,0.3);">
  <div style="font-size:2.2rem; margin-bottom:4px;">✈️</div>
  <h2 style="margin:0; font-size:1.3rem; font-weight:700; letter-spacing:-0.02em;">Skylark Drones</h2>
  <p style="margin:4px 0 0 0; font-size:0.75rem; opacity:0.85;">Business Intelligence Agent</p>
</div>
""", unsafe_allow_html=True)

        page = st.radio(
            "Navigation",
            ["💬 Chat", "📊 Data Explorer", "📈 Pipeline", "💰 Revenue", "⚙️ Operations", "🔍 Data Quality"],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown(f'<div style="margin:1rem 0 0.5rem 0; border-top:1px solid {C_BORDER};"></div>', unsafe_allow_html=True)

        wo = processor.get_work_orders()
        deals = processor.get_deals()
        st.markdown(f"""
<div style="padding:0.5rem;">
  <p style="font-size:0.75rem; font-weight:600; color:{C_MUTED}; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;">Data Sources</p>
  {stat_badge("📋", "Work Orders", len(wo))}
  {stat_badge("💼", "Deals", len(deals))}
</div>
""", unsafe_allow_html=True)

        st.markdown(f'<div style="margin:0.5rem 0; border-top:1px solid {C_BORDER};"></div>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:0.75rem; font-weight:600; color:{C_MUTED}; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;">Quick Queries</p>', unsafe_allow_html=True)

        quick_queries = [
            ("📊", "How's our pipeline looking?"),
            ("💰", "What's our total revenue?"),
            ("🏆", "Show me top 5 deals"),
            ("🏭", "Which sectors are strongest?"),
            ("⚠️", "Any data quality issues?"),
            ("🔄", "What's our deal funnel?"),
        ]
        for icon, q in quick_queries:
            if st.button(f"{icon}  {q}", key=f"quick_{q}", use_container_width=True):
                st.session_state["query_input"] = q
                st.rerun()

        st.markdown(f"""
<div style="margin-top:2rem; padding:1rem; background:rgba(255,255,255,0.05); border-radius:12px; text-align:center; border:1px solid rgba(255,255,255,0.08);">
  <p style="font-size:0.7rem; color:{C_MUTED}; margin:0;">Powered by Gemini AI</p>
  <p style="font-size:0.65rem; color:#CBD5E1; margin:2px 0 0 0;">v1.0.0</p>
</div>
""", unsafe_allow_html=True)

    page_map = {
        "💬 Chat": "Chat", "📊 Data Explorer": "Data Explorer",
        "📈 Pipeline": "Pipeline", "💰 Revenue": "Revenue",
        "⚙️ Operations": "Operations", "🔍 Data Quality": "Data Quality",
    }
    return page_map.get(page, "Chat")


# ──────────────────────────────────────────────
# KPI CARDS
# ──────────────────────────────────────────────
def render_kpi_cards():
    revenue = bi_engine.revenue_summary()
    pipeline = bi_engine.pipeline_health()
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card(c1, "Contract Value", format_currency(revenue.get("total_contract_value", 0)), "₹", "indigo")
    with c2: kpi_card(c2, "Pipeline Value", format_currency(pipeline.get("total_pipeline_value", 0)), "📈", "blue")
    with c3: kpi_card(c3, "Collected", format_currency(revenue.get("total_collected", 0)), "✅", "green")
    with c4: kpi_card(c4, "Open Deals", pipeline.get("open_deals_count", 0), "💼", "amber")


# ──────────────────────────────────────────────
# CHAT PAGE
# ──────────────────────────────────────────────
def render_chat():
    st.markdown(section_header("💬 Ask Your Business Question"), unsafe_allow_html=True)
    st.markdown(f'<p style="color:{C_MUTED}; font-size:0.88rem; margin-top:-0.5rem; margin-bottom:1rem;">Ask anything about pipeline, revenue, sectors, operations, and more.</p>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": "Hello! I'm your BI agent for Skylark Drones. I can help you with:\n\n"
                           "- **📊 Pipeline health** — deal status, stage distribution, conversion rates\n"
                           "- **💰 Revenue & billing** — contract values, collections, receivables\n"
                           "- **🏭 Sector performance** — Mining, Powerline, Renewables, etc.\n"
                           "- **⚙️ Operations** — project execution, delays, billing status\n"
                           "- **🏆 Deal analysis** — top deals, funnel, quarterly trends\n\n"
                           "What would you like to know?",
            }
        ]

    for msg in st.session_state["messages"]:
        role = msg["role"]
        if role == "user":
            st.markdown(f"""
<div style="display:flex; justify-content:flex-end; margin:12px 0;">
  <div style="background:linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); color:white; padding:14px 18px; border-radius:16px 16px 4px 16px; max-width:80%; margin-left:auto; box-shadow:0 4px 12px rgba(79,70,229,0.3);">
    <div style="display:flex; align-items:center; justify-content:flex-end; gap:8px;">
      <span>{msg['content']}</span>
      <div style="width:32px; height:32px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:0.85rem; background:linear-gradient(135deg, #4F46E5, #7C3AED); color:white;">👤</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            sources_html = ""
            if msg.get("sources"):
                sources_html = '<div style="margin-top:8px;">' + "".join([source_pill(s) for s in msg["sources"]]) + '</div>'
            notes_html = ""
            if msg.get("data_quality_notes"):
                notes_html = "".join([f'<div style="background:rgba(251,191,36,0.1); border-left:3px solid #FBBF24; padding:8px 12px; border-radius:6px; margin-top:8px; font-size:0.82rem; color:#FCD34D;">⚠️ {n}</div>' for n in msg["data_quality_notes"]])
            content_html = msg['content'].replace(chr(10), '<br>')
            st.markdown(f"""
<div style="display:flex; gap:10px; margin:12px 0;">
  <div style="width:32px; height:32px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:0.85rem; background:linear-gradient(135deg, #2563EB, #0EA5E9); color:white; flex-shrink:0;">🤖</div>
  <div style="background:{C_CARD}; color:{C_TEXT}; padding:14px 18px; border-radius:16px 16px 16px 4px; max-width:90%; box-shadow:{C_SHADOW}; border:1px solid {C_BORDER};">
    <div>{content_html}</div>
    {notes_html}
    {sources_html}
  </div>
</div>
""", unsafe_allow_html=True)

    query = st.chat_input("Ask about your business...", key="chat_input")
    if not query:
        query = st.session_state.pop("query_input", None)

    if query:
        st.session_state["messages"].append({"role": "user", "content": query})
        st.markdown(f"""
<div style="display:flex; justify-content:flex-end; margin:12px 0;">
  <div style="background:linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); color:white; padding:14px 18px; border-radius:16px 16px 4px 16px; max-width:80%; margin-left:auto; box-shadow:0 4px 12px rgba(79,70,229,0.3);">
    <div style="display:flex; align-items:center; justify-content:flex-end; gap:8px;">
      <span>{query}</span>
      <div style="width:32px; height:32px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:0.85rem; background:linear-gradient(135deg, #4F46E5, #7C3AED); color:white;">👤</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        with st.chat_message("assistant"):
            with st.spinner("🤖 Analyzing your data..."):
                result = asyncio.run(ai_agent.process_query(query))

            st.markdown(result["answer"])
            if result.get("data_quality_notes"):
                for note in result["data_quality_notes"]:
                    st.warning(f"⚠️ {note}")
            if result.get("sources"):
                sources_html = '<div style="margin-top:8px;">' + "".join([source_pill(s) for s in result["sources"]]) + '</div>'
                st.markdown(sources_html, unsafe_allow_html=True)
            if result.get("clarifying_question"):
                st.info(f"💡 {result['clarifying_question']}")

        st.session_state["messages"].append({
            "role": "assistant",
            "content": result["answer"],
            "data_quality_notes": result.get("data_quality_notes", []),
            "sources": result.get("sources", []),
        })


# ──────────────────────────────────────────────
# DATA EXPLORER
# ──────────────────────────────────────────────
def render_data_explorer():
    st.markdown(section_header("📊 Data Explorer"), unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Work Orders", "💼 Deals"])

    with tab1:
        wo = processor.get_work_orders()
        if wo.empty:
            st.warning("No work order data loaded.")
        else:
            st.markdown(f"""
<div style="background:{C_CARD}; padding:1rem 1.2rem; border-radius:12px; box-shadow:{C_SHADOW}; margin-bottom:1rem; border-left:3px solid {C_PRIMARY}; border:1px solid {C_BORDER};">
  <p style="margin:0; font-size:0.85rem; font-weight:600; color:{C_TEXT};">Work Orders — {len(wo)} records</p>
</div>
""", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                sectors = ["All"] + sorted(wo["sector"].dropna().unique().tolist())
                sector_filter = st.selectbox("Filter by Sector", sectors, key="wo_sector")
            with col2:
                statuses = ["All"] + sorted(wo["execution_status"].dropna().unique().tolist())
                status_filter = st.selectbox("Filter by Status", statuses, key="wo_status")
            filtered = wo.copy()
            if sector_filter != "All":
                filtered = filtered[filtered["sector"] == sector_filter]
            if status_filter != "All":
                filtered = filtered[filtered["execution_status"] == status_filter]
            display_cols = ["deal_name", "customer", "sector", "execution_status",
                            "billing_status", "amount_excl_gst", "collected_amount"]
            available_cols = [c for c in display_cols if c in filtered.columns]
            st.dataframe(filtered[available_cols], use_container_width=True, height=400)

    with tab2:
        deals = processor.get_deals()
        if deals.empty:
            st.warning("No deal data loaded.")
        else:
            st.markdown(f"""
<div style="background:{C_CARD}; padding:1rem 1.2rem; border-radius:12px; box-shadow:{C_SHADOW}; margin-bottom:1rem; border-left:3px solid {C_PRIMARY}; border:1px solid {C_BORDER};">
  <p style="margin:0; font-size:0.85rem; font-weight:600; color:{C_TEXT};">Deals — {len(deals)} records</p>
</div>
""", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                deal_statuses = ["All"] + sorted(deals["Deal Status"].dropna().unique().tolist())
                status_filter = st.selectbox("Filter by Status", deal_statuses, key="deal_status")
            with col2:
                deal_sectors = ["All"] + sorted(deals["sector_clean"].dropna().unique().tolist())
                sector_filter = st.selectbox("Filter by Sector", deal_sectors, key="deal_sector")
            with col3:
                deal_stages = ["All"] + sorted(deals["deal_stage_clean"].dropna().unique().tolist())
                stage_filter = st.selectbox("Filter by Stage", deal_stages, key="deal_stage")
            filtered = deals.copy()
            if status_filter != "All":
                filtered = filtered[filtered["Deal Status"] == status_filter]
            if sector_filter != "All":
                filtered = filtered[filtered["sector_clean"] == sector_filter]
            if stage_filter != "All":
                filtered = filtered[filtered["deal_stage_clean"] == stage_filter]
            display_cols = ["Deal Name", "Deal Status", "deal_stage_clean", "deal_value",
                           "sector_clean", "Closure Probability", "Tentative Close Date"]
            st.dataframe(filtered[display_cols], use_container_width=True, height=400)
            st.markdown(f'<p style="text-align:center; color:{C_MUTED}; font-size:0.82rem;">Showing {len(filtered)} of {len(deals)} records</p>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# PIPELINE PAGE
# ──────────────────────────────────────────────
def render_pipeline():
    st.markdown(section_header("📈 Pipeline Analysis"), unsafe_allow_html=True)
    pipeline = bi_engine.pipeline_health()
    if "error" in pipeline:
        st.error(pipeline["error"])
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card(c1, "Total Pipeline", format_currency(pipeline["total_pipeline_value"]), "📊", "indigo")
    with c2: kpi_card(c2, "Open Deals", pipeline["open_deals_count"], "🔵", "blue")
    with c3: kpi_card(c3, "Won Deals", pipeline["won_deals_count"], "✅", "green")
    with c4: kpi_card(c4, "Dead Deals", pipeline["dead_deals_count"], "🔴", "red")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(section_header("Deal Distribution by Stage"), unsafe_allow_html=True)
        funnel = bi_engine.deal_conversion_funnel()
        if funnel.get("funnel"):
            df = pd.DataFrame(funnel["funnel"])
            st.bar_chart(df.set_index("stage")["count"], color="#4F46E5")
    with col2:
        st.markdown(section_header("Pipeline by Sector"), unsafe_allow_html=True)
        sector = bi_engine.sector_performance()
        if "deals_by_sector" in sector:
            df = pd.DataFrame(sector["deals_by_sector"])
            if not df.empty:
                st.bar_chart(df.set_index("sector_clean")["deal_count"], color="#0EA5E9")

    st.markdown(section_header("Stage Details"), unsafe_allow_html=True)
    if funnel.get("funnel"):
        df = pd.DataFrame(funnel["funnel"])
        df.columns = ["Stage", "Count", "Value (₹)"]
        st.dataframe(df, use_container_width=True)


# ──────────────────────────────────────────────
# REVENUE PAGE
# ──────────────────────────────────────────────
def render_revenue():
    st.markdown(section_header("💰 Revenue & Billing"), unsafe_allow_html=True)
    revenue = bi_engine.revenue_summary()
    if "error" in revenue:
        st.error(revenue["error"])
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card(c1, "Contract Value", format_currency(revenue["total_contract_value"]), "₹", "indigo")
    with c2: kpi_card(c2, "Billed", format_currency(revenue["total_billed"]), "📄", "blue")
    with c3: kpi_card(c3, "Collected", format_currency(revenue["total_collected"]), "✅", "green")
    with c4: kpi_card(c4, "Receivable", format_currency(revenue["total_receivable"]), "⏳", "amber")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(section_header("Billing & Collection Ratios"), unsafe_allow_html=True)
        billing_color = "green" if revenue["billing_ratio"] >= 70 else ("amber" if revenue["billing_ratio"] >= 40 else "red")
        collection_color = "green" if revenue["collection_ratio"] >= 80 else ("amber" if revenue["collection_ratio"] >= 50 else "red")
        st.markdown(progress_bar("Billing Ratio", revenue["billing_ratio"], billing_color), unsafe_allow_html=True)
        st.markdown(progress_bar("Collection Ratio", revenue["collection_ratio"], collection_color), unsafe_allow_html=True)
    with col2:
        st.markdown(section_header("Revenue by Sector"), unsafe_allow_html=True)
        sector = bi_engine.sector_performance()
        if "revenue_by_sector" in sector:
            df = pd.DataFrame(sector["revenue_by_sector"])
            if not df.empty:
                st.bar_chart(df.set_index("sector")["total_value"], color="#818CF8")

    st.markdown(section_header("Quarterly Comparison"), unsafe_allow_html=True)
    quarterly = bi_engine.quarterly_comparison()
    if quarterly.get("data"):
        df = pd.DataFrame(quarterly["data"])
        if not df.empty:
            st.dataframe(df, use_container_width=True)

    st.markdown(section_header("Top Deals"), unsafe_allow_html=True)
    top = bi_engine.top_deals()
    if top.get("deals"):
        df = pd.DataFrame(top["deals"])
        st.dataframe(df, use_container_width=True)


# ──────────────────────────────────────────────
# OPERATIONS PAGE
# ──────────────────────────────────────────────
def render_operations():
    st.markdown(section_header("⚙️ Operational Metrics"), unsafe_allow_html=True)
    ops = bi_engine.operational_metrics()
    if "error" in ops:
        st.error(ops["error"])
        return

    completed = ops["by_status"].get("Completed", 0)
    c1, c2, c3 = st.columns(3)
    with c1: kpi_card(c1, "Total Projects", ops["total_projects"], "📋", "indigo")
    with c2: kpi_card(c2, "Overdue", ops["overdue_projects"], "⚠️", "red")
    with c3: kpi_card(c3, "Completed", completed, "✅", "green")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(section_header("By Execution Status"), unsafe_allow_html=True)
        if ops["by_status"]:
            st.bar_chart(pd.Series(ops["by_status"]), color="#4F46E5")
    with col2:
        st.markdown(section_header("By Billing Status"), unsafe_allow_html=True)
        if ops["by_billing_status"]:
            st.bar_chart(pd.Series(ops["by_billing_status"]), color="#0EA5E9")

    st.markdown(section_header("By Nature of Work"), unsafe_allow_html=True)
    if ops["by_nature"]:
        st.bar_chart(pd.Series(ops["by_nature"]), color="#10B981")


# ──────────────────────────────────────────────
# DATA QUALITY PAGE
# ──────────────────────────────────────────────
def render_data_quality():
    st.markdown(section_header("🔍 Data Quality Report"), unsafe_allow_html=True)
    wo = processor.get_work_orders()
    deals = processor.get_deals()

    tab1, tab2 = st.tabs(["📋 Work Orders", "💼 Deals"])

    def render_quality_tab(df, board_name):
        if df.empty:
            st.warning("No data loaded.")
            return
        report = processor.data_quality_report(df, board_name)

        c1, c2 = st.columns(2)
        with c1: kpi_card(c1, "Total Rows", report['total_rows'], "📊", "indigo")
        with c2: kpi_card(c2, "Issues Found", len(report['issues']), "⚠️", "red")

        if report["issues"]:
            st.markdown(section_header("Issues Found"), unsafe_allow_html=True)
            for issue in report["issues"]:
                if "critical" in issue:
                    st.markdown(f'<div style="background:rgba(248,113,113,0.1); border-left:3px solid #F87171; padding:10px 14px; border-radius:8px; margin:6px 0; font-size:0.85rem; color:#FCA5A5;">{badge_html("CRITICAL", "critical")} {issue}</div>', unsafe_allow_html=True)
                elif "data gap" in issue:
                    st.markdown(f'<div style="background:rgba(251,191,36,0.1); border-left:3px solid #FBBF24; padding:10px 14px; border-radius:8px; margin:6px 0; font-size:0.85rem; color:#FCD34D;">{badge_html("DATA GAP", "gap")} {issue}</div>', unsafe_allow_html=True)
                elif "partial" in issue:
                    st.markdown(f'<div style="background:rgba(251,191,36,0.1); border-left:3px solid #EAB308; padding:10px 14px; border-radius:8px; margin:6px 0; font-size:0.85rem; color:#FCD34D;">{badge_html("PARTIAL", "partial")} {issue}</div>', unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ {issue}")

        st.markdown(section_header("Null Analysis"), unsafe_allow_html=True)
        null_data = []
        for col, info in report["null_summary"].items():
            if info["null_pct"] > 0:
                null_data.append({"Column": col, "Null Count": info["null_count"], "Null %": info["null_pct"]})
        if null_data:
            ndf = pd.DataFrame(null_data).sort_values("Null %", ascending=False)
            for _, row in ndf.iterrows():
                pct = row["Null %"]
                if pct >= 90:
                    badge = badge_html("CRITICAL", "critical")
                    color = "red"
                elif pct >= 70:
                    badge = badge_html("DATA GAP", "gap")
                    color = "amber"
                elif pct >= 50:
                    badge = badge_html("PARTIAL", "partial")
                    color = "amber"
                else:
                    badge = badge_html("OK", "ok")
                    color = "green"
                st.markdown(f"""
<div style="margin:6px 0;">
  <div style="display:flex; align-items:center; gap:8px; margin-bottom:3px;">
    <span style="font-size:0.82rem; font-weight:500; color:{C_TEXT};">{row['Column']}</span>
    {badge}
    <span style="font-size:0.75rem; color:{C_MUTED};">{int(row['Null Count'])} rows</span>
  </div>
  {progress_bar('', int(pct), color)}
</div>
""", unsafe_allow_html=True)

    with tab1:
        render_quality_tab(wo, "Work Orders")
    with tab2:
        render_quality_tab(deals, "Deals")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    page = render_sidebar()

    if page == "Chat":
        render_kpi_cards()
        st.markdown(f'<div style="margin:0.5rem 0 1.5rem 0; border-top:1px solid {C_BORDER};"></div>', unsafe_allow_html=True)
        render_chat()
    elif page == "Data Explorer":
        render_data_explorer()
    elif page == "Pipeline":
        render_pipeline()
    elif page == "Revenue":
        render_revenue()
    elif page == "Operations":
        render_operations()
    elif page == "Data Quality":
        render_data_quality()

    st.markdown(f"""
<div style="text-align:center; padding:2rem 0 1rem 0; color:{C_MUTED}; font-size:0.75rem; border-top:1px solid {C_BORDER}; margin-top:2rem;">
  Skylark Drones BI Agent — Built for the Skylark Drones Technical Assignment
</div>
""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
