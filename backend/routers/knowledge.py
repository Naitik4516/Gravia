from typing import List, Literal, Optional, Dict, Any

from fastapi import APIRouter, File, Form, HTTPException, Query

from knowledge_manager import knowledge_manager, vector_db
import json

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/content")
async def list_content(
    limit: int = Query(20, ge=1, le=200),
    page: int = Query(1, ge=1),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query(None),
):
    try:
        data, total = knowledge_manager.list_contents(
            limit=limit, page=page, sort_by=sort_by, sort_order=sort_order
        )
        total_pages = (total + limit - 1) // limit if limit else 1
        return {
            "data": data,
            "meta": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_count": total,
            },
        }
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/{content_id}")
async def get_content_by_id(content_id: str):
    try:
        return knowledge_manager.get_content_by_id(content_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Content not found")
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_content(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    filter: Optional[str] = Query(None, description="Optional filter in JSON format")
):
    filter_dict = None
    if filter:
        try:
            filter_dict = json.loads(filter)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid filter format: {str(e)}")
    try:
        results = vector_db.search(query, limit=limit, filters=filter_dict)
        return {"query": query, "results": results}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/content")
async def create_content(
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tag: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    text_content: Optional[str] = Form(None),
    path: Optional[str] = File(None),
    topics: Optional[List[str]] = Form(None),
    chunking_strategy: Literal["semantic", "document"] = Form("semantic")
):
    try:
        created = await knowledge_manager.add_content(
            name,
            description,
            tag,
            path,
            url,
            text_content,
            topics,
            chunking_strategy=chunking_strategy
        )

        return created
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/content/{content_id}")
async def update_content(
    content_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tag: Optional[str] = Form(None),
):
    try:
        updated = knowledge_manager.update_content(content_id, name, description, tag)
        return updated
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Content not found")
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/content/{content_id}")
async def delete_content(content_id: str):
    try:
        deleted = knowledge_manager.delete_content(content_id)
        return deleted
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/content")
async def delete_all_content():
    try:
        count = knowledge_manager.delete_all()
        return {"deleted_count": count}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
