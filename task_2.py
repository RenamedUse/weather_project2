# Второе задание, вывожу через Flask данные по погоде в 2-х городах
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from flask import Flask, render_template

app = Flask(__name__)

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


def check_bad_weather(current_temperature_2m, current_apparent_temperature, relative_humidity_2m,
                      first_precipitation_value, current_wind_speed_10m):
    if (current_temperature_2m < -15 or current_temperature_2m > 33 or
            current_apparent_temperature < -25 or current_apparent_temperature > 37 or
            relative_humidity_2m > 95 or
            first_precipitation_value > 95 or
            current_wind_speed_10m > 8):
        return False, 'Ой-ой, погода плохая'
    else:
        return True, 'Погода — супер'


def fetch_weather_data(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
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

    daily = response.Daily()
    daily_precipitation_probability_max = daily.Variables(0).ValuesAsNumpy()

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        ),
        "precipitation_probability_max": daily_precipitation_probability_max
    }

    daily_dataframe = pd.DataFrame(data=daily_data)
    first_precipitation_value = daily_dataframe['precipitation_probability_max'].iloc[0]

    return (current_temperature_2m, current_apparent_temperature,
            current_relative_humidity_2m, first_precipitation_value,
            current_wind_speed_10m)


@app.route('/task-2', methods=['GET'])
def task_two():
    coordinates = [(56.8584, 35.9006), (25.0772, 55.3093)]  # Тверь и Дубай
    results = []

    for lat, lon in coordinates:
        weather_data = fetch_weather_data(lat, lon)
        result, message = check_bad_weather(*weather_data)
        results.append({
            'location': f'({lat}, {lon})',
            'message': message,
            'temperature': round(weather_data[0]),
            'apparent_temperature': round(weather_data[1]),
            'humidity': round(weather_data[2]),
            'precipitation_probability': round(weather_data[3]),
            'wind_speed': round(weather_data[4])
        })

    return render_template('task_two.html', results=results)


if __name__ == '__main__':
    app.run(debug=True)
