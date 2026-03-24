from fastmcp import FastMCP
from typing import Any

# Initialize the server with a name
mcp = FastMCP("weather-server")

# Define a tool using the @mcp.tool decorator
@mcp.tool()
def get_weather(city: str) -> dict[str, Any]:
    """
    Get the current weather for a specified city.

    Args:
        city: The name of the city.

    Returns:
        A dictionary containing weather information.
    """
    # In a real application, you would call a weather API.
    # For this example, we return mock data.
    weather_data = {
        "new york": {"temp": 72, "condition": "sunny"},
        "london": {"temp": 59, "condition": "cloudy"},
        "tokyo": {"temp": 68, "condition": "rainy"},
    }
    city_lower = city.lower()
    if city_lower in weather_data:
        return {"city": city, **weather_data[city_lower]}
    else:
        return {"city": city, "temp": 70, "condition": "unknown"}

# Run the server
if __name__ == "__main__":
    # This runs the server using standard I/O (stdio) for communication
    print("Starting MCP server. Press Ctrl+C to stop.")
    mcp.run(transport="stdio")
