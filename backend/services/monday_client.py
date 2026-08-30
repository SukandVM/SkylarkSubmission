import httpx
import logging
from typing import Optional
from backend.config import settings

logger = logging.getLogger(__name__)

MONDAY_HEADERS = {
    "Content-Type": "application/json",
    "API-Version": "2024-10",
}


class MondayClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.MONDAY_API_KEY
        self.api_url = settings.MONDAY_API_URL
        self.headers = {**MONDAY_HEADERS, "Authorization": self.api_key}

    async def _execute_query(self, query: str, variables: dict = None) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.api_url, json=payload, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                logger.error("Monday API errors: %s", data["errors"])
            return data

    async def get_boards(self) -> list[dict]:
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
        data = await self._execute_query(query)
        return data.get("data", {}).get("boards", [])

    async def get_board_items(self, board_id: int, limit: int = 500, page: int = 1) -> dict:
        query = """
        query ($boardId: [ID!]!, $limit: Int!, $page: Int!) {
            boards(ids: $boardId) {
                items_page(limit: $limit, page: $page) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            title
                            text
                            value
                            type
                        }
                    }
                }
            }
        }
        """
        data = await self._execute_query(query, {"boardId": [str(board_id)], "limit": limit, "page": page})
        boards = data.get("data", {}).get("boards", [])
        if boards:
            return boards[0].get("items_page", {})
        return {"items": [], "cursor": None}

    async def get_all_board_items(self, board_id: int) -> list[dict]:
        all_items = []
        page = 1
        while True:
            result = await self.get_board_items(board_id, limit=500, page=page)
            items = result.get("items", [])
            all_items.extend(items)
            if len(items) < 500:
                break
            page += 1
        return all_items

    async def search_items(self, board_id: int, column_id: str, search_value: str) -> list[dict]:
        query = """
        query ($boardId: [ID!]!, $columnId: String!, $searchValue: String!) {
            items_page(limit: 500, board_ids: $boardId, rule: {
                column_id: $columnId,
                compare_value: [$searchValue],
                operator: contains
            }) {
                items {
                    id
                    name
                    column_values { id title text value type }
                }
            }
        }
        """
        data = await self._execute_query(query, {
            "boardId": [str(board_id)],
            "columnId": column_id,
            "searchValue": search_value,
        })
        return data.get("data", {}).get("items_page", {}).get("items", [])


monday_client = MondayClient()
