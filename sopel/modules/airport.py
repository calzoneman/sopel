#coding=utf-8
'''
airport.py - Look up an airport by IATA or ICAO identifier
'''

from sopel.module import commands, example
import requests
import re

IATA = re.compile(r'^[A-Z]{3}$')
ICAO = re.compile(r'^[A-Z]{4}$')

FETCH_TEMPLATE = 'http://www.airport-data.com/api/ap_info.json?{source}={code}'

class APIError(Exception):
    def __init__(self, status_code, message=''):
        self.status_code = status_code
        self.message = message

    def __str__(self):
        return 'API returned HTTP {status_code} {message}'.format(
                **self.__dict__
        )

@commands('air', 'airport')
@example('.air ATL')
def airport(bot, trigger):
    code = trigger.group(2)
    if not code:
        return bot.reply('Give me an airport code, like .air SEA')

    code = code.upper().strip()
    try:
        if IATA.match(code):
            data = get_airport_info(code, 'iata')
        elif ICAO.match(code):
            data = get_airport_info(code, 'icao')
        else:
            return bot.reply('Give me an IATA or ICAO code, like .air SEA')

        bot.say(format_airport_info(data))
    except APIError as e:
        return bot.say('Unable to retrieve airport data: {}'.format(str(e)))
    except Exception as e:
        return bot.say('[Exception] {}'.format(repr(e)))

def get_airport_info(code, source):
    r = requests.get(FETCH_TEMPLATE.format(code=code, source=source))
    print(FETCH_TEMPLATE.format(code=code, source=source))

    if r.status_code != 200:
        raise APIError(r.status_code)

    result = r.json()
    print(result)
    if result['status'] != 200:
        raise APIError(result['status'], result['error'])

    return result

def format_airport_info(info):
    return '{name}, {location} (ICAO: {icao}, IATA: {iata}) - {link}'.format(
            **info
    )
