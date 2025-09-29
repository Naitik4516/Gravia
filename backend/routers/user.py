import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, status
from pydantic import BaseModel

from schemas import Profile
from utils.data_handler import user

router = APIRouter(prefix="/user", tags=["user"])


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str


# # Utility functions
# def hash_password(password: str) -> str:
#     """Simple password hashing using SHA-256"""
#     return hashlib.sha256(password.encode()).hexdigest()

# def verify_password(password: str, hashed_password: str) -> bool:
#     """Verify password against hash"""
#     return hash_password(password) == hashed_password


@router.post("/signup", response_model=UserResponse)
async def signup(name: Annotated[str, Form()], email: Annotated[str, Form()]):
    """Create a new user account"""
    # Check if user already exists
    if user.profile and user.profile.email == email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user
    current_time = datetime.now().isoformat()
    user_id = str(uuid.uuid4())

    new_user_data = {
        "id": user_id,
        "profile": {
            "name": name,
            "email": email,
            "created_at": current_time,
            "additional_info": {}
        },
    }
    
    user.save_data(new_user_data)
    user.data = user.load_data()
    
    return UserResponse(
        id=user_id,
        name=name,
        email=email,
        created_at=current_time,
    )


@router.get("/profile", response_model=Profile)
async def get_profile():
    """Get user profile information"""
    if not user.user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    profile = user.profile

    return profile


@router.put("/profile", response_model=Profile)
async def update_profile(request: Profile):
    """Update user profile information"""
    if user.user_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    success = user.save_profile(request)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

    return user.profile

