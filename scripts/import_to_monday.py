import pandas as pd
import httpx
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MONDAY_API_URL = "https://api.monday.com/v2"
WORK_ORDER_BOARD_NAME = "Skylark Work Orders"
DEALS_BOARD_NAME = "Skylark Deals"


def get_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": api_key,
        "API-Version": "2024-10",
    }


def execute_query(client: httpx.Client, query: str, variables: dict = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = client.post(MONDAY_API_URL, json=payload)
    resp.raise_for_status()
    return resp.json()


def create_board(client: httpx.Client, name: str, columns: list[dict]) -> str:
    cols = [{"title": c["title"], "kind": c.get("kind", "text")} for c in columns]
    query = """
    mutation ($name: String!, $columns: [Column!]!) {
        create_board(board_name: $name, columns: $columns, board_kind: public) { id }
    }
    """
    result = execute_query(client, query, {"name": name, "columns": cols})
    board_id = result["data"]["create_board"]["id"]
    print(f"Created board '{name}' with ID: {board_id}")
    return board_id


def create_item(client: httpx.Client, board_id: str, name: str, column_values: dict) -> str:
    col_vals = json.dumps(column_values)
    query = """
    mutation ($boardId: ID!, $name: String!, $columnValues: JSON!) {
        create_item(board_id: $boardId, item_name: $name, column_values: $columnValues) { id }
    }
    """
    result = execute_query(client, query, {
        "boardId": board_id,
        "name": name,
        "columnValues": col_vals,
    })
    return result["data"]["create_item"]["id"]


def import_work_orders(client: httpx.Client, api_key: str):
    df = pd.read_csv(os.path.join("data", "work_orders.csv"))
    print(f"Importing {len(df)} work orders...")

    columns = [
        {"title": "Customer", "kind": "text"},
        {"title": "Serial #", "kind": "text"},
        {"title": "Nature of Work", "kind": "status"},
        {"title": "Execution Status", "kind": "status"},
        {"title": "Sector", "kind": "status"},
        {"title": "Type of Work", "kind": "text"},
        {"title": "Amount (Excl GST)", "kind": "number"},
        {"title": "Billed Value", "kind": "number"},
        {"title": "Collected Amount", "kind": "number"},
        {"title": "WO Status", "kind": "status"},
        {"title": "Billing Status", "kind": "status"},
        {"title": "Document Type", "kind": "status"},
    ]

    board_id = create_board(client, WORK_ORDER_BOARD_NAME, columns)

    imported = 0
    for _, row in df.iterrows():
        try:
            name = str(row.iloc[0]) if pd.notna(row.iloc[0]) else "Unnamed"
            col_values = {}
            if pd.notna(row.iloc[1]):
                col_values["{\"columns\":[{\"id\":")] = str(row.iloc[1])
            create_item(client, board_id, name, {
                "customer": str(row.iloc[1]) if pd.notna(row.iloc[1]) else "",
                "serial": str(row.iloc[2]) if pd.notna(row.iloc[2]) else "",
                "nature": str(row.iloc[3]) if pd.notna(row.iloc[3]) else "",
                "status": str(row.iloc[5]) if pd.notna(row.iloc[5]) else "",
                "sector": str(row.iloc[12]) if pd.notna(row.iloc[12]) else "",
                "amount": float(row.iloc[17]) if pd.notna(row.iloc[17]) else 0,
            })
            imported += 1
            if imported % 10 == 0:
                print(f"  Imported {imported}/{len(df)}...")
                time.sleep(1)
        except Exception as e:
            print(f"  Error importing row: {e}")
            continue

    print(f"Imported {imported} work orders to board {board_id}")
    return board_id


def import_deals(client: httpx.Client, api_key: str):
    df = pd.read_csv(os.path.join("data", "deals.csv"))
    print(f"Importing {len(df)} deals...")

    columns = [
        {"title": "Owner", "kind": "text"},
        {"title": "Client Code", "kind": "text"},
        {"title": "Deal Status", "kind": "status"},
        {"title": "Close Date", "kind": "date"},
        {"title": "Closure Probability", "kind": "status"},
        {"title": "Deal Value", "kind": "number"},
        {"title": "Tentative Close Date", "kind": "date"},
        {"title": "Deal Stage", "kind": "status"},
        {"title": "Product", "kind": "text"},
        {"title": "Sector", "kind": "status"},
        {"title": "Created Date", "kind": "date"},
    ]

    board_id = create_board(client, DEALS_BOARD_NAME, columns)

    imported = 0
    for _, row in df.iterrows():
        try:
            name = str(row["Deal Name"]) if pd.notna(row["Deal Name"]) else "Unnamed"
            create_item(client, board_id, name, {
                "owner": str(row["Owner code"]) if pd.notna(row["Owner code"]) else "",
                "client": str(row["Client Code"]) if pd.notna(row["Client Code"]) else "",
                "status": str(row["Deal Status"]) if pd.notna(row["Deal Status"]) else "",
                "probability": str(row["Closure Probability"]) if pd.notna(row["Closure Probability"]) else "",
                "value": float(row["Masked Deal value"]) if pd.notna(row["Masked Deal value"]) else 0,
                "stage": str(row["Deal Stage"]) if pd.notna(row["Deal Stage"]) else "",
                "product": str(row["Product deal"]) if pd.notna(row["Product deal"]) else "",
                "sector": str(row["Sector/service"]) if pd.notna(row["Sector/service"]) else "",
            })
            imported += 1
            if imported % 10 == 0:
                print(f"  Imported {imported}/{len(df)}...")
                time.sleep(1)
        except Exception as e:
            print(f"  Error importing row: {e}")
            continue

    print(f"Imported {imported} deals to board {board_id}")
    return board_id


def main():
    api_key = os.environ.get("MONDAY_API_KEY", "")
    if not api_key:
        print("ERROR: Set MONDAY_API_KEY environment variable")
        print("  export MONDAY_API_KEY=your_api_key_here")
        sys.exit(1)

    client = httpx.Client(
        timeout=30,
        headers=get_headers(api_key),
    )

    print("=== Skylark Drones Monday.com Import ===\n")
    wo_board = import_work_orders(client, api_key)
    print()
    deals_board = import_deals(client, api_key)

    print(f"\n=== Import Complete ===")
    print(f"Work Orders Board ID: {wo_board}")
    print(f"Deals Board ID: {deals_board}")
    print(f"\nUpdate backend/services/monday_client.py with these board IDs")


if __name__ == "__main__":
    main()
