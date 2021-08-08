from bot import HypixelSloveniaDiscordBot, StopAction

channel_shutdown_id = 0

while True:
    bot = HypixelSloveniaDiscordBot(channel_shutdown_id)
    bot.runBot()

    channel_shutdown_id = bot.channel_shutdown_id

    if bot.stop_action == StopAction.NONE:
        print("Bot has been interrupted")
        break
    elif bot.stop_action == StopAction.SHUTDOWN:
        print("Bot has shutdown")
        break
    elif bot.stop_action == StopAction.RESTART:
        print("Bot is restarting")
