"""
Tool 2: Weather Fetcher

Fetches weather from Open-Meteo (free, no API key required).

Two public entry points:

  get_weather()                — current conditions for "right now".
                                  Used by Today / everyday flows.
  get_weather_for_date(date)   — forecast for a SPECIFIC future date
                                  (YYYY-MM-DD). Used by the Planner so
                                  every upcoming event sees its OWN
                                  forecast instead of today's weather.

Both return the same result shape:

    {
      "success": bool,
      "error":   str | None,
      "source":  "live" | "forecast" | "seasonal-fallback",
      "in_range": bool,             # was the date inside the API window?
      "target_date": "YYYY-MM-DD" | None,
      "weather": {
        "city":              str,
        "temp_f":            float | int,
        "feels_like_f":      float | int,
        "condition":         str,
        "wind_mph":          float,
        "precip_chance_pct": int,
        "layer_advice":      str,
        # Daily forecasts also include:
        "temp_high_f":       float | None,
        "temp_low_f":        float | None,
        # Seasonal fallbacks include:
        "fallback_reason":   "past-date" | "beyond-forecast-window"
                              | "api-error" | None,
      }
    }

The `source` field is the agent's source-of-truth for honesty: the
reasoning trail says "live conditions in Minneapolis" only when
source == "live"; it says "forecast for Sat May 16" when source ==
"forecast"; it says "seasonal estimate (May, no live forecast)" when
source == "seasonal-fallback". No silent re-use of today's reading
for events three months out.

Open-Meteo forecast window: 16 days from today. Anything farther out
gets the seasonal fallback. Past dates also use the seasonal fallback
(we don't try to fetch historical weather — that's a different
endpoint, and "what was the weather on a past date" doesn't help an
outfit-planning agent anyway).
"""

import urllib.request
import json
from datetime import datetime, date as _date_cls
from typing import Optional


# Default location: Minneapolis, MN
DEFAULT_LAT = 44.9778
DEFAULT_LON = -93.2650
DEFAULT_CITY = "Minneapolis, MN"

# Open-Meteo free forecast endpoint covers ~16 days out.
_FORECAST_WINDOW_DAYS = 15  # day 0 = today, day 15 = +15 ahead


def get_weather(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    city: str = DEFAULT_CITY,
) -> dict:
    """
    Fetch current ("right now") weather. Falls back to a seasonal
    estimate on network error so the agent never crashes.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,weathercode,windspeed_10m,apparent_temperature"
        f"&daily=temperature_2m_max,temperature_2m_min,"
        f"precipitation_probability_max"
        f"&temperature_unit=fahrenheit"
        f"&forecast_days=1"
        f"&timezone=America%2FChicago"
    )

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())

        current = data.get("current", {})
        daily   = data.get("daily", {})

        temp_f      = current.get("temperature_2m", "N/A")
        feels_like  = current.get("apparent_temperature", temp_f)
        wind_mph    = round(current.get("windspeed_10m", 0) * 0.621371, 1)
        precip_list = daily.get("precipitation_probability_max", [0])
        precip_chance = precip_list[0] if precip_list else 0
        weather_code = current.get("weathercode", 0)

        condition    = _weather_code_to_condition(weather_code)
        layer_advice = _get_layering_advice(temp_f, precip_chance, wind_mph)

        return {
            "success":     True,
            "error":       None,
            "source":      "live",
            "in_range":    True,
            "target_date": _date_cls.today().isoformat(),
            "weather": {
                "city":              city,
                "temp_f":            round(temp_f, 1) if isinstance(temp_f, (int, float)) else temp_f,
                "feels_like_f":      round(feels_like, 1) if isinstance(feels_like, (int, float)) else feels_like,
                "condition":         condition,
                "wind_mph":          wind_mph,
                "precip_chance_pct": precip_chance,
                "layer_advice":      layer_advice,
                "temp_high_f":       None,
                "temp_low_f":        None,
                "fallback_reason":   None,
            },
        }

    except Exception as e:
        return _seasonal_fallback(
            _date_cls.today().isoformat(),
            city,
            reason="api-error",
            note=f"Live weather unavailable ({e}). Using typical seasonal estimate.",
        )


def get_weather_for_date(
    target_date: str,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    city: str = DEFAULT_CITY,
    *,
    _today: Optional[_date_cls] = None,
) -> dict:
    """
    Fetch forecast for a specific date (YYYY-MM-DD).

    Decision tree:
      target_date == today         → call get_weather() (current "now"
                                       reading, source="live").
      target_date in 1..15 days     → Open-Meteo daily forecast for
                                       that day. source="forecast".
      target_date is past           → seasonal estimate.
                                       source="seasonal-fallback",
                                       reason="past-date".
      target_date > +15 days        → seasonal estimate.
                                       reason="beyond-forecast-window".
      API failure (anywhere)        → seasonal estimate.
                                       reason="api-error".

    `_today` is a test hook so tests can pin "today" deterministically.
    """
    if not isinstance(target_date, str) or not target_date.strip():
        # No date — caller meant "now".
        return get_weather(lat=lat, lon=lon, city=city)

    try:
        tdate = datetime.strptime(target_date.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return get_weather(lat=lat, lon=lon, city=city)

    today = _today if isinstance(_today, _date_cls) else _date_cls.today()
    days_out = (tdate - today).days

    if days_out == 0:
        # Same day → live current is the most accurate read.
        return get_weather(lat=lat, lon=lon, city=city)
    if days_out < 0:
        return _seasonal_fallback(target_date, city, reason="past-date")
    if days_out > _FORECAST_WINDOW_DAYS:
        return _seasonal_fallback(
            target_date, city, reason="beyond-forecast-window"
        )

    # 1..15 days out — fetch daily forecast for the target index.
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode,"
        f"precipitation_probability_max,windspeed_10m_max"
        f"&temperature_unit=fahrenheit"
        f"&forecast_days={days_out + 1}"
        f"&timezone=America%2FChicago"
    )

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
        daily = data.get("daily", {}) or {}

        def _at(name, default=None):
            arr = daily.get(name) or []
            return arr[days_out] if len(arr) > days_out else default

        tmax  = _at("temperature_2m_max")
        tmin  = _at("temperature_2m_min")
        wcode = _at("weathercode", 0)
        prec  = _at("precipitation_probability_max", 0) or 0
        wind_kmh = _at("windspeed_10m_max", 0) or 0

        if tmax is None or tmin is None:
            return _seasonal_fallback(
                target_date, city, reason="missing-data",
                note="Forecast returned but the target day had no readings.",
            )

        wind_mph = round(wind_kmh * 0.621371, 1)
        avg_t    = round((tmax + tmin) / 2, 1)
        condition = _weather_code_to_condition(wcode)
        layer_advice = _get_layering_advice(avg_t, prec, wind_mph)

        return {
            "success":     True,
            "error":       None,
            "source":      "forecast",
            "in_range":    True,
            "target_date": target_date,
            "weather": {
                "city":              city,
                "temp_f":            avg_t,
                "feels_like_f":      avg_t,
                "condition":         condition,
                "wind_mph":          wind_mph,
                "precip_chance_pct": int(prec) if isinstance(prec, (int, float)) else 0,
                "layer_advice":      layer_advice,
                "temp_high_f":       round(tmax, 1),
                "temp_low_f":        round(tmin, 1),
                "fallback_reason":   None,
            },
        }
    except Exception as e:
        return _seasonal_fallback(
            target_date, city, reason="api-error",
            note=f"Live forecast unavailable ({e}). Using typical seasonal estimate.",
        )


def _seasonal_fallback(
    target_date: str,
    city: str,
    *,
    reason: str,
    note: Optional[str] = None,
) -> dict:
    """
    A deterministic, Northern-Hemisphere seasonal estimate for any
    date. Honest framing: the source field is "seasonal-fallback",
    the fallback_reason explains why, and the reasoning trail
    surfaces both — the user knows this isn't a real forecast.
    """
    try:
        mon = datetime.strptime(target_date, "%Y-%m-%d").month
    except (ValueError, TypeError):
        mon = datetime.now().month

    # Coarse Northern-Hemisphere seasonal profile. Conservative; we
    # never pretend it's a precise forecast. Tuned so an outfit
    # planner gets a reasonable layering signal.
    if mon in (12, 1, 2):
        temp, cond, precip, wind = 28, "Mixed Conditions", 30, 10
    elif mon in (3, 11):
        temp, cond, precip, wind = 45, "Partly Cloudy", 25, 11
    elif mon in (4, 10):
        temp, cond, precip, wind = 58, "Partly Cloudy", 25, 9
    elif mon in (5, 9):
        temp, cond, precip, wind = 68, "Partly Cloudy", 20, 8
    else:  # 6, 7, 8
        temp, cond, precip, wind = 78, "Clear Sky", 15, 7

    layer_advice = _get_layering_advice(temp, precip, wind)
    reason_phrase = {
        "past-date":              "the date is in the past",
        "beyond-forecast-window":
            "the date is more than 15 days out (beyond Open-Meteo's "
            "free-tier forecast window)",
        "api-error":              "the weather service is unreachable",
        "missing-data":           "the forecast returned no readings for that day",
    }.get(reason, reason)

    return {
        "success":     True,
        "error":       note,
        "source":      "seasonal-fallback",
        "in_range":    False,
        "target_date": target_date,
        "weather": {
            "city":              city,
            "temp_f":            temp,
            "feels_like_f":      temp,
            "condition":         cond,
            "wind_mph":          wind,
            "precip_chance_pct": precip,
            "layer_advice": (
                f"Seasonal estimate — {reason_phrase}. " + layer_advice
            ),
            "temp_high_f":       None,
            "temp_low_f":        None,
            "fallback_reason":   reason,
        },
    }


def _weather_code_to_condition(code: int) -> str:
    """Maps WMO weather codes to human-readable descriptions."""
    if code == 0:
        return "Clear Sky"
    if code in (1, 2, 3):
        return "Partly Cloudy"
    if code in (45, 48):
        return "Foggy"
    if code in (51, 53, 55):
        return "Drizzle"
    if code in (61, 63, 65):
        return "Rain"
    if code in (71, 73, 75):
        return "Snow"
    if code in (80, 81, 82):
        return "Rain Showers"
    if code in (95, 96, 99):
        return "Thunderstorm"
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
