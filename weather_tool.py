"""
Tool 2: Weather Fetcher
Fetches real weather data from Open-Meteo (free, no API key required).
Falls back to mock data if the network call fails.
Location defaults to Minneapolis, MN (lat/lon configurable).
"""

import urllib.request
import json


# Default location: Minneapolis, MN
DEFAULT_LAT = 44.9778
DEFAULT_LON = -93.2650
DEFAULT_CITY = "Minneapolis, MN"


def get_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, city: str = DEFAULT_CITY) -> dict:
    """
    Fetches current weather and today's forecast from Open-Meteo API.
    Returns a dict with 'success', 'weather', and 'error' keys.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,weathercode,windspeed_10m,apparent_temperature"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&temperature_unit=fahrenheit"
        f"&forecast_days=1"
        f"&timezone=America%2FChicago"
    )

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())

        current = data.get("current", {})
        daily = data.get("daily", {})

        temp_f = current.get("temperature_2m", "N/A")
        feels_like = current.get("apparent_temperature", temp_f)
        wind_mph = round(current.get("windspeed_10m", 0) * 0.621371, 1)
        precip_chance = daily.get("precipitation_probability_max", [0])[0] if daily else 0
        weather_code = current.get("weathercode", 0)

        condition = _weather_code_to_condition(weather_code)
        layer_advice = _get_layering_advice(temp_f, precip_chance, wind_mph)

        return {
            "success": True,
            "error": None,
            "weather": {
                "city": city,
                "temp_f": round(temp_f, 1) if isinstance(temp_f, (int, float)) else temp_f,
                "feels_like_f": round(feels_like, 1) if isinstance(feels_like, (int, float)) else feels_like,
                "condition": condition,
                "wind_mph": wind_mph,
                "precip_chance_pct": precip_chance,
                "layer_advice": layer_advice
            }
        }

    except Exception as e:
        # Graceful fallback — mock data so the agent still runs
        return {
            "success": True,
            "error": f"Live weather unavailable ({e}). Using typical seasonal estimate.",
            "weather": {
                "city": city,
                "temp_f": 52,
                "feels_like_f": 48,
                "condition": "Partly Cloudy",
                "wind_mph": 10,
                "precip_chance_pct": 20,
                "layer_advice": "A light jacket or coat is recommended."
            }
        }


def _weather_code_to_condition(code: int) -> str:
    """Maps WMO weather codes to human-readable descriptions."""
    if code == 0:
        return "Clear Sky"
    elif code in [1, 2, 3]:
        return "Partly Cloudy"
    elif code in [45, 48]:
        return "Foggy"
    elif code in [51, 53, 55]:
        return "Drizzle"
    elif code in [61, 63, 65]:
        return "Rain"
    elif code in [71, 73, 75]:
        return "Snow"
    elif code in [80, 81, 82]:
        return "Rain Showers"
    elif code in [95, 96, 99]:
        return "Thunderstorm"
    else:
        return "Mixed Conditions"


def _get_layering_advice(temp_f, precip_chance: int, wind_mph: float) -> str:
    """Translates weather numbers into practical dressing advice."""
    advice = []

    if isinstance(temp_f, (int, float)):
        if temp_f < 32:
            advice.append("Heavy coat, scarf, and gloves are essential.")
        elif temp_f < 45:
            advice.append("Wear a warm coat.")
        elif temp_f < 58:
            advice.append("A light jacket or trench coat is recommended.")
        elif temp_f < 70:
            advice.append("Light layers work well — a cardigan or blazer is enough.")
        else:
            advice.append("No coat needed. Light, breathable clothing is ideal.")

    if isinstance(precip_chance, (int, float)) and precip_chance > 50:
        advice.append("Rain is likely — consider waterproof outerwear or an umbrella.")
    elif isinstance(precip_chance, (int, float)) and precip_chance > 25:
        advice.append("Some rain possible — bring an umbrella just in case.")

    if isinstance(wind_mph, (int, float)) and wind_mph > 20:
        advice.append("It's windy — avoid flowing or very lightweight fabrics outdoors.")

    return " ".join(advice) if advice else "Standard clothing for the season."
