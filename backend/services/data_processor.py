import pandas as pd
import re
import os
import logging
from datetime import datetime
from typing import Optional
from backend.config import settings

logger = logging.getLogger(__name__)

SECTOR_CANONICAL = {
    "mining": "Mining",
    "powerline": "Powerline",
    "renewables": "Renewables",
    "railways": "Railways",
    "construction": "Construction",
    "others": "Others",
    "tender": "Tender",
    "dsp": "DSP",
    "security and surveillance": "Security & Surveillance",
    "security": "Security & Surveillance",
    "aviation": "Aviation",
    "manufacturing": "Manufacturing",
    "oil & gas": "Oil & Gas",
    "oil and gas": "Oil & Gas",
    "energy": "Energy",
    "solar": "Solar",
    "wind": "Wind",
}

STATUS_CANONICAL = {
    "completed": "Completed",
    "not started": "Not Started",
    "ongoing": "Ongoing",
    "executed until current month": "Ongoing",
    "partial completed": "Partial Completed",
    "pause / struck": "Paused",
    "paused": "Paused",
    "stuck": "Paused",
    "details pending from client": "Pending",
    "pending": "Pending",
}

BILLING_STATUS_CANONICAL = {
    "billed": "Billed",
    "billed": "Billed",
    "partially billed": "Partially Billed",
    "not billable": "Not Billable",
    "update required": "Pending",
    "stuck": "Paused",
}

DEAL_STAGE_CANONICAL = {
    "a. lead generated": "Lead Generated",
    "b. sales qualified leads": "Sales Qualified",
    "c. demo done": "Demo Done",
    "d. feasibility": "Feasibility",
    "e. proposal/commercials sent": "Proposal Sent",
    "f. negotiations": "Negotiations",
    "g. project won": "Won",
    "h. work order received": "WO Received",
    "i. poc": "POC",
    "j. invoice sent": "Invoice Sent",
    "k. amount accrued": "Accrued",
    "l. project lost": "Lost",
    "m. projects on hold": "On Hold",
    "n. not relevant at the moment": "Not Relevant",
    "o. not relevant at all": "Not Relevant",
    "project completed": "Completed",
}

COLUMNS_TO_DROP_WO = [
    "expected_billing_month",
    "actual_collection_month",
    "collection_status",
    "collection_date",
]


class DataProcessor:
    def __init__(self):
        self.work_orders: Optional[pd.DataFrame] = None
        self.deals: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self):
        wo_path = os.path.join(settings.DATA_DIR, "work_orders.csv")
        deals_path = os.path.join(settings.DATA_DIR, "deals.csv")
        try:
            self.work_orders = pd.read_csv(wo_path)
            self._clean_work_orders()
            logger.info("Loaded %d work orders", len(self.work_orders))
        except Exception as e:
            logger.error("Failed to load work orders: %s", e)
            self.work_orders = pd.DataFrame()
        try:
            self.deals = pd.read_csv(deals_path)
            self._clean_deals()
            logger.info("Loaded %d deals", len(self.deals))
        except Exception as e:
            logger.error("Failed to load deals: %s", e)
            self.deals = pd.DataFrame()

    def _clean_work_orders(self):
        df = self.work_orders
        rename_map = {
            df.columns[0]: "deal_name",
            df.columns[1]: "customer",
            df.columns[2]: "serial_number",
            df.columns[3]: "nature_of_work",
            df.columns[4]: "last_executed_month",
            df.columns[5]: "execution_status",
            df.columns[6]: "data_delivery_date",
            df.columns[7]: "date_of_po_loi",
            df.columns[8]: "document_type",
            df.columns[9]: "probable_start_date",
            df.columns[10]: "probable_end_date",
            df.columns[11]: "bd_personnel",
            df.columns[12]: "sector",
            df.columns[13]: "type_of_work",
            df.columns[14]: "skylark_platform",
            df.columns[15]: "last_invoice_date",
            df.columns[16]: "latest_invoice_no",
            df.columns[17]: "amount_excl_gst",
            df.columns[18]: "amount_incl_gst",
            df.columns[19]: "billed_value_excl_gst",
            df.columns[20]: "billed_value_incl_gst",
            df.columns[21]: "collected_amount",
            df.columns[22]: "amount_to_be_billed_excl",
            df.columns[23]: "amount_to_be_billed_incl",
            df.columns[24]: "amount_receivable",
            df.columns[25]: "ar_priority",
            df.columns[26]: "quantity_by_ops",
            df.columns[27]: "quantity_per_po",
            df.columns[28]: "quantity_billed",
            df.columns[29]: "balance_quantity",
            df.columns[30]: "invoice_status",
            df.columns[31]: "expected_billing_month",
            df.columns[32]: "actual_billing_month",
            df.columns[33]: "actual_collection_month",
            df.columns[34]: "wo_status",
            df.columns[35]: "collection_status",
            df.columns[36]: "collection_date",
            df.columns[37]: "billing_status",
        }
        df.rename(columns=rename_map, inplace=True)

        cols_to_drop = [c for c in COLUMNS_TO_DROP_WO if c in df.columns]
        df.drop(columns=cols_to_drop, inplace=True)
        logger.info("Dropped %d 100%%-null columns from work orders: %s", len(cols_to_drop), cols_to_drop)

        df["sector"] = df["sector"].apply(lambda x: self._normalize_sector(x) if pd.notna(x) else x)
        df["execution_status"] = df["execution_status"].apply(
            lambda x: self._normalize_status(x) if pd.notna(x) else x
        )
        if "billing_status" in df.columns:
            df["billing_status"] = df["billing_status"].apply(
                lambda x: self._normalize_billing_status(x) if pd.notna(x) else x
            )

        for col in ["amount_excl_gst", "amount_incl_gst", "billed_value_excl_gst",
                      "billed_value_incl_gst", "collected_amount", "amount_to_be_billed_excl",
                      "amount_to_be_billed_incl", "amount_receivable"]:
            if col in df.columns:
                df[col] = df[col].apply(self._parse_currency)

        for col in ["data_delivery_date", "date_of_po_loi", "probable_start_date",
                      "probable_end_date", "last_invoice_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        if "quantity_by_ops" in df.columns:
            df["quantity_by_ops"] = df["quantity_by_ops"].apply(self._parse_quantity)

        df.dropna(subset=["deal_name"], inplace=True)

    def _clean_deals(self):
        df = self.deals

        header_values = ["Deal Name", "Deal Status", "Deal Stage", "Close Date (A)",
                         "Closure Probability", "Sector/service", "Product deal",
                         "Owner code", "Client Code", "Masked Deal value",
                         "Tentative Close Date", "Created Date"]
        for col in df.columns:
            if col in df.columns:
                df = df[df[col].astype(str) != col]

        df["sector_clean"] = df["Sector/service"].apply(
            lambda x: self._normalize_sector(x) if pd.notna(x) else x
        )
        df["deal_stage_clean"] = df["Deal Stage"].apply(
            lambda x: self._normalize_deal_stage(x) if pd.notna(x) else x
        )
        df["deal_value"] = df["Masked Deal value"].apply(self._parse_currency)

        for col in ["Close Date (A)", "Tentative Close Date", "Created Date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        df.dropna(subset=["Deal Name"], inplace=True)
        df = df[df["Deal Name"] != "Deal Name"]
        df = df[df["Deal Status"] != "Deal Status"]
        df = df[df["Deal Stage"] != "Deal Stage"]

        df["_completeness"] = df.notna().sum(axis=1)
        df = df.sort_values("_completeness", ascending=False).drop_duplicates(
            subset=["Deal Name", "Client Code"], keep="first"
        )
        df.drop(columns=["_completeness"], inplace=True)

        self.deals = df

    @staticmethod
    def _normalize_sector(value: str) -> str:
        if not isinstance(value, str):
            return str(value)
        cleaned = value.strip().lower()
        return SECTOR_CANONICAL.get(cleaned, value.strip().title())

    @staticmethod
    def _normalize_status(value: str) -> str:
        if not isinstance(value, str):
            return str(value)
        cleaned = value.strip().lower()
        return STATUS_CANONICAL.get(cleaned, value.strip())

    @staticmethod
    def _normalize_billing_status(value: str) -> str:
        if not isinstance(value, str):
            return str(value)
        cleaned = value.strip().lower()
        return BILLING_STATUS_CANONICAL.get(cleaned, value.strip())

    @staticmethod
    def _normalize_deal_stage(value: str) -> str:
        if not isinstance(value, str):
            return str(value)
        cleaned = value.strip().lower()
        return DEAL_STAGE_CANONICAL.get(cleaned, value.strip())

    @staticmethod
    def _parse_currency(value) -> Optional[float]:
        if pd.isna(value) or value == "" or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        s = re.sub(r"[₹$,\s]", "", s)
        s = re.sub(r"[^0-9.\-]", "", s)
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _parse_quantity(value) -> Optional[float]:
        if pd.isna(value) or value == "" or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        s = re.sub(r"[^0-9.\-]", "", s)
        try:
            return float(s) if s else None
        except ValueError:
            return None

    def get_work_orders(self) -> pd.DataFrame:
        return self.work_orders.copy() if self.work_orders is not None else pd.DataFrame()

    def get_deals(self) -> pd.DataFrame:
        return self.deals.copy() if self.deals is not None else pd.DataFrame()

    def data_quality_report(self, df: pd.DataFrame, board_name: str) -> dict:
        if df.empty:
            return {"board": board_name, "total_rows": 0, "columns": [], "null_summary": {}, "issues": ["No data loaded"]}
        total = len(df)
        null_summary = {}
        issues = []
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            pct = round(null_count / total * 100, 1)
            null_summary[col] = {"null_count": null_count, "null_pct": pct}
            if pct >= 90:
                issues.append(f"Column '{col}' has {pct}% missing values (critical)")
            elif pct >= 70:
                issues.append(f"Column '{col}' has {pct}% missing values (data gap)")
            elif pct >= 50:
                issues.append(f"Column '{col}' has {pct}% missing values (partial)")
        return {
            "board": board_name,
            "total_rows": total,
            "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
            "null_summary": null_summary,
            "issues": issues,
        }

    def reload_data(self):
        self._load_data()


processor = DataProcessor()
