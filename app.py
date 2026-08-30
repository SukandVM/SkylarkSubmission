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

# ──────────────────────────────────────────────
# CUSTOM CSS — Light Theme with Accents
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #4F46E5;
    --primary-light: #818CF8;
    --secondary: #0EA5E9;
    --success: #10B981;
    --warning: #F59E0B;
    --danger: #EF4444;
    --bg: #F1F5F9;
    --card: #FFFFFF;
    --text: #1E293B;
    --text-muted: #64748B;
    --border: #E2E8F0;
    --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.04);
}

/* ── Global ── */
.stApp { font-family: 'Inter', sans-serif; background: var(--bg) !important; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important; border-right: 1px solid var(--border) !important; }
.block-container { padding-top: 2rem !important; }

/* ── Sidebar ── */
.sidebar-brand {
    text-align: center; padding: 1.5rem 0 1rem 0;
    background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
    border-radius: 16px; margin: 0 0.5rem 1rem 0.5rem;
    color: white;
}
.sidebar-brand h2 { margin: 0; font-size: 1.3rem; font-weight: 700; letter-spacing: -0.02em; }
.sidebar-brand p { margin: 4px 0 0 0; font-size: 0.75rem; opacity: 0.85; }

.nav-pill {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 16px; margin: 3px 0; border-radius: 10px;
    font-size: 0.88rem; font-weight: 500; color: var(--text);
    cursor: pointer; transition: all 0.2s ease;
    border: 1px solid transparent;
}
.nav-pill:hover { background: #EEF2FF; border-color: var(--primary-light); }
.nav-pill.active { background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%); color: white; border-color: transparent; }
.nav-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

.stat-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #F1F5F9; border-radius: 20px; padding: 5px 12px;
    font-size: 0.78rem; font-weight: 500; color: var(--text-muted); margin: 3px 0;
}
.stat-badge .num { color: var(--primary); font-weight: 700; }

.quick-btn {
    display: block; width: 100%; padding: 10px 14px; margin: 4px 0;
    background: white; border: 1px solid var(--border); border-radius: 10px;
    font-size: 0.82rem; color: var(--text); text-align: left;
    cursor: pointer; transition: all 0.2s ease;
}
.quick-btn:hover { border-color: var(--primary); background: #EEF2FF; transform: translateX(3px); }

/* ── KPI Cards ── */
.kpi-row { display: flex; gap: 16px; margin-bottom: 1.5rem; }
.kpi-card {
    flex: 1; background: var(--card); border-radius: 16px;
    padding: 1.4rem 1.2rem; box-shadow: var(--shadow);
    border-top: 3px solid var(--primary); position: relative; overflow: hidden;
}
.kpi-card::after {
    content: ''; position: absolute; top: -20px; right: -20px;
    width: 80px; height: 80px; border-radius: 50%;
    background: linear-gradient(135deg, rgba(79,70,229,0.08) 0%, rgba(14,165,233,0.05) 100%);
}
.kpi-card.green { border-top-color: var(--success); }
.kpi-card.green::after { background: linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(16,185,129,0.03) 100%); }
.kpi-card.amber { border-top-color: var(--warning); }
.kpi-card.amber::after { background: linear-gradient(135deg, rgba(245,158,11,0.08) 0%, rgba(245,158,11,0.03) 100%); }
.kpi-card.red { border-top-color: var(--danger); }
.kpi-card.red::after { background: linear-gradient(135deg, rgba(239,68,68,0.08) 0%, rgba(239,68,68,0.03) 100%); }
.kpi-card.blue { border-top-color: var(--secondary); }
.kpi-card.blue::after { background: linear-gradient(135deg, rgba(14,165,233,0.08) 0%, rgba(14,165,233,0.03) 100%); }
.kpi-icon {
    width: 40px; height: 40px; border-radius: 10px; display: flex;
    align-items: center; justify-content: center; font-size: 1.2rem;
    margin-bottom: 10px; position: relative; z-index: 1;
}
.kpi-icon.indigo { background: #EEF2FF; color: var(--primary); }
.kpi-icon.green { background: #ECFDF5; color: var(--success); }
.kpi-icon.amber { background: #FFFBEB; color: var(--warning); }
.kpi-icon.red { background: #FEF2F2; color: var(--danger); }
.kpi-icon.blue { background: #F0F9FF; color: var(--secondary); }
.kpi-label { font-size: 0.78rem; font-weight: 500; color: var(--text-muted); margin: 0; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-value { font-size: 1.6rem; font-weight: 700; color: var(--text); margin: 4px 0 0 0; }

/* ── Section Headers ── */
.section-header {
    font-size: 1.1rem; font-weight: 700; color: var(--text);
    padding-bottom: 8px; margin-bottom: 1rem;
    border-bottom: 2px solid var(--primary); display: inline-block;
}

/* ── Chat ── */
.chat-user {
    background: linear-gradient(135deg, var(--primary) 0%, #6366F1 100%);
    color: white; padding: 14px 18px; border-radius: 16px 16px 4px 16px;
    margin: 8px 0; max-width: 80%; margin-left: auto; box-shadow: var(--shadow);
}
.chat-assistant {
    background: var(--card); color: var(--text); padding: 14px 18px;
    border-radius: 16px 16px 16px 4px; margin: 8px 0; max-width: 90%;
    box-shadow: var(--shadow); border: 1px solid var(--border);
}
.chat-avatar {
    width: 32px; height: 32px; border-radius: 50%; display: inline-flex;
    align-items: center; justify-content: center; font-size: 0.85rem;
    margin-right: 8px; flex-shrink: 0;
}
.chat-avatar.user { background: var(--primary); color: white; }
.chat-avatar.bot { background: var(--secondary); color: white; }

.source-pill {
    display: inline-block; background: #F1F5F9; color: var(--text-muted);
    padding: 3px 10px; border-radius: 20px; font-size: 0.72rem;
    font-weight: 500; margin: 2px; border: 1px solid var(--border);
}

/* ── Progress Bars ── */
.progress-container { margin: 8px 0; }
.progress-label { display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px; }
.progress-track { height: 10px; background: #E2E8F0; border-radius: 10px; overflow: hidden; }
.progress-fill {
    height: 100%; border-radius: 10px; transition: width 0.5s ease;
    background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%);
}
.progress-fill.green { background: linear-gradient(90deg, #059669 0%, var(--success) 100%); }
.progress-fill.amber { background: linear-gradient(90deg, #D97706 0%, var(--warning) 100%); }
.progress-fill.red { background: linear-gradient(90deg, #DC2626 0%, var(--danger) 100%); }

/* ── Severity Badges ── */
.badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600;
}
.badge-critical { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
.badge-gap { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
.badge-partial { background: #FEF9C3; color: #A16207; border: 1px solid #FDE047; }
.badge-ok { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }

/* ── Data Explorer ── */
.filter-bar {
    background: var(--card); padding: 1rem 1.2rem; border-radius: 12px;
    box-shadow: var(--shadow); margin-bottom: 1rem;
    border-left: 3px solid var(--primary);
}

/* ── Tables ── */
.stDataFrame { border-radius: 12px !important; overflow: hidden; box-shadow: var(--shadow) !important; }

/* ── Cards ── */
.glass-card {
    background: var(--card); border-radius: 16px; padding: 1.5rem;
    box-shadow: var(--shadow); border: 1px solid var(--border); margin-bottom: 1rem;
}

/* ── Footer ── */
.footer {
    text-align: center; padding: 2rem 0 1rem 0; color: var(--text-muted);
    font-size: 0.75rem; border-top: 1px solid var(--border); margin-top: 2rem;
}

/* ── Streamlit overrides ── */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    padding: 10px 20px; border-radius: 10px 10px 0 0;
    font-weight: 500; font-size: 0.88rem;
}
.stTabs [aria-selected="true"] { background: var(--primary); color: white; }
div[data-testid="stMetric"] {
    background: var(--card); padding: 12px 16px; border-radius: 12px;
    box-shadow: var(--shadow); border-left: 3px solid var(--primary);
}
div[data-testid="stMetric"] label { font-size: 0.78rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; }
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


def render_kpi_html(label, value, icon, color_class):
    return f"""
    <div class="kpi-card {color_class}">
        <div class="kpi-icon {color_class}">{icon}</div>
        <p class="kpi-label">{label}</p>
        <p class="kpi-value">{value}</p>
    </div>
    """


def render_progress_html(label, value, pct, color_class=""):
    return f"""
    <div class="progress-container">
        <div class="progress-label"><span>{label}</span><span style="font-weight:600;">{pct}%</span></div>
        <div class="progress-track"><div class="progress-fill {color_class}" style="width:{pct}%;"></div></div>
    </div>
    """


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <div style="font-size:2.2rem; margin-bottom:4px;">✈️</div>
            <h2>Skylark Drones</h2>
            <p>Business Intelligence Agent</p>
        </div>
        """, unsafe_allow_html=True)

        page = st.radio(
            "Navigation",
            ["💬 Chat", "📊 Data Explorer", "📈 Pipeline", "💰 Revenue", "⚙️ Operations", "🔍 Data Quality"],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("<div style='margin: 1rem 0 0.5rem 0; border-top: 1px solid #E2E8F0;'></div>", unsafe_allow_html=True)

        wo = processor.get_work_orders()
        deals = processor.get_deals()
        st.markdown(f"""
        <div style="padding: 0.5rem;">
            <p style="font-size:0.75rem; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;">Data Sources</p>
            <div class="stat-badge">📋 Work Orders <span class="num">{len(wo)}</span></div>
            <div class="stat-badge">💼 Deals <span class="num">{len(deals)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin: 0.5rem 0; border-top: 1px solid #E2E8F0;'></div>", unsafe_allow_html=True)

        st.markdown('<p style="font-size:0.75rem; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;">Quick Queries</p>', unsafe_allow_html=True)
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

        st.markdown("""
        <div style="margin-top: 2rem; padding: 1rem; background: #F8FAFC; border-radius: 12px; text-align: center;">
            <p style="font-size: 0.7rem; color: #94A3B8; margin: 0;">Powered by Gemini AI</p>
            <p style="font-size: 0.65rem; color: #CBD5E1; margin: 2px 0 0 0;">v1.0.0</p>
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
    cards = render_kpi_html("Contract Value", format_currency(revenue.get("total_contract_value", 0)), "₹", "indigo")
    cards += render_kpi_html("Pipeline Value", format_currency(pipeline.get("total_pipeline_value", 0)), "📈", "blue")
    cards += render_kpi_html("Collected", format_currency(revenue.get("total_collected", 0)), "✅", "green")
    cards += render_kpi_html("Open Deals", pipeline.get("open_deals_count", 0), "💼", "amber")
    st.markdown(f'<div class="kpi-row">{cards}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# CHAT PAGE
# ──────────────────────────────────────────────
def render_chat():
    st.markdown('<p class="section-header">💬 Ask Your Business Question</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#64748B; font-size:0.88rem; margin-top:-0.5rem; margin-bottom:1rem;">Ask anything about pipeline, revenue, sectors, operations, and more.</p>', unsafe_allow_html=True)

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
                <div class="chat-user">
                    <div style="display:flex; align-items:center; justify-content:flex-end; gap:8px;">
                        <span>{msg['content']}</span>
                        <div class="chat-avatar user">👤</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            sources_html = ""
            if msg.get("sources"):
                sources_html = "".join([f'<span class="source-pill">{s}</span>' for s in msg["sources"]])
                sources_html = f'<div style="margin-top:8px;">{sources_html}</div>'
            notes_html = ""
            if msg.get("data_quality_notes"):
                notes_html = "".join([f'<div style="background:#FFFBEB; border-left:3px solid #F59E0B; padding:8px 12px; border-radius:6px; margin-top:8px; font-size:0.82rem; color:#92400E;">⚠️ {n}</div>' for n in msg["data_quality_notes"]])
            st.markdown(f"""
            <div style="display:flex; gap:10px; margin:12px 0;">
                <div class="chat-avatar bot">🤖</div>
                <div class="chat-assistant">
                    <div>{msg['content'].replace(chr(10), '<br>')}</div>
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
            <div class="chat-user">
                <div style="display:flex; align-items:center; justify-content:flex-end; gap:8px;">
                    <span>{query}</span>
                    <div class="chat-avatar user">👤</div>
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
                sources_html = "".join([f'<span class="source-pill">{s}</span>' for s in result["sources"]])
                st.markdown(f'<div style="margin-top:8px;">{sources_html}</div>', unsafe_allow_html=True)
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
    st.markdown('<p class="section-header">📊 Data Explorer</p>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Work Orders", "💼 Deals"])

    with tab1:
        wo = processor.get_work_orders()
        if wo.empty:
            st.warning("No work order data loaded.")
        else:
            st.markdown(f"""
            <div class="filter-bar">
                <p style="margin:0; font-size:0.85rem; font-weight:600; color:var(--text);">Work Orders — {len(wo)} records</p>
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
            st.dataframe(filtered, use_container_width=True, height=400)
            st.markdown(f'<p style="text-align:center; color:var(--text-muted); font-size:0.82rem;">Showing {len(filtered)} of {len(wo)} records</p>', unsafe_allow_html=True)

    with tab2:
        deals = processor.get_deals()
        if deals.empty:
            st.warning("No deal data loaded.")
        else:
            st.markdown(f"""
            <div class="filter-bar">
                <p style="margin:0; font-size:0.85rem; font-weight:600; color:var(--text);">Deals — {len(deals)} records</p>
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
            st.markdown(f'<p style="text-align:center; color:var(--text-muted); font-size:0.82rem;">Showing {len(filtered)} of {len(deals)} records</p>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# PIPELINE PAGE
# ──────────────────────────────────────────────
def render_pipeline():
    st.markdown('<p class="section-header">📈 Pipeline Analysis</p>', unsafe_allow_html=True)
    pipeline = bi_engine.pipeline_health()
    if "error" in pipeline:
        st.error(pipeline["error"])
        return

    cards = render_kpi_html("Total Pipeline", format_currency(pipeline["total_pipeline_value"]), "📊", "indigo")
    cards += render_kpi_html("Open Deals", pipeline["open_deals_count"], "🔵", "blue")
    cards += render_kpi_html("Won Deals", pipeline["won_deals_count"], "✅", "green")
    cards += render_kpi_html("Dead Deals", pipeline["dead_deals_count"], "🔴", "red")
    st.markdown(f'<div class="kpi-row">{cards}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p class="section-header">Deal Distribution by Stage</p>', unsafe_allow_html=True)
        funnel = bi_engine.deal_conversion_funnel()
        if funnel.get("funnel"):
            df = pd.DataFrame(funnel["funnel"])
            st.bar_chart(df.set_index("stage")["count"], color="#4F46E5")
    with col2:
        st.markdown('<p class="section-header">Pipeline by Sector</p>', unsafe_allow_html=True)
        sector = bi_engine.sector_performance()
        if "deals_by_sector" in sector:
            df = pd.DataFrame(sector["deals_by_sector"])
            if not df.empty:
                st.bar_chart(df.set_index("sector_clean")["deal_count"], color="#0EA5E9")

    st.markdown('<p class="section-header">Stage Details</p>', unsafe_allow_html=True)
    if funnel.get("funnel"):
        df = pd.DataFrame(funnel["funnel"])
        df.columns = ["Stage", "Count", "Value (₹)"]
        st.dataframe(df, use_container_width=True)


# ──────────────────────────────────────────────
# REVENUE PAGE
# ──────────────────────────────────────────────
def render_revenue():
    st.markdown('<p class="section-header">💰 Revenue & Billing</p>', unsafe_allow_html=True)
    revenue = bi_engine.revenue_summary()
    if "error" in revenue:
        st.error(revenue["error"])
        return

    cards = render_kpi_html("Contract Value", format_currency(revenue["total_contract_value"]), "₹", "indigo")
    cards += render_kpi_html("Billed", format_currency(revenue["total_billed"]), "📄", "blue")
    cards += render_kpi_html("Collected", format_currency(revenue["total_collected"]), "✅", "green")
    cards += render_kpi_html("Receivable", format_currency(revenue["total_receivable"]), "⏳", "amber")
    st.markdown(f'<div class="kpi-row">{cards}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p class="section-header">Billing & Collection Ratios</p>', unsafe_allow_html=True)
        billing_color = "green" if revenue["billing_ratio"] >= 70 else ("amber" if revenue["billing_ratio"] >= 40 else "red")
        collection_color = "green" if revenue["collection_ratio"] >= 80 else ("amber" if revenue["collection_ratio"] >= 50 else "red")
        st.markdown(render_progress_html("Billing Ratio", revenue["total_billed"], revenue["billing_ratio"], billing_color), unsafe_allow_html=True)
        st.markdown(render_progress_html("Collection Ratio", revenue["total_collected"], revenue["collection_ratio"], collection_color), unsafe_allow_html=True)
    with col2:
        st.markdown('<p class="section-header">Revenue by Sector</p>', unsafe_allow_html=True)
        sector = bi_engine.sector_performance()
        if "work_orders_by_sector" in sector:
            df = pd.DataFrame(sector["work_orders_by_sector"])
            if not df.empty:
                st.bar_chart(df.set_index("sector")["total_value"], color="#4F46E5")

    st.markdown('<p class="section-header">Top Deals by Value</p>', unsafe_allow_html=True)
    top = bi_engine.top_deals(10)
    if top.get("deals"):
        df = pd.DataFrame(top["deals"])
        st.dataframe(df, use_container_width=True)


# ──────────────────────────────────────────────
# OPERATIONS PAGE
# ──────────────────────────────────────────────
def render_operations():
    st.markdown('<p class="section-header">⚙️ Operational Metrics</p>', unsafe_allow_html=True)
    ops = bi_engine.operational_metrics()
    if "error" in ops:
        st.error(ops["error"])
        return

    completed = ops["by_status"].get("Completed", 0)
    cards = render_kpi_html("Total Projects", ops["total_projects"], "📋", "indigo")
    cards += render_kpi_html("Overdue", ops["overdue_projects"], "⚠️", "red")
    cards += render_kpi_html("Completed", completed, "✅", "green")
    st.markdown(f'<div class="kpi-row">{cards}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p class="section-header">By Execution Status</p>', unsafe_allow_html=True)
        if ops["by_status"]:
            st.bar_chart(pd.Series(ops["by_status"]), color="#4F46E5")
    with col2:
        st.markdown('<p class="section-header">By Billing Status</p>', unsafe_allow_html=True)
        if ops["by_billing_status"]:
            st.bar_chart(pd.Series(ops["by_billing_status"]), color="#0EA5E9")

    st.markdown('<p class="section-header">By Nature of Work</p>', unsafe_allow_html=True)
    if ops["by_nature"]:
        st.bar_chart(pd.Series(ops["by_nature"]), color="#10B981")


# ──────────────────────────────────────────────
# DATA QUALITY PAGE
# ──────────────────────────────────────────────
def render_data_quality():
    st.markdown('<p class="section-header">🔍 Data Quality Report</p>', unsafe_allow_html=True)
    wo = processor.get_work_orders()
    deals = processor.get_deals()

    tab1, tab2 = st.tabs(["📋 Work Orders", "💼 Deals"])

    def render_quality_tab(df, board_name):
        if df.empty:
            st.warning("No data loaded.")
            return
        report = processor.data_quality_report(df, board_name)

        st.markdown(f"""
        <div style="display:flex; gap:16px; margin-bottom:1.5rem;">
            <div class="kpi-card indigo" style="flex:1;">
                <p class="kpi-label">Total Rows</p>
                <p class="kpi-value">{report['total_rows']}</p>
            </div>
            <div class="kpi-card" style="flex:1; border-top-color: var(--danger);">
                <p class="kpi-label">Issues Found</p>
                <p class="kpi-value">{len(report['issues'])}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if report["issues"]:
            st.markdown('<p class="section-header">Issues Found</p>', unsafe_allow_html=True)
            for issue in report["issues"]:
                if "critical" in issue:
                    st.markdown(f'<div style="background:#FEF2F2; border-left:3px solid #EF4444; padding:10px 14px; border-radius:8px; margin:6px 0; font-size:0.85rem;"><span class="badge badge-critical">CRITICAL</span> {issue}</div>', unsafe_allow_html=True)
                elif "data gap" in issue:
                    st.markdown(f'<div style="background:#FFFBEB; border-left:3px solid #F59E0B; padding:10px 14px; border-radius:8px; margin:6px 0; font-size:0.85rem;"><span class="badge badge-gap">DATA GAP</span> {issue}</div>', unsafe_allow_html=True)
                elif "partial" in issue:
                    st.markdown(f'<div style="background:#FEF9C3; border-left:3px solid #EAB308; padding:10px 14px; border-radius:8px; margin:6px 0; font-size:0.85rem;"><span class="badge badge-partial">PARTIAL</span> {issue}</div>', unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ {issue}")

        st.markdown('<p class="section-header">Null Analysis</p>', unsafe_allow_html=True)
        null_data = []
        for col, info in report["null_summary"].items():
            if info["null_pct"] > 0:
                null_data.append({"Column": col, "Null Count": info["null_count"], "Null %": info["null_pct"]})
        if null_data:
            ndf = pd.DataFrame(null_data).sort_values("Null %", ascending=False)
            for _, row in ndf.iterrows():
                pct = row["Null %"]
                if pct >= 90:
                    badge = '<span class="badge badge-critical">CRITICAL</span>'
                    color = "red"
                elif pct >= 70:
                    badge = '<span class="badge badge-gap">DATA GAP</span>'
                    color = "amber"
                elif pct >= 50:
                    badge = '<span class="badge badge-partial">PARTIAL</span>'
                    color = "amber"
                else:
                    badge = '<span class="badge badge-ok">OK</span>'
                    color = "green"
                st.markdown(f"""
                <div style="margin:6px 0;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:3px;">
                        <span style="font-size:0.82rem; font-weight:500;">{row['Column']}</span>
                        {badge}
                        <span style="font-size:0.75rem; color:#94A3B8;">{int(row['Null Count'])} rows</span>
                    </div>
                    {render_progress_html('', '', int(pct), color)}
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
        st.markdown("<div style='margin: 0.5rem 0 1.5rem 0; border-top: 1px solid #E2E8F0;'></div>", unsafe_allow_html=True)
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

    st.markdown("""
    <div class="footer">
        <p>Skylark Drones BI Agent — Built for the Skylark Drones Technical Assignment</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
