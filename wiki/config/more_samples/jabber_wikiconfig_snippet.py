    # This is a sample configuration snippet for a wiki which uses a Jabber
    # notification bot.
    # Note that the bot has to be started separately and has its own configuration.

    # Host and port on which the notification bot runs
    notification_bot_uri = u"http://localhost:8000"

    # A secret shared with notification bot, must be the same in both configs
    # (the wiki config and the notification bot config) for communication to work.
    # CHANGE IT TO A LONG RANDOM STRING, OR YOU WILL HAVE A SECURITY ISSUE!
    secret = u""

