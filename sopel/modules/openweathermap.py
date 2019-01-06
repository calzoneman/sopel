from pyowm import OWM
from pyowm.exceptions import OWMError
from sopel.module import commands, example, NOLIMIT
from sopel.config.types import StaticSection, ValidatedAttribute, NO_DEFAULT
import json
import requests
import re

owm = None
WEATHER_TEMPLATE = (
    '{city}, {country}: {condition}, '
    '{temp_c:.0f}\u00b0C ({temp_f:.0f}\u00b0F), '
    'Humidity: {humidity}%, '
    'Wind: {wind_speed} m/s ({wind_direction})'
)

ZIP_CODE = re.compile(r'(?P<uszip>\d{5})|zip:(?P<zip>.+?),(?P<cc>[a-z]{2})')
CITY_ID = re.compile(r'id:(?P<id>\d+)')

class OpenWeatherMapSection(StaticSection):
    api_key = ValidatedAttribute('api_key', default=NO_DEFAULT)

def configure(config):
    config.define_section('open_weather_map', OpenWeatherMapSection,
            validate=False)
    config.open_weather_map.configure_setting(
            'api_key',
            'Enter your Open Weather Map API key'
    )

def setup(bot):
    global owm
    bot.config.define_section('open_weather_map', OpenWeatherMapSection)
    owm = OWM(API_key=bot.config.open_weather_map.api_key, version='2.5')

def arrow_direction(degrees):
    arrows = list('↓↙←↖↑↗→↘')
    index = round(degrees / 45) % 8
    return arrows[index]

def wind_direction(wind):
    return arrow_direction(wind['deg']) if 'deg' in wind else 'variable'

def format_observation(observation):
    w = observation.get_weather()
    loc = observation.get_location()
    celsius = w.get_temperature()['temp'] - 273.15
    fahrenheit = celsius * 9/5 + 32
    wind = w.get_wind()

    return WEATHER_TEMPLATE.format(
            city=loc.get_name(),
            country=loc.get_country(),
            condition=w.get_detailed_status(),
            temp_c=celsius,
            temp_f=fahrenheit,
            humidity=w.get_humidity(),
            wind_speed=wind['speed'],
            wind_direction=wind_direction(wind))

def get_observation(location):
    m = CITY_ID.match(location)
    if m:
        return owm.weather_at_id(int(m.group('id')))

    m = ZIP_CODE.match(location)
    if m:
        # Default to US zip code if exactly 5 digits are provided
        if m.group('uszip'):
            return owm.weather_at_zip_code(m.group('uszip'), 'us')
        else:
            return owm.weather_at_zip_code(m.group('zip'), m.group('cc'))

    # Fallback to search
    return owm.weather_at_place(location)

@commands('weather')
@example('.weather Seattle')
def wunderground(bot, trigger):
    location = trigger.group(2)
    if not location:
        location = bot.db.get_nick_value(trigger.nick, 'openweathermap_loc')
        if not location:
            if bot.db.get_nick_value(trigger.nick, 'woeid'):
                return bot.reply(
                        "I lost your location when Yahoo shut down its "
                        "free weather API.  You'll have to .setlocation "
                        "again :("
                )

            return bot.reply("I don't know where you live.  " +
                    'Give me a location, like .weather Seattle, or tell me '
                    'where you live by saying .setlocation Seattle, '
                    'for example.')

    location = location.strip()
    try:
        observation = get_observation(location)
        bot.say('[Weather] ' + format_observation(observation))
    except OWMError as e:
        if e.status_code == 404:
            return bot.say("I don't know where that is.  Try one of "
                           "<city>,<country> | "
                           "zip:<zip code>,<country> | "
                           "id:<city id from openweathermap.org>")
        else:
            return bot.say('Unexpected error calling OpenWeatherMap: ' + str(e))
    except Exception as e:
        return bot.say('[Exception] {}'.format(e))

@commands('setlocation')
@example('.setlocation Seattle,US')
@example('.setlocation 98101')
@example('.setlocation zip:98101,us')
@example('.setlocation id:5809844')
def update_location(bot, trigger):
    if not trigger.group(2):
        bot.reply('Give me a location, like "Seattle, WA".')
        return NOLIMIT

    try:
        observation = get_observation(trigger.group(2).strip())
        bot.db.set_nick_value(trigger.nick, 'openweathermap_loc',
                'id:' + str(observation.get_location().get_ID()))
        bot.reply("OK, I've updated your location to {}".format(
                observation.get_location().get_name()))
        bot.say('[Weather] ' + format_observation(observation))
    except OWMError as e:
        if e.status_code == 404:
            return bot.say("I don't know where that is.  Try one of "
                           "<city>,<country> | "
                           "zip:<zip code>,<country> | "
                           "id:<city id from openweathermap.org>")
        else:
            return bot.say('Unexpected error calling OpenWeatherMap: ' + str(e))
    except Exception as e:
        return bot.say('[Exception] {}'.format(e))
