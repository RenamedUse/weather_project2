# Первое задание, получаем данные по погоде на участке при помощи API, выводим их в формате JSON
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import json

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 55.7522,
    "longitude": 37.6156,
    "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "wind_speed_10m"],
    "daily": "precipitation_probability_max",
    "timezone": "Europe/Moscow",
    "forecast_days": 1
}
responses = openmeteo.weather_api(url, params=params)

response = responses[0]

current = response.Current()
current_temperature_2m = current.Variables(0).Value()
current_relative_humidity_2m = current.Variables(1).Value()
current_apparent_temperature = current.Variables(2).Value()
current_wind_speed_10m = current.Variables(3).Value()

data = {
    "current": {
        "temperature_2m": round(current_temperature_2m),
        "apparent_temperature": round(current_apparent_temperature),
        "relative_humidity_2m": round(current_relative_humidity_2m),
        "wind_speed_10m": round(current_wind_speed_10m)
    }
}

daily = response.Daily()
daily_precipitation_probability_max = daily.Variables(0).ValuesAsNumpy()

daily_data = {
    "date": pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    ).astype(str).tolist(),
    "precipitation_probability_max": daily_precipitation_probability_max.tolist()
}

data["daily"] = daily_data
json_output = json.dumps(data, ensure_ascii=False, indent=4)
print(json_output)
