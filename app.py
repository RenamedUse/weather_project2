# Рабочий сайт, принимающий названия городов на русском и оценивающий погодные условния на заданном маршруте
import openmeteo_requests
import requests
import requests_cache
from retry_requests import retry
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


def is_weather_favorable(current_temperature_2m, current_apparent_temperature, first_precipitation_value,
                         current_wind_speed_10m):
    unfavorable_conditions = (
            current_temperature_2m < 5 or current_temperature_2m > 28 or
            current_apparent_temperature < -5 or current_apparent_temperature > 30 or
            first_precipitation_value > 60 or
            current_wind_speed_10m > 7
    )
    return not unfavorable_conditions, 'погода плохая' if unfavorable_conditions else 'погода хорошая'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/error')
def error():
    message = request.args.get('message', 'Неизвестная ошибка.')
    return render_template('error.html', message=message)


@app.route('/result')
def result():
    overall_message = request.args.get('message', 'Нет данных для отображения.')
    return render_template('result.html', message=overall_message)


def fetch_coordinates(city_name):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=ru&format=json"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    if data.get("results"):
        return data["results"][0]["latitude"], data["results"][0]["longitude"]

    raise ValueError(f"Не удалось найти координаты для города: {city_name}")


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

    if responses:
        response = responses[0]
        current = response.Current()
        daily = response.Daily()

        weather_data = {
            "current_temperature_2m": current.Variables(0).Value(),
            "current_apparent_temperature": current.Variables(2).Value(),
            "current_wind_speed_10m": current.Variables(3).Value(),
            "first_precipitation_value": daily.Variables(0).ValuesAsNumpy()[0]
        }

        return (weather_data["current_temperature_2m"],
                weather_data["current_apparent_temperature"],
                weather_data["first_precipitation_value"],
                weather_data["current_wind_speed_10m"])

    raise ConnectionError("Ошибка получения данных о погоде.")


@app.route('/submit', methods=['POST'])
def submit():
    departure_place = request.form['departure_place']
    destination_place = request.form['destination_place']

    try:
        latitude1, longitude1 = fetch_coordinates(departure_place)
        departure_weather_data = fetch_weather_data(latitude1, longitude1)

        latitude2, longitude2 = fetch_coordinates(destination_place)
        destination_weather_data = fetch_weather_data(latitude2, longitude2)

        if (latitude1 == latitude2) and (longitude1 == longitude2):
            return redirect(url_for('error', message="Начальная и конечная точки совпадают!"))

        departure_weather_check_result, departure_weather_message = is_weather_favorable(*departure_weather_data)
        destination_weather_check_result, destination_weather_message = is_weather_favorable(*destination_weather_data)

        if departure_weather_check_result and destination_weather_check_result:
            overall_message = 'Погода - супер в обеих точках! ;)'
        elif not departure_weather_check_result and not destination_weather_check_result:
            overall_message = 'Ой-ой, погода везде плохая :('
        else:
            overall_message = f'Что ж, {departure_weather_message} в отправной точке и {destination_weather_message} в конечной точке :/'

        return redirect(url_for('result', message=overall_message))

    except ValueError as ve:
        return redirect(url_for('error', message=str(ve)))
    except ConnectionError as ce:
        return redirect(url_for('error', message=str(ce)))
    except Exception as e:
        return redirect(url_for('error', message="Упс. Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова."))


if __name__ == '__main__':
    app.run(debug=True)
