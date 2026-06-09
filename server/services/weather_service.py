"""
Ayura AI - Weather Service
Fetches real-time weather data from OpenWeatherMap and maps conditions to Ayurvedic impact.
Optional — works without an API key by returning None.
"""

import httpx
from config import settings


async def fetch_weather(lat: float | None = None, lon: float | None = None) -> dict | None:
    """Fetch current weather from OpenWeatherMap. Returns None if unavailable."""
    api_key = getattr(settings, "WEATHER_API_KEY", None)
    if not api_key:
        return None

    lat = lat or getattr(settings, "DEFAULT_LAT", 28.6139)
    lon = lon or getattr(settings, "DEFAULT_LON", 77.2090)

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        conditions = data["weather"][0]["main"] if data.get("weather") else "Clear"
        description = data["weather"][0]["description"] if data.get("weather") else ""

        return {
            "temperature_c": round(temp, 1),
            "humidity": humidity,
            "conditions": conditions,
            "description": description,
            "location": data.get("name", "Unknown"),
            "ayurvedic_impact": _map_to_ayurvedic_impact(temp, humidity, conditions),
        }
    except Exception:
        return None


def _map_to_ayurvedic_impact(temp: float, humidity: int, conditions: str) -> dict:
    """Map weather conditions to Ayurvedic dosha impact."""
    aggravated = []
    pacified = []

    # Temperature effects
    if temp > 35:
        aggravated.append("pitta")
        pacified.append("kapha")
    elif temp > 25:
        aggravated.append("pitta")
    elif temp < 10:
        aggravated.append("vata")
        pacified.append("pitta")
    elif temp < 20:
        aggravated.append("vata")

    # Humidity effects
    if humidity > 75:
        aggravated.append("kapha")
        pacified.append("vata")
    elif humidity < 30:
        aggravated.append("vata")
        pacified.append("kapha")

    # Weather condition effects
    conditions_lower = conditions.lower()
    if conditions_lower in ("rain", "drizzle", "thunderstorm"):
        aggravated.append("vata")
        aggravated.append("kapha")
    elif conditions_lower in ("snow", "mist", "fog"):
        aggravated.append("kapha")
    elif conditions_lower == "clear" and temp > 30:
        aggravated.append("pitta")

    # Deduplicate
    aggravated = list(set(aggravated))
    pacified = list(set(pacified))

    if not aggravated:
        summary = "Weather conditions are balanced — no major dosha aggravation expected."
    else:
        summary = f"Current weather may aggravate {', '.join(aggravated)} dosha. Take extra care with balancing practices."

    return {
        "aggravated_doshas": aggravated,
        "pacified_doshas": pacified,
        "summary": summary,
    }
