from fastapi import APIRouter, Query
from backend.services.data_processor import processor
from backend.services.monday_client import monday_client

router = APIRouter(prefix="/api", tags=["Boards"])


@router.get("/boards")
async def list_boards():
    try:
        boards = await monday_client.get_boards()
        return {"boards": boards}
    except Exception:
        wo = processor.get_work_orders()
        deals = processor.get_deals()
        return {
            "boards": [
                {"id": "local_work_orders", "name": "Work Orders (Local CSV)", "items_count": len(wo)},
                {"id": "local_deals", "name": "Deals (Local CSV)", "items_count": len(deals)},
            ],
            "note": "Using local CSV data (Monday.com API not configured)",
        }


@router.get("/boards/{board_id}/items")
async def get_board_items(board_id: str, limit: int = Query(100, ge=1, le=500)):
    if board_id == "local_work_orders":
        df = processor.get_work_orders()
        if df.empty:
            return {"items": [], "total": 0}
        items = df.head(limit).to_dict("records")
        return {"items": items, "total": len(df), "source": "local_csv"}
    elif board_id == "local_deals":
        df = processor.get_deals()
        if df.empty:
            return {"items": [], "total": 0}
        items = df.head(limit).to_dict("records")
        return {"items": items, "total": len(df), "source": "local_csv"}
    else:
        items = await monday_client.get_all_board_items(int(board_id))
        return {"items": items, "total": len(items), "source": "monday_api"}


@router.get("/data-quality")
async def data_quality():
    wo = processor.get_work_orders()
    deals = processor.get_deals()
    return {
        "work_orders": processor.data_quality_report(wo, "Work Orders"),
        "deals": processor.data_quality_report(deals, "Deals"),
    }
