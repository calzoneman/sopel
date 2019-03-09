from sopel.module import NOLIMIT, commands, example, rule

def fullwidth_char(c):
    if 33 <= ord(c) <= 126:
        return chr(0xff01 + ord(c) - 33)
    return c

def convert(text):
    return ''.join(fullwidth_char(c) for c in text.lower())

@commands('fw', 'fullwidth')
@example('.fw aesthetic')
def fullwidth(bot, trigger):
    if trigger.group(2) is None:
        bot.reply(convert('convert what to fullwidth?'))
        return NOLIMIT

    bot.say(convert(trigger.group(2)))
