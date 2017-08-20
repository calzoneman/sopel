# coding=utf-8
# Copyright 2013 Elsie Powell, embolalia.com
# Licensed under the Eiffel Forum License 2
from __future__ import unicode_literals, absolute_import, print_function, division

import json
import re
import requests

from sopel.module import commands, example, NOLIMIT

exchange_url = 'http://api.fixer.io/latest?base={from_code}&symbols={to_code}'
regex = re.compile(r'''
    (\d+(?:\.\d+)?)        # Decimal number
    \s*([a-zA-Z]{3})       # 3-letter currency code
    \s+(?:in|as|of|to)\s+  # preposition
    ([a-zA-Z]{3})          # 3-letter currency code
    ''', re.VERBOSE)

def get_exchange_rate(from_code, to_code):
    from_code = from_code.upper()
    to_code = to_code.upper()

    # TODO: fix bitcoin
    if from_code == 'BTC' or to_code == 'BTC':
        raise Exception('Bitcoin conversion is not supported at the moment')

    url = exchange_url.format(from_code=from_code, to_code=to_code)
    res = requests.get(url)

    if res.status_code == 422: # Unprocessable Entity
        raise Exception('Unknown currency code "{}"'.format(from_code))

    if res.status_code != 200:
        raise Exception('Unable to retrieve exchange rate: HTTP {}'.format(
                res.status_code))

    data = res.json()

    if to_code not in data['rates']:
        raise Exception('Unknown currency code "{}"'.format(to_code))

    return data['rates'][to_code]

@commands('cur', 'currency', 'exchange')
@example('.cur 20 EUR in USD')
def exchange(bot, trigger):
    """Show the exchange rate between two currencies"""

    if not trigger.group(2):
        return bot.reply("No search term. An example: .cur 20 EUR in USD")

    match = regex.match(trigger.group(2))

    if not match:
        bot.reply("Sorry, I didn't understand the input.")
        return NOLIMIT

    amount, of, to = match.groups()

    try:
        amount = float(amount)
    except:
        bot.reply("Sorry, I didn't understand the input.")

    display(bot, amount, of, to)


def display(bot, amount, of, to):
    if not amount:
        bot.reply("Zero is zero, no matter what country you're in.")

    try:
        rate = get_exchange_rate(of, to)
    except Exception as e:
        bot.reply('Unable to retrieve exchange rate: {}'.format(e))
        return NOLIMIT

    result = amount * rate
    bot.say('{from_amount:.2f} {from_code} = {to_amount:.2f} {to_code}'.format(
        from_amount=amount,
        from_code=of.upper(),
        to_amount=result,
        to_code=to.upper()
    ))
