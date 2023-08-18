from flask import Flask, render_template, request, jsonify
from flask_basicauth import BasicAuth
import requests


from logger import LogHandler
from utils import ConfigManager  # To read the config file
from exception import CustomException
from weather_api import WeatherDataProcessor #To read data from the API
from mongodb_manager import WeatherProcessorApp  # To do the MongoDB operation
from prediction_pipeline import PredictPipeline
import pymongo
import logging

app = Flask(__name__)


# Initialize LogHandler and ConfigManager
log_handler = LogHandler()
log_handler.setup_logging()
config_manager = ConfigManager()

# Read authentication credentials from config.ini
auth_username = config_manager.get_authentication_username()
auth_password = config_manager.get_authentication_password()

# Initialize Basic Authentication
app.config['BASIC_AUTH_USERNAME'] = auth_username
app.config['BASIC_AUTH_PASSWORD'] = auth_password
basic_auth = BasicAuth(app)


# Initialize WeatherDataProcessor that handle the MongoDB and Weather API operation
api_baseurl =config_manager.get_api_file_path()
mongodb_uri, database_name, collection_name = config_manager.get_MongoDB_info()
mongo_client= pymongo.MongoClient(mongodb_uri)
weather_processor=WeatherDataProcessor(api_baseurl, mongo_client, database_name, collection_name)

# weather_processor.remove_weather_condition()


@app.route('/get_weatherdata', methods=['GET', 'POST'])
@basic_auth.required 
def get_location():
    if request.method == 'POST':
        location = request.form['location']
        lat, lon = get_lat_lon_from_location(location)
        if lat and lon:
                getdata=WeatherProcessorApp(config_manager,log_handler,lat,lon)
                getdata.get_weather_save_db()
                weather_data = weather_processor.get_weather(lat, lon)
                if weather_data:
                    weather_processor.save_to_mongodb(weather_data)
                    json_weather_data = weather_processor.convert_to_serializable(weather_data)
                    return jsonify(json_weather_data)
                
                else:
                    return "Weather data not available"
        else:
            return "Location not found"
    return render_template('location_form.html')


def get_lat_lon_from_location(location):
    nominatim_url = f'https://nominatim.openstreetmap.org/search?format=json&q={location}'
    
    try:
        response = requests.get(nominatim_url)
        response.raise_for_status()
        location_data = response.json()

        if location_data:
            latitude = location_data[0]['lat']
            longitude = location_data[0]['lon']
            return latitude, longitude
        else:
            return None, None
    except requests.exceptions.RequestException:
        return None, None
    



   
@app.route('/add_weather_condition', methods=['GET', 'POST'])
def add_weather_condition():
    if request.method == 'POST':
        location = request.form['location']
        condition = request.form['condition']

        if location and condition:
            # Get latitude and longitude from location using geocoding
            latitude, longitude = get_lat_lon_from_location(location)
            if latitude is not None and longitude is not None:
                weather_processor.add_weather_condition(latitude, longitude, condition)
                print(latitude, longitude, condition)
                return "Weather condition added in MongoDB successfully"
            else:
                return "Invalid location provided"
        else:
            return "Invalid data provided"
    return render_template('weather_form.html')



if __name__ == '__main__':
    app.run(debug=True)