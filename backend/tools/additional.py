from agno.tools import Toolkit, tool
from agno.tools.function import ToolResult
from agno.media import Image
import httpx
from mss.windows import MSS as mss
import os
from tools.desktop.tools import file_explorer

api_key = "0972f803392142ada89165126242707"

class WeatherToolkit(Toolkit):
    def __init__(self):
        super().__init__(
            name="WeatherToolkit",
            tools=[
                self.fetch_current_weather,
                self.fetch_forecast
            ]
        )

    async def fetch_current_weather(self, location: str, aqi: bool = False) -> dict:
        """Fetch the current weather for a specific location."""
        
        url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={location}&aqi={'yes' if aqi else 'no'}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def fetch_forecast(self, location: str, days: int = 1, aqi: bool = False, fields = "") -> list:
        """Fetch the weather forecast for a specific location for a specific number of days.        
        Args:
            location: Location to get forecast for
            days: Number of days to forecast
            aqi: Include air quality index
            fields (optional, recommended when data is large): List of fields to include (separated by commas, eg. "temperature,precipitation"). Options: 'temperature', 'precipitation', 'condition', 'astro', 'wind', 'visibility', 'humidity'
        """
        url = f"https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days={days}&aqi={'yes' if aqi else 'no'}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            forecast_days = data.get("forecast", {}).get("forecastday", [])
            
            # Remove hours from each day
            for day in forecast_days:
                day.pop("hour", None)
            
            # Filter fields if specified
            if fields:=fields.split(","):
                field_mapping = {
                    'temperature': ['maxtemp_c', 'maxtemp_f', 'mintemp_c', 'mintemp_f', 'avgtemp_c', 'avgtemp_f'],
                    'precipitation': ['totalprecip_mm', 'totalprecip_in', 'totalsnow_cm', 'daily_will_it_rain', 'daily_chance_of_rain', 'daily_will_it_snow', 'daily_chance_of_snow'],
                    'condition': ['condition'],
                    'astro': ['astro'],
                    'wind': ['maxwind_mph', 'maxwind_kph'],
                    'visibility': ['avgvis_km', 'avgvis_miles'],
                    'humidity': ['avghumidity']
                }
                
                # Get all keys to include based on requested fields
                keys_to_include = ['date', 'date_epoch']  # Always include date info
                for field in fields:
                    if field in field_mapping:
                        keys_to_include.extend(field_mapping[field])
                
                # Filter each forecast day
                filtered_days = []
                for day in forecast_days:
                    filtered_day = {
                        'date': day['date'],
                        'date_epoch': day['date_epoch'],
                        'day': {},
                        'astro': day.get('astro', {}) if 'astro' in fields else None
                    }
                    
                    # Filter day data
                    day_data = day.get('day', {})
                    for key in keys_to_include:
                        if key in day_data:
                            filtered_day['day'][key] = day_data[key]
                    
                    # Remove astro if not requested
                    if 'astro' not in fields:
                        filtered_day.pop('astro')
                    
                    filtered_days.append(filtered_day)
                
                return filtered_days
            
            return forecast_days

@tool
def take_screenshot(path: str = "artifacts/screenshot.png"):
    """Take a screenshot of the current screen."""
    with mss() as sct:
        screenshot = sct.shot(output=path)
        
    return ToolResult(
        content=f"Screenshot saved to {screenshot}",
        images=[Image(filepath=screenshot)]
    )

async def open_app(app_name: str) -> bool:
    """
    Opens an installed application by name on user's computer.
    """
    opened = os.system(f"appManager.exe run {app_name}")
    return opened == 0

async def close_app(app_name: str) -> bool:
    """
    Closes a running application by name on user's computer.
    """
    closed = os.system(f"appManager.exe close {app_name}")
    return closed == 0

def get_active_explorer_path():
    """Get the path of the folder open in the most recently active File Explorer window. You should use this when the user's request contains screenshot of file explorer and asking to perform some file related actions."""

    if file_explorer.get_active_explorer_path:
        return file_explorer.get_active_explorer_path()
    else:
        return "No active File Explorer window found."

def get_active_explorer_selected_paths():
    """Get paths of selected items in the most recently active File Explorer window. You should use this when the user's request contains screenshot of file explorer with items selected and asking to perform some file related actions."""
    if file_explorer.get_active_explorer_selected_paths:
        return file_explorer.get_active_explorer_selected_paths()
    else:
        return "No items selected or no active File Explorer window."
    


if __name__ == '__main__':
    print(get_active_explorer_path())
    print(get_active_explorer_selected_paths())