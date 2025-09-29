from utils.composio_agno import AgnoProvider
from composio import Composio
from utils.data_handler import user, integrations
from config import COMPOSIO_API_KEY

cp = Composio(provider=AgnoProvider(api_key=COMPOSIO_API_KEY), allow_tracking=False)


toolkits = []

def refresh_toolkits():
    """Refresh the composio toolkits list based on current integrations."""
    global toolkits
    toolkits.clear()
    
    # Always include these base toolkits
    toolkits += cp.tools.get(user_id=user.get("id"), toolkits=["COMPOSIO_SEARCH"])
    
    toolkits += cp.tools.get(user_id=user.get("id"), tools= [
        "GEMINI_GENERATE_IMAGE",
        "GEMINI_GENERATE_VIDEOS",
        "GEMINI_GET_VIDEOS_OPERATION",
        "GEMINI_WAIT_FOR_VIDEO"
    ])
    
    # Add toolkits based on enabled integrations
    for toolkit, toolkit_tools_list in toolkit_tools.items():
        integration = integrations.get(toolkit)
        if integration is not None and integration.get("value"):
            tools = cp.tools.get(user_id=user.get("id"), tools=toolkit_tools_list)
            if tools:
                toolkits += tools


toolkit_tools = {
    "GMAIL": [
        "GMAIL_CREATE_EMAIL_DRAFT",
        "GMAIL_FETCH_EMAILS",
        "GMAIL_GET_CONTACTS",
        "GMAIL_REPLY_TO_THREAD",
        "GMAIL_SEARCH_PEOPLE",
        "GMAIL_SEND_DRAFT",
        "GMAIL_SEND_EMAIL",
        "GMAIL_GET_PEOPLE",
        "GMAIL_MOVE_TO_TRASH",
    ],
    "GOOGLE_DRIVE": [
        "GOOGLEDRIVE_CREATE_FILE",
        "GOOGLEDRIVE_CREATE_FOLDER",
        "GOOGLEDRIVE_DOWNLOAD_FILE",
        "GOOGLEDRIVE_LIST_FILES",
        "GOOGLEDRIVE_MOVE_FILE",
        "GOOGLEDRIVE_UPLOAD_FILE",
        "GOOGLEDRIVE_ADD_FILE_SHARING_PREFERENCE",
        "GOOGLEDRIVE_COPY_FILE",
        "GOOGLEDRIVE_CREATE_FILE_FROM_TEXT",
        "GOOGLEDRIVE_EDIT_FILE",
        "GOOGLEDRIVE_FIND_FILE",
        "GOOGLEDRIVE_FIND_FOLDER",
    ],
    "GOOGLE_CALENDAR": [
        "GOOGLECALENDAR_CREATE_EVENT",
        "GOOGLECALENDAR_EVENTS_LIST",
        "GOOGLECALENDAR_FIND_EVENT",
        "GOOGLECALENDAR_FREE_BUSY_QUERY",
        "GOOGLECALENDAR_QUICK_ADD",
        "GOOGLECALENDAR_UPDATE_EVENT",
        "GOOGLECALENDAR_LIST_CALENDARS",
        "GOOGLECALENDAR_FIND_FREE_SLOTS",
        "GOOGLECALENDAR_GET_CALENDAR",
    ],
    "GOOGLE_MAPS": [
        "GOOGLE_MAPS_DISTANCE_MATRIX_API",
        "GOOGLE_MAPS_GEOCODING_API",
        "GOOGLE_MAPS_TEXT_SEARCH",
        "GOOGLE_MAPS_GET_DIRECTION",
        "GOOGLE_MAPS_GET_ROUTE",
        "GOOGLE_MAPS_NEARBY_SEARCH",
    ],
    "ONE_DRIVE": [
        "ONE_DRIVE_CREATE_TEXT_FILE",
        "ONE_DRIVE_ONEDRIVE_CREATE_FOLDER",
        "ONE_DRIVE_DOWNLOAD_FILE",
        "ONE_DRIVE_ONEDRIVE_LIST_ITEMS",
        "ONE_DRIVE_MOVE_ITEM",
        "ONE_DRIVE_ONEDRIVE_UPLOAD_FILE",
        "ONE_DRIVE_ONEDRIVE_FIND_FILE",
        "ONE_DRIVE_ONEDRIVE_FIND_FOLDER",
        "ONE_DRIVE_SEARCH_ITEMS",
        "ONE_DRIVE_GET_ITEM",
    ],
    "NOTION": [
        "NOTION_ADD_PAGE_CONTENT",
        "NOTION_CREATE_NOTION_PAGE",
        "NOTION_FETCH_BLOCK_CONTENTS",
        "NOTION_FETCH_DATABASE",
        "NOTION_INSERT_ROW_DATABASE",
        "NOTION_QUERY_DATABASE",
        "NOTION_SEARCH_NOTION_PAGE",
        "NOTION_UPDATE_PAGE",
        "NOTION_APPEND_BLOCK_CHILDREN",
    ],
    "INSTAGRAM": [
        "INSTAGRAM_CREATE_POST",
        "INSTAGRAM_CREATE_CAROUSEL_CONTAINER",
        "INSTAGRAM_CREATE_MEDIA_CONTAINER",
        "INSTAGRAM_SEND_TEXT_MESSAGE",
        "INSTAGRAM_SEND_IMAGE",
        "INSTAGRAM_GET_CONVERSATION",
        "INSTAGRAM_LIST_ALL_CONVERSATIONS",
        "INSTAGRAM_LIST_ALL_MESSAGES",
        "INSTAGRAM_MARK_SEEN",
        "INSTAGRAM_REPLY_TO_COMMENT",
    ],

    "TWITTER": [
        "TWITTER_CREATION_OF_A_POST",
        "TWITTER_POST_DELETE_BY_POST_ID",
        "TWITTER_SEND_A_NEW_MESSAGE_TO_A_USER",
        "TWITTER_CREATE_A_NEW_DM_CONVERSATION",
        "TWITTER_SEND_A_NEW_MESSAGE_TO_A_DM_CONVERSATION",
        "TWITTER_GET_RECENT_DM_EVENTS",
        "TWITTER_RETRIEVE_DM_CONVERSATION_EVENTS",
        "TWITTER_GET_DM_EVENTS_BY_ID",
        "TWITTER_RETWEET_POST",
        "TWITTER_UNRETWEET_POST",
        "TWITTER_USER_LIKE_POST",
        "TWITTER_UNLIKE_POST",
        "TWITTER_RECENT_SEARCH",
        "TWITTER_USER_LOOKUP_BY_USERNAME",
        "TWITTER_USER_LOOKUP_ME",
        "TWITTER_USER_HOME_TIMELINE_BY_USER_ID",
        "TWITTER_FOLLOW_USER",
        "TWITTER_UNFOLLOW_USER",
    ],

    "REDDIT": [
        "REDDIT_CREATE_REDDIT_POST",
        "REDDIT_POST_REDDIT_COMMENT",
        "REDDIT_EDIT_REDDIT_COMMENT_OR_POST",
        "REDDIT_DELETE_REDDIT_COMMENT",
        "REDDIT_DELETE_REDDIT_POST",
        "REDDIT_SEARCH_ACROSS_SUBREDDITS",
        "REDDIT_RETRIEVE_REDDIT_POST",
        "REDDIT_RETRIEVE_POST_COMMENTS",
    ],

    "FACEBOOK": [
        "FACEBOOK_CREATE_POST",
        "FACEBOOK_CREATE_PHOTO_POST",
        "FACEBOOK_CREATE_VIDEO_POST",
        "FACEBOOK_CREATE_COMMENT",
        "FACEBOOK_UPDATE_COMMENT",
        "FACEBOOK_DELETE_COMMENT",
        "FACEBOOK_DELETE_POST",
        "FACEBOOK_UPDATE_POST",
        "FACEBOOK_LIKE_POST_OR_COMMENT",
        "FACEBOOK_UNLIKE_POST_OR_COMMENT",
        "FACEBOOK_ADD_REACTION",
        "FACEBOOK_SEND_MESSAGE",
        "FACEBOOK_SEND_MEDIA_MESSAGE",
        "FACEBOOK_MARK_MESSAGE_SEEN",
        "FACEBOOK_GET_CONVERSATION_MESSAGES",
        "FACEBOOK_GET_MESSAGE_DETAILS",
        "FACEBOOK_GET_POST",
        "FACEBOOK_GET_COMMENTS",
        "FACEBOOK_GET_COMMENT",
        "FACEBOOK_GET_POST_REACTIONS",
    ],
}

# Initialize toolkits on import
refresh_toolkits()

print(toolkits)