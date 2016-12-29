from sopel.module import commands, example, NOLIMIT
from sopel.config.types import StaticSection, ValidatedAttribute, NO_DEFAULT
from urllib.parse import quote
import json
import requests
import re

API_KEY = ''
URL_TEMPLATE = (
    'https://api.wunderground.com/api/{api_key}/conditions/q/{query}.json'
)
WEATHER_TEMPLATE = (
    '{location}: {condition}, {temperature}, Humidity: {humidity}, Wind: {wind}'
)
DEGREES_RE = re.compile(r'(\d) ([CF])')

class WeatherUndergroundSection(StaticSection):
    api_key = ValidatedAttribute('api_key', default=NO_DEFAULT)

def configure(config):
    config.define_section('weather_underground', WeatherUndergroundSection,
            validate=False)
    config.weather_underground.configure_setting(
            'api_key',
            'Enter your Weather Underground API key'
    )

def setup(bot):
    global API_KEY
    bot.config.define_section('weather_underground', WeatherUndergroundSection)
    API_KEY = bot.config.weather_underground.api_key

class WeatherError(Exception):
    pass

class WeatherReport:
    def __init__(self, raw):
        self.location = raw['display_location']['full']
        self.condition = raw['weather']
        self.temperature = DEGREES_RE.sub('\\1\u00b0\\2',
                raw['temperature_string'], count=2)
        self.humidity = raw['relative_humidity']
        self.wind = raw['wind_string']

    def __str__(self):
        return WEATHER_TEMPLATE.format(**self.__dict__)

def get_weather(location):
    location = quote(location)
    r = requests.get(URL_TEMPLATE.format(api_key=API_KEY, query=location))
    if r.status_code != 200:
        r.raise_for_status()

    response = r.json()
    if 'error' in response:
        raise WeatherError(
                'Unable to retrieve weather: {}'.format(response['error']))

    return WeatherReport(response['current_observation'])

@commands('weather')
@example('.weather Seattle')
def wunderground(bot, trigger):
    location = trigger.group(2)
    if not location:
        location = bot.db.get_nick_value(trigger.nick, 'wunderground_loc')
        if not location:
            return bot.reply("I don't know where you live.  " +
                    'Give me a location, like .weather Seattle, or tell me ' +
                    'where you live by saying .setlocation Seattle, ' +
                    'for example.')

    location = location.strip()
    try:
        weather = get_weather(location)
        bot.say('[Weather Underground] ' + str(weather))
    except Exception as e:
        return bot.say('[Exception] {}'.format(e))

@commands('setlocation')
@example('.setlocation Seattle, WA')
def update_location(bot, trigger):
    if not trigger.group(2):
        bot.reply('Give me a location, like "Seattle, WA".')
        return NOLIMIT

    try:
        weather = get_weather(trigger.group(2))
        bot.db.set_nick_value(trigger.nick, 'wunderground_loc',
                weather.location)
        bot.reply("OK, I've updated your location to {}".format(
                weather.location))
        bot.say('[Weather Underground] ' + str(weather))
    except Exception as e:
        bot.reply('Unable to update location: {}'.format(e))
