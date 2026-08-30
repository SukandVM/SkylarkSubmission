import pandas as pd
from typing import Optional
from backend.services.data_processor import processor


class BIEngine:
    def __init__(self):
        self._dp = processor

    def revenue_summary(self, sector: str = None, year: int = None) -> dict:
        wo = self._dp.get_work_orders()
        if wo.empty:
            return {"error": "No work order data available"}
        df = wo.copy()
        if sector:
            df = df[df["sector"].str.contains(sector, case=False, na=False)]
        if year:
            if "date_of_po_loi" in df.columns:
                df["year"] = pd.to_datetime(df["date_of_po_loi"], errors="coerce").dt.year
                df = df[df["year"] == year]
        total_amount = df["amount_excl_gst"].sum()
        total_billed = df["billed_value_excl_gst"].sum()
        total_collected = df["collected_amount"].sum()
        total_receivable = df["amount_receivable"].sum()
        return {
            "metric": "revenue_summary",
            "total_contract_value": round(total_amount, 2),
            "total_billed": round(total_billed, 2),
            "total_collected": round(total_collected, 2),
            "total_receivable": round(total_receivable, 2),
            "billing_ratio": round(total_billed / total_amount * 100, 1) if total_amount > 0 else 0,
            "collection_ratio": round(total_collected / total_billed * 100, 1) if total_billed > 0 else 0,
            "project_count": len(df),
            "sector_filter": sector,
        }

    def pipeline_health(self, sector: str = None) -> dict:
        deals = self._dp.get_deals()
        if deals.empty:
            return {"error": "No deal data available"}
        df = deals.copy()
        if sector:
            df = df[df["sector_clean"].str.contains(sector, case=False, na=False)]
        open_deals = df[df["Deal Status"] == "Open"]
        won_deals = df[df["Deal Status"] == "Won"]
        dead_deals = df[df["Deal Status"] == "Dead"]
        on_hold = df[df["Deal Status"] == "On Hold"]
        total_pipeline = open_deals["deal_value"].sum()
        won_value = won_deals["deal_value"].sum()
        by_stage = {}
        for stage in df["deal_stage_clean"].dropna().unique():
            stage_df = df[df["deal_stage_clean"] == stage]
            by_stage[stage] = {
                "count": len(stage_df),
                "value": round(stage_df["deal_value"].sum(), 2),
            }
        return {
            "metric": "pipeline_health",
            "total_pipeline_value": round(total_pipeline, 2),
            "open_deals_count": len(open_deals),
            "won_deals_count": len(won_deals),
            "won_value": round(won_value, 2),
            "dead_deals_count": len(dead_deals),
            "on_hold_count": len(on_hold),
            "by_stage": by_stage,
            "sector_filter": sector,
        }

    def sector_performance(self, sector: str = None) -> dict:
        deals = self._dp.get_deals()
        wo = self._dp.get_work_orders()
        result = {}
        if not deals.empty:
            deal_df = deals.copy()
            if sector:
                deal_df = deal_df[deal_df["sector_clean"].str.contains(sector, case=False, na=False)]
            deal_sector = deal_df.groupby("sector_clean").agg(
                deal_count=("Deal Name", "count"),
                total_value=("deal_value", "sum"),
                won_count=("Deal Status", lambda x: (x == "Won").sum()),
            ).reset_index()
            result["deals_by_sector"] = deal_sector.to_dict("records")
        if not wo.empty:
            wo_df = wo.copy()
            if sector:
                wo_df = wo_df[wo_df["sector"].str.contains(sector, case=False, na=False)]
            wo_sector = wo_df.groupby("sector").agg(
                project_count=("deal_name", "count"),
                total_value=("amount_excl_gst", "sum"),
                total_billed=("billed_value_excl_gst", "sum"),
                total_collected=("collected_amount", "sum"),
            ).reset_index()
            result["work_orders_by_sector"] = wo_sector.to_dict("records")
        result["metric"] = "sector_performance"
        return result

    def operational_metrics(self) -> dict:
        wo = self._dp.get_work_orders()
        if wo.empty:
            return {"error": "No work order data available"}
        status_counts = wo["execution_status"].value_counts().to_dict()
        nature_counts = wo["nature_of_work"].value_counts().to_dict()
        billing_counts = wo["billing_status"].value_counts().to_dict()
        overdue = 0
        if "probable_end_date" in wo.columns:
            today = pd.Timestamp.now()
            past_due = wo[
                (wo["probable_end_date"] < today) & (wo["execution_status"] != "Completed")
            ]
            overdue = len(past_due)
        return {
            "metric": "operational_metrics",
            "total_projects": len(wo),
            "by_status": status_counts,
            "by_nature": nature_counts,
            "by_billing_status": billing_counts,
            "overdue_projects": overdue,
        }

    def top_deals(self, n: int = 5) -> dict:
        deals = self._dp.get_deals()
        if deals.empty:
            return {"error": "No deal data available"}
        df = deals.dropna(subset=["deal_value"]).nlargest(n, "deal_value")
        return {
            "metric": "top_deals",
            "deals": [
                {
                    "name": row["Deal Name"],
                    "value": round(row["deal_value"], 2),
                    "stage": row.get("deal_stage_clean", "N/A"),
                    "sector": row.get("sector_clean", "N/A"),
                    "status": row.get("Deal Status", "N/A"),
                }
                for _, row in df.iterrows()
            ],
        }

    def deal_conversion_funnel(self) -> dict:
        deals = self._dp.get_deals()
        if deals.empty:
            return {"error": "No deal data available"}
        stage_order = [
            "Lead Generated", "Sales Qualified", "Demo Done", "Feasibility",
            "Proposal Sent", "Negotiations", "Won", "Lost", "On Hold",
        ]
        funnel = []
        for stage in stage_order:
            count = len(deals[deals["deal_stage_clean"] == stage])
            value = deals.loc[deals["deal_stage_clean"] == stage, "deal_value"].sum()
            funnel.append({"stage": stage, "count": count, "value": round(value, 2)})
        return {"metric": "deal_conversion_funnel", "funnel": funnel}

    def quarterly_comparison(self, quarter: str = None) -> dict:
        deals = self._dp.get_deals()
        if deals.empty:
            return {"error": "No deal data available"}
        df = deals.copy()
        if "Tentative Close Date" in df.columns:
            df["quarter"] = df["Tentative Close Date"].dt.quarter
            df["year"] = df["Tentative Close Date"].dt.year
            quarterly = df.groupby(["year", "quarter"]).agg(
                deal_count=("Deal Name", "count"),
                total_value=("deal_value", "sum"),
                won_count=("Deal Status", lambda x: (x == "Won").sum()),
            ).reset_index()
            return {"metric": "quarterly_comparison", "data": quarterly.to_dict("records")}
        return {"metric": "quarterly_comparison", "data": [], "note": "No date data available"}

    def get_summary_for_agent(self) -> dict:
        return {
            "revenue": self.revenue_summary(),
            "pipeline": self.pipeline_health(),
            "sectors": self.sector_performance(),
            "operations": self.operational_metrics(),
            "top_deals": self.top_deals(5),
            "funnel": self.deal_conversion_funnel(),
        }


bi_engine = BIEngine()
