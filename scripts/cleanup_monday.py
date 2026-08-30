import httpx
import os
import sys
import json
import time
from dotenv import load_dotenv

load_dotenv()

MONDAY_API_URL = "https://api.monday.com/v2"
API_KEY = os.environ.get("MONDAY_API_KEY", "")

if not API_KEY:
    print("ERROR: MONDAY_API_KEY not set in .env")
    sys.exit(1)

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": API_KEY,
    "API-Version": "2024-10",
}


def execute_query(query: str, variables: dict = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = httpx.post(MONDAY_API_URL, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        print(f"  API Errors: {data['errors']}")
    return data


def get_boards():
    query = """
    query {
        boards(limit: 50) {
            id
            name
            items_count
            columns { id title type }
        }
    }
    """
    data = execute_query(query)
    return data.get("data", {}).get("boards", [])


def get_board_items(board_id: str, limit: int = 500, cursor: str = None) -> dict:
    if cursor:
        query = """
        query ($boardId: [ID!]!, $limit: Int!, $cursor: String!) {
            boards(ids: $boardId) {
                items_page(limit: $limit, cursor: $cursor) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            type
                        }
                    }
                }
            }
        }
        """
        data = execute_query(query, {"boardId": [board_id], "limit": limit, "cursor": cursor})
    else:
        query = """
        query ($boardId: [ID!]!, $limit: Int!) {
            boards(ids: $boardId) {
                items_page(limit: $limit) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            type
                        }
                    }
                }
            }
        }
        """
        data = execute_query(query, {"boardId": [board_id], "limit": limit})
    boards = data.get("data", {}).get("boards", [])
    if boards:
        return boards[0].get("items_page", {})
    return {"items": [], "cursor": None}


def get_all_items(board_id: str) -> list:
    all_items = []
    cursor = None
    while True:
        result = get_board_items(board_id, limit=500, cursor=cursor)
        items = result.get("items", [])
        all_items.extend(items)
        cursor = result.get("cursor")
        if not cursor or len(items) < 500:
            break
        time.sleep(0.5)
    return all_items


def delete_item(item_id: str) -> bool:
    query = """
    mutation ($itemId: [ID!]!) {
        delete_items(item_ids: $itemId) { ids }
    }
    """
    try:
        execute_query(query, {"itemId": [item_id]})
        return True
    except Exception as e:
        print(f"  Failed to delete item {item_id}: {e}")
        return False


def change_column_value(item_id: str, board_id: str, column_id: str, value: str) -> bool:
    query = """
    mutation ($itemId: ID!, $boardId: ID!, $columnId: String!, $value: JSON!) {
        change_column_value(item_id: $itemId, board_id: $boardId, column_id: $columnId, value: $value) {
            id
        }
    }
    """
    try:
        col_value = json.dumps({"label": value})
        execute_query(query, {
            "itemId": item_id,
            "boardId": board_id,
            "columnId": column_id,
            "value": col_value,
        })
        return True
    except Exception as e:
        print(f"  Failed to update item {item_id}: {e}")
        return False


def find_work_orders_board(boards: list) -> dict:
    for b in boards:
        name = b["name"].lower().replace(" ", "")
        if "workorder" in name or "work_order" in name:
            return b
    for b in boards:
        name = b["name"].lower()
        if "work order" in name or "skylark work" in name:
            return b
    return None


def find_deals_board(boards: list) -> dict:
    for b in boards:
        name = b["name"].lower()
        if "deal" in name or "skylark deal" in name:
            return b
    return None


def cleanup_work_orders(board: dict):
    print(f"\n--- Cleaning Work Orders Board: {board['name']} (ID: {board['id']}) ---")
    items = get_all_items(board["id"])
    print(f"  Found {len(items)} items")

    billing_col = None
    for col in board.get("columns", []):
        if "billing" in col["title"].lower() and "status" in col["title"].lower():
            billing_col = col["id"]
            break

    updated = 0
    for item in items:
        for cv in item.get("column_values", []):
            if cv["id"] == billing_col and cv["text"]:
                if cv["text"].strip() == "BIlled":
                    print(f"  Fixing 'BIlled' -> 'Billed' in item '{item['name']}'")
                    change_column_value(item["id"], board["id"], billing_col, "Billed")
                    updated += 1
                    time.sleep(0.3)

    print(f"  Updated {updated} items in Work Orders board")


def cleanup_deals(board: dict):
    print(f"\n--- Cleaning Deals Board: {board['name']} (ID: {board['id']}) ---")
    items = get_all_items(board["id"])
    print(f"  Found {len(items)} items")

    HEADER_ARTIFACTS = [
        "Deal Name", "Deal Status", "Deal Stage", "Close Date (A)",
        "Closure Probability", "Sector/service", "Product deal",
        "Owner code", "Client Code", "Masked Deal value",
        "Tentative Close Date", "Created Date",
    ]

    deleted = 0
    for item in items:
        if item["name"] in HEADER_ARTIFACTS:
            print(f"  Deleting header artifact: '{item['name']}' (ID: {item['id']})")
            delete_item(item["id"])
            deleted += 1
            time.sleep(0.3)

    print(f"  Deleted {deleted} header-artifact items from Deals board")


def main():
    print("=== Monday.com Data Cleanup ===\n")

    boards = get_boards()
    print(f"Found {len(boards)} boards:")
    for b in boards:
        print(f"  - {b['name']} (ID: {b['id']}, {b['items_count']} items)")

    wo_board = find_work_orders_board(boards)
    deals_board = find_deals_board(boards)

    if wo_board:
        cleanup_work_orders(wo_board)
    else:
        print("\nWARNING: Work Orders board not found. Skipping.")

    if deals_board:
        cleanup_deals(deals_board)
    else:
        print("\nWARNING: Deals board not found. Skipping.")

    print("\n=== Cleanup Complete ===")


if __name__ == "__main__":
    main()
