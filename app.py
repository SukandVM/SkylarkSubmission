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
    page_icon=" drones",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem; border-radius: 12px; color: white; text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 0.85rem; opacity: 0.9; }
    .metric-card p { margin: 0.3rem 0 0 0; font-size: 1.8rem; font-weight: bold; }
    .data-quality-warning {
        background: #fff3cd; border-left: 4px solid #ffc107;
        padding: 0.8rem; border-radius: 4px; margin: 0.5rem 0; font-size: 0.9rem;
    }
    .chat-message {
        padding: 1rem; border-radius: 8px; margin: 0.5rem 0;
        border-left: 4px solid #667eea; background: #f8f9fa;
    }
    .source-tag {
        display: inline-block; background: #e9ecef; padding: 2px 8px;
        border-radius: 12px; font-size: 0.75rem; margin: 2px;
    }
</style>
""", unsafe_allow_html=True)


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


def render_kpi_cards():
    col1, col2, col3, col4 = st.columns(4)
    revenue = bi_engine.revenue_summary()
    pipeline = bi_engine.pipeline_health()
    ops = bi_engine.operational_metrics()
    with col1:
        st.metric("Total Contract Value", format_currency(revenue.get("total_contract_value", 0)))
    with col2:
        st.metric("Pipeline Value", format_currency(pipeline.get("total_pipeline_value", 0)))
    with col3:
        st.metric("Total Collected", format_currency(revenue.get("total_collected", 0)))
    with col4:
        st.metric("Open Deals", pipeline.get("open_deals_count", 0))


def render_sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/drone.png", width=64)
        st.title("Skylark Drones")
        st.caption("Business Intelligence Agent")
        st.divider()
        page = st.radio(
            "Navigation",
            ["Chat", "Data Explorer", "Pipeline", "Revenue", "Operations", "Data Quality"],
            index=0,
        )
        st.divider()
        st.markdown("**Data Sources:**")
        wo = processor.get_work_orders()
        deals = processor.get_deals()
        st.markdown(f"- Work Orders: {len(wo)} records")
        st.markdown(f"- Deals: {len(deals)} records")
        st.divider()
        st.markdown("**Quick Queries:**")
        quick_queries = [
            "How's our pipeline looking?",
            "What's our total revenue?",
            "Show me top 5 deals",
            "Which sectors are we strongest in?",
            "Any data quality issues?",
            "What's our deal conversion funnel?",
        ]
        for q in quick_queries:
            if st.button(q, key=f"quick_{q}", use_container_width=True):
                st.session_state["query_input"] = q
                st.rerun()
    return page


def render_chat():
    st.header(" Ask Your Business Question")
    st.caption("Ask anything about Skylark Drones' business data — pipeline, revenue, sectors, operations, and more.")

    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": "Hello! I'm your BI agent for Skylark Drones. I can help you with:\n\n"
                           "- **Pipeline health** — deal status, stage distribution, conversion rates\n"
                           "- **Revenue & billing** — contract values, collections, receivables\n"
                           "- **Sector performance** — Mining, Powerline, Renewables, etc.\n"
                           "- **Operations** — project execution, delays, billing status\n"
                           "- **Deal analysis** — top deals, funnel, quarterly trends\n\n"
                           "What would you like to know?",
            }
        ]

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("data_quality_notes"):
                for note in msg["data_quality_notes"]:
                    st.warning(f" {note}")
            if msg.get("sources"):
                st.caption("Sources: " + " | ".join(msg["sources"]))

    query = st.chat_input("Ask about your business...", key="chat_input")
    if not query:
        query = st.session_state.pop("query_input", None)

    if query:
        st.session_state["messages"].append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing your data..."):
                result = asyncio.run(ai_agent.process_query(query))
            st.markdown(result["answer"])
            if result.get("data_quality_notes"):
                for note in result["data_quality_notes"]:
                    st.warning(f" {note}")
            if result.get("sources"):
                st.caption("Sources: " + " | ".join(result["sources"]))
            if result.get("clarifying_question"):
                st.info(f" {result['clarifying_question']}")

        st.session_state["messages"].append({
            "role": "assistant",
            "content": result["answer"],
            "data_quality_notes": result.get("data_quality_notes", []),
            "sources": result.get("sources", []),
        })


def render_data_explorer():
    st.header(" Data Explorer")
    tab1, tab2 = st.tabs(["Work Orders", "Deals"])

    with tab1:
        wo = processor.get_work_orders()
        if wo.empty:
            st.warning("No work order data loaded.")
        else:
            st.subheader(f"Work Orders ({len(wo)} records)")
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
            st.caption(f"Showing {len(filtered)} of {len(wo)} records")

    with tab2:
        deals = processor.get_deals()
        if deals.empty:
            st.warning("No deal data loaded.")
        else:
            st.subheader(f"Deals ({len(deals)} records)")
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
            st.caption(f"Showing {len(filtered)} of {len(deals)} records")


def render_pipeline():
    st.header(" Pipeline Analysis")
    pipeline = bi_engine.pipeline_health()
    if "error" in pipeline:
        st.error(pipeline["error"])
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Pipeline", format_currency(pipeline["total_pipeline_value"]))
    with col2:
        st.metric("Open Deals", pipeline["open_deals_count"])
    with col3:
        st.metric("Won Deals", pipeline["won_deals_count"])
    with col4:
        st.metric("Dead Deals", pipeline["dead_deals_count"])

    st.subheader("Deal Distribution by Stage")
    funnel = bi_engine.deal_conversion_funnel()
    if funnel.get("funnel"):
        df = pd.DataFrame(funnel["funnel"])
        st.bar_chart(df.set_index("stage")["count"])

    st.subheader("Pipeline by Sector")
    sector = bi_engine.sector_performance()
    if "deals_by_sector" in sector:
        df = pd.DataFrame(sector["deals_by_sector"])
        if not df.empty:
            st.bar_chart(df.set_index("sector_clean")["deal_count"])


def render_revenue():
    st.header(" Revenue & Billing")
    revenue = bi_engine.revenue_summary()
    if "error" in revenue:
        st.error(revenue["error"])
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Contract Value", format_currency(revenue["total_contract_value"]))
    with col2:
        st.metric("Billed", format_currency(revenue["total_billed"]))
    with col3:
        st.metric("Collected", format_currency(revenue["total_collected"]))
    with col4:
        st.metric("Receivable", format_currency(revenue["total_receivable"]))

    st.subheader("Billing & Collection Ratios")
    col1, col2 = st.columns(2)
    with col1:
        st.progress(revenue["billing_ratio"] / 100, text=f"Billing: {revenue['billing_ratio']}%")
    with col2:
        st.progress(revenue["collection_ratio"] / 100, text=f"Collection: {revenue['collection_ratio']}%")

    st.subheader("Revenue by Sector")
    sector = bi_engine.sector_performance()
    if "work_orders_by_sector" in sector:
        df = pd.DataFrame(sector["work_orders_by_sector"])
        if not df.empty:
            st.bar_chart(df.set_index("sector")["total_value"])

    st.subheader("Top Deals by Value")
    top = bi_engine.top_deals(10)
    if top.get("deals"):
        df = pd.DataFrame(top["deals"])
        st.dataframe(df, use_container_width=True)


def render_operations():
    st.header(" Operational Metrics")
    ops = bi_engine.operational_metrics()
    if "error" in ops:
        st.error(ops["error"])
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Projects", ops["total_projects"])
    with col2:
        st.metric("Overdue Projects", ops["overdue_projects"])
    with col3:
        completed = ops["by_status"].get("Completed", 0)
        st.metric("Completed", completed)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("By Execution Status")
        if ops["by_status"]:
            st.bar_chart(pd.Series(ops["by_status"]))
    with col2:
        st.subheader("By Billing Status")
        if ops["by_billing_status"]:
            st.bar_chart(pd.Series(ops["by_billing_status"]))

    st.subheader("By Nature of Work")
    if ops["by_nature"]:
        st.bar_chart(pd.Series(ops["by_nature"]))


def render_data_quality():
    st.header(" Data Quality Report")
    wo = processor.get_work_orders()
    deals = processor.get_deals()

    tab1, tab2 = st.tabs(["Work Orders", "Deals"])

    with tab1:
        if wo.empty:
            st.warning("No work order data loaded.")
        else:
            report = processor.data_quality_report(wo, "Work Orders")
            st.metric("Total Rows", report["total_rows"])
            if report["issues"]:
                st.subheader("Issues Found")
                for issue in report["issues"]:
                    st.error(issue)
            st.subheader("Null Analysis")
            null_data = []
            for col, info in report["null_summary"].items():
                if info["null_pct"] > 0:
                    null_data.append({"Column": col, "Null Count": info["null_count"], "Null %": info["null_pct"]})
            if null_data:
                df = pd.DataFrame(null_data).sort_values("Null %", ascending=False)
                st.dataframe(df, use_container_width=True)

    with tab2:
        if deals.empty:
            st.warning("No deal data loaded.")
        else:
            report = processor.data_quality_report(deals, "Deals")
            st.metric("Total Rows", report["total_rows"])
            if report["issues"]:
                st.subheader("Issues Found")
                for issue in report["issues"]:
                    st.error(issue)
            st.subheader("Null Analysis")
            null_data = []
            for col, info in report["null_summary"].items():
                if info["null_pct"] > 0:
                    null_data.append({"Column": col, "Null Count": info["null_count"], "Null %": info["null_pct"]})
            if null_data:
                df = pd.DataFrame(null_data).sort_values("Null %", ascending=False)
                st.dataframe(df, use_container_width=True)


def main():
    page = render_sidebar()

    if page == "Chat":
        render_kpi_cards()
        st.divider()
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


if __name__ == "__main__":
    main()
