import requests
from datetime import datetime, timedelta, timezone
from langchain_core.tools import tool

UA = {"User-Agent": "LangGraph-Demo/1.0 (+https://example.local)"}
meta = {"verbose": True}


def _parse_date_label(date_label: str) -> str:
    """Parse relative labels like today/tomorrow or ISO date; return YYYY-MM-DD."""
    now = datetime.now(timezone.utc)
    dl = (date_label or "today").strip().lower()
    if dl in {"today", "now"}:
        d = now
    elif dl in {"tomorrow", "tmr"}:
        d = now + timedelta(days=1)
    else:
        try:
            d = datetime.fromisoformat(dl).replace(tzinfo=timezone.utc)
        except Exception:
            d = now
    return d.strftime("%Y-%m-%d")


@tool("weather_tool")
def weather_tool(city: str, date: str = "today") -> str:
    """Get simple weather (Open-Meteo). Supports 'today'/'tomorrow' or ISO date."""
    if meta["verbose"]:
        print("[INFO] weather_tool is called. Executing...")

    city_q = (city or "").strip()
    if not city_q:
        return "[weather] Please provide a city name."

    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city_q, "count": 1, "language": "en"},
            headers=UA,
            timeout=4,
        )
        if geo.status_code != 200:
            return f"[weather] Geocoding failed for {city_q}."
        g = geo.json()
        results = g.get("results") or []
        if not results:
            return f"[weather] City not found: {city_q}."
        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        canonical = results[0].get("name", city_q)
        country = results[0].get("country", "")

        target = _parse_date_label(date)

        fc = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": "UTC",
                "start_date": target,
                "end_date": target,
            },
            headers=UA,
            timeout=4,
        )
        if fc.status_code != 200:
            return f"[weather] Forecast fetch failed for {canonical}."
        d = fc.json()
        daily = d.get("daily", {})
        if not daily.get("time"):
            return f"[weather] No forecast data for {canonical} on {target}."

        tmax = daily.get("temperature_2m_max", [None])[0]
        tmin = daily.get("temperature_2m_min", [None])[0]
        rain = daily.get("precipitation_sum", [None])[0]
        code = daily.get("weathercode", [None])[0]

        desc_map = {
            0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "fog", 48: "depositing rime fog", 51: "light drizzle", 53: "drizzle",
            55: "dense drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
            71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
            81: "heavy showers", 95: "thunderstorm",
        }
        desc = desc_map.get(code, "mixed conditions")
        rain_txt = f", precip {rain}mm" if rain is not None else ""
        return (
            f"Weather in {canonical}{' ('+country+')' if country else ''} on {target}: "
            f"{desc}, min {tmin}°C / max {tmax}°C{rain_txt}."
        )

    except Exception as e:
        return f"[weather] Error: {e}"


