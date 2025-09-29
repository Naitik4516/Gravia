from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Union
from utils.data_handler import settings
import edge_tts
from schemas import SettingsCategory, SettingsItem


router = APIRouter(prefix="/settings", tags=["settings"])

# Pydantic models for request/response

class SettingsResponse(BaseModel):
    categories: List[SettingsCategory]

class SettingUpdateRequest(BaseModel):
    category: str
    key: str
    value: Union[str, int, float, bool, List[str]]

class SettingsCategoryUpdateRequest(BaseModel):
    category: str
    settings: List

class UserSettingsResponse(BaseModel):
    preferences: Dict[str, Any]
    conversation: Dict[str, Any]


@router.get("/category/{category_name}")
async def get_settings_by_category(category_name: str):
    """Get settings for a specific category (excluding integrations)"""
    if category_name not in settings.CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category_name}' not found"
        )

    return SettingsCategory(
        category=category_name,
        settings=[SettingsItem(**setting) for setting in settings.get_category(category_name)]
    )

@router.put("/update")
async def update_setting(request: SettingUpdateRequest):
    success = settings.set(request.key, request.value)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update setting"
        )
    
    return {"message": f"Setting '{request.key}' updated successfully", "key": request.key, "value": request.value}


@router.put("/update-category")
async def update_category(request: SettingsCategoryUpdateRequest):
    success = settings.set_category(request.category, request.settings)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )

    return {"message": f"Category '{request.category}' updated successfully"}


@router.get("/voices")
async def get_available_voices():
    """Get list of available voices"""
    try:
        voices = await edge_tts.list_voices()
        return {
            "voices": [
                {
                    "name": voice["Name"],
                    "short_name": voice["ShortName"],
                    "gender": voice["Gender"],
                    "locale": voice["Locale"]
                }
                for voice in voices
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching voices: {str(e)}")
