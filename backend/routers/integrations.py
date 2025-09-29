from fastapi import APIRouter, HTTPException, status, Depends
from composio import Composio
import logging
from config import COMPOSIO_API_KEY
from utils.data_handler import user, integrations
import webbrowser
from notification_service import NotificationService

composio = None  

async def get_composio_client():
    global composio

    if not user.user_exists:
        logging.error("User does not exist.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found.")

    if not COMPOSIO_API_KEY:
        logging.error("Composio API key is not set.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Composio client not initialized.")
    try:
        composio = Composio(api_key=COMPOSIO_API_KEY)
    except Exception as e:
        logging.error(f"Failed to initialize Composio client: {e}")
        composio = None
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Composio client not initialized.")


router = APIRouter(prefix="/integrations", tags=["integrations"], dependencies=[Depends(get_composio_client)])


# base_frontend_url = "http://localhost:3000" # Replace with your actual frontend URL



@router.post("/connect/{toolkit_key}")
async def connect_integration(toolkit_key: str):
    config = integrations.get(toolkit_key)
    print("Config:", config)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Integration '{toolkit_key}' not found")
    auth_config_id = config["auth_id"]
    # callback_url = f"{base_frontend_url}/integrations/callback"

    try:
        connection_request = composio.connected_accounts.initiate(
            user_id=user.get("id"),
            auth_config_id=auth_config_id,
            # callback_url=callback_url,
            config={"auth_scheme": "OAUTH2"},
        )
    except Exception as e:
        logging.error(f"Failed to initiate connection for {toolkit_key}: {e}")
        await NotificationService.send_default("Integration Connection Error", f"Failed to initiate connection for {toolkit_key}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate connection with Composio.")

    webbrowser.open(connection_request.redirect_url)

    connected_account = connection_request.wait_for_connection()

    if connected_account:
        await NotificationService.send_default("Integration Connected", f"Successfully connected {toolkit_key}.")
    else:
        await NotificationService.send_default("Integration Connection Failed", f"Failed to connect {toolkit_key}.")

    return {"message": "Connection process completed."}


@router.post("/disconnect/{toolkit_key}")
async def disconnect_integration(toolkit_key: str):
    toolkit = integrations.get(toolkit_key)
    if not toolkit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Integration '{toolkit_key}' not found")
    else:
        auth_config_id = toolkit.get("auth_id")

    try:
        if not toolkit.get("value", False):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No active connection found for {toolkit_key}.")

        composio.connected_accounts.delete(auth_config_id)
        await NotificationService.send_default("Integration Disconnected", f"Successfully disconnected {toolkit_key}.")
        
    except Exception as e:
        logging.error(f"Failed to disconnect {toolkit_key}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to disconnect integration.")

    return {"message": f"Successfully disconnected {toolkit_key}"}
