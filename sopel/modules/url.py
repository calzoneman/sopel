# coding=utf-8
"""URL title module"""
# Copyright 2010-2011, Michael Yanovich, yanovich.net, Kenneth Sham
# Copyright 2012-2013 Elsie Powell
# Copyright 2013      Lior Ramati (firerogue517@gmail.com)
# Copyright © 2014 Elad Alfassa <elad@fedoraproject.org>
# Licensed under the Eiffel Forum License 2.
from __future__ import unicode_literals, absolute_import, print_function, division

import re
from sopel import web, tools, __version__
from sopel.module import commands, rule, example
from sopel.config.types import ValidatedAttribute, ListAttribute, StaticSection

import requests
from bs4 import BeautifulSoup

USER_AGENT = 'Sopel/{} (https://sopel.chat)'.format(__version__)
default_headers = {'User-Agent': USER_AGENT}
url_finder = None
# This is another regex that presumably does something important.
re_dcc = re.compile(r'(?i)dcc\ssend')
re_maybe_html_tag = re.compile(r'<[A-Za-z]+')


class UrlSection(StaticSection):
    # TODO some validation rules maybe?
    exclude = ListAttribute('exclude')
    exclusion_char = ValidatedAttribute('exclusion_char', default='!')


def configure(config):
    config.define_section('url', UrlSection)
    config.url.configure_setting(
        'exclude',
        'Enter regular expressions for each URL you would like to exclude.'
    )
    config.url.configure_setting(
        'exclusion_char',
        'Enter a character which can be prefixed to suppress URL titling'
    )


def setup(bot):
    global url_finder

    bot.config.define_section('url', UrlSection)

    if bot.config.url.exclude:
        regexes = [re.compile(s) for s in bot.config.url.exclude]
    else:
        regexes = []

    # We're keeping these in their own list, rather than putting then in the
    # callbacks list because 1, it's easier to deal with modules that are still
    # using this list, and not the newer callbacks list and 2, having a lambda
    # just to pass is kinda ugly.
    if not bot.memory.contains('url_exclude'):
        bot.memory['url_exclude'] = regexes
    else:
        exclude = bot.memory['url_exclude']
        if regexes:
            exclude.extend(regexes)
        bot.memory['url_exclude'] = exclude

    # Ensure that url_callbacks and last_seen_url are in memory
    if not bot.memory.contains('url_callbacks'):
        bot.memory['url_callbacks'] = tools.SopelMemory()
    if not bot.memory.contains('last_seen_url'):
        bot.memory['last_seen_url'] = tools.SopelMemory()

    url_finder = re.compile(r'(?u)(%s?(?:http|https|ftp)(?:://\S+))' %
                            (bot.config.url.exclusion_char), re.IGNORECASE)


@commands('title')
@example('.title http://google.com', '[ Google ] - google.com')
def title_command(bot, trigger):
    """
    Show the title or URL information for the given URL, or the last URL seen
    in this channel.
    """
    if not trigger.group(2):
        if trigger.sender not in bot.memory['last_seen_url']:
            return
        matched = check_callbacks(bot, trigger,
                                  bot.memory['last_seen_url'][trigger.sender],
                                  True)
        if matched:
            return
        else:
            urls = [bot.memory['last_seen_url'][trigger.sender]]
    else:
        urls = re.findall(url_finder, trigger)

    results = process_urls(bot, trigger, urls)
    for title, domain in results[:4]:
        bot.reply('[ %s ] - %s' % (title, domain))


@rule('(?u).*(https?://\S+).*')
def title_auto(bot, trigger):
    """
    Automatically show titles for URLs. For shortened URLs/redirects, find
    where the URL redirects to and show the title for that (or call a function
    from another module to give more information).
    """
    if re.match(bot.config.core.prefix + 'title', trigger):
        return

    # Avoid fetching known malicious links
    if 'safety_cache' in bot.memory and trigger in bot.memory['safety_cache']:
        if bot.memory['safety_cache'][trigger]['positives'] > 1:
            return

    urls = re.findall(url_finder, trigger)
    if len(urls) == 0:
        return

    results = process_urls(bot, trigger, urls)
    bot.memory['last_seen_url'][trigger.sender] = urls[-1]

    for title, domain in results[:4]:
        message = '[ %s ] - %s' % (title, domain)
        # Guard against responding to other instances of this bot.
        if message != trigger:
            bot.say(message)


def process_urls(bot, trigger, urls):
    """
    For each URL in the list, ensure that it isn't handled by another module.
    If not, find where it redirects to, if anywhere. If that redirected URL
    should be handled by another module, dispatch the callback for it.
    Return a list of (title, hostname) tuples for each URL which is not handled by
    another module.
    """

    results = []
    for url in urls:
        if not url.startswith(bot.config.url.exclusion_char):
            # Magic stuff to account for international domain names
            try:
                url = web.iri_to_uri(url)
            except Exception:  # TODO: Be specific
                pass
            # First, check that the URL we got doesn't match
            matched = check_callbacks(bot, trigger, url, False)
            if matched:
                continue
            # Finally, actually show the URL
            title = find_title(url, verify=bot.config.core.verify_ssl)
            if title:
                results.append((title, get_hostname(url)))
    return results


def check_callbacks(bot, trigger, url, run=True):
    """
    Check the given URL against the callbacks list. If it matches, and ``run``
    is given as ``True``, run the callback function, otherwise pass. Returns
    ``True`` if the url matched anything in the callbacks list.
    """
    # Check if it matches the exclusion list first
    matched = any(regex.search(url) for regex in bot.memory['url_exclude'])
    # Then, check if there's anything in the callback list
    for regex, function in tools.iteritems(bot.memory['url_callbacks']):
        match = regex.search(url)
        if match:
            # Always run ones from @url; they don't run on their own.
            if run or hasattr(function, 'url_regex'):
                function(bot, trigger, match)
            matched = True
    return matched

def looks_like_html(fragment):
    try:
        if re_maybe_html_tag.search(fragment.decode('ascii', errors='replace')):
            return True
        else:
            return False
    except:
        return False


def find_title(url, verify=True):
    """Return the title for the given URL."""
    response = requests.get(url, stream=True, verify=verify,
                            headers=default_headers)

    if not response.headers['content-type'].startswith('text/html'):
        return None

    # If there's not an HTML tag in the first 1KB of the page, probably not
    # going to be in the rest of it...
    if not looks_like_html(response.content[:1000]):
        return None

    # Limit to souping the first 1MB of text
    soup = BeautifulSoup(response.content[:1000000], 'html.parser')
    if not soup.title:
        soup.decompose()
        return None

    title = soup.title.string
    soup.decompose()

    # Below substitutions left intact
    title = title.strip()[:200]
    title = ' '.join(title.split())  # cleanly remove multiple spaces
    # More cryptic regex substitutions. This one looks to be myano's invention.
    # @calzoneman 2017-08-11: this seems unnecessary but I'm afraid to remove.
    title = re_dcc.sub('', title)

    return title or None


def get_hostname(url):
    idx = 7
    if url.startswith('https://'):
        idx = 8
    elif url.startswith('ftp://'):
        idx = 6
    hostname = url[idx:]
    slash = hostname.find('/')
    if slash != -1:
        hostname = hostname[:slash]
    return hostname


if __name__ == "__main__":
    from sopel.test_tools import run_example_tests
    run_example_tests(__file__)
