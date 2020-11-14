from sopel.module import NOLIMIT, commands, example, rule

# Sorry to anyone whose text editor chokes on this (my terminal hates it)
upside_down = 'ɐqɔpǝɟbɥıſʞןɯuodbɹsʇnʌʍxʎz'

def australian_char(c):
    if ord('a') <= ord(c) <= ord('z'):
        return upside_down[ord(c) - ord('a')]
    elif c == "'":
        return ','
    elif c == '!':
        return '¡'
    elif c == '?':
        return '¿'
    else:
        return c

def fullwidth_char(c):
    if 33 <= ord(c) <= 126:
        return chr(0xff01 + ord(c) - 33)
    return c

def convert_fw(text):
    return ''.join(fullwidth_char(c) for c in text)

def convert_au(text):
    return ''.join(australian_char(c.lower()) for c in text[::-1])

def convert_sb(text):
    chars = [
        text[i].upper() if i % 2 == 0 else text[i].lower()
        for i in range(len(text))
    ]
    return ''.join(chars)

@commands('fw', 'fullwidth')
@example('.fw aesthetic')
def fullwidth(bot, trigger):
    if trigger.group(2) is None:
        bot.reply(convert_fw('convert what to fullwidth?'))
        return NOLIMIT

    bot.say(convert_fw(trigger.group(2)))

@commands('au', 'australia')
@example(".au g'day mate")
def australia(bot, trigger):
    if trigger.group(2) is None:
        bot.reply(convert_au('convert what to australian?'))
        return NOLIMIT

    bot.say(convert_au(trigger.group(2)))

@commands('sb', 'spongebob')
@example('.sb sarcasm')
def spongebob(bot, trigger):
    if trigger.group(2) is None:
        bot.reply(convert_sb('convert what to spongebob?'))
        return NOLIMIT

    bot.say(convert_sb(trigger.group(2)))
