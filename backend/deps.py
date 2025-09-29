from utils.data_handler import user
from fastapi import  HTTPException, status

def user_exists():
    if not user.user_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found"
        )
    return True