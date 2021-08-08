from bot import HypixelSloveniaDiscordBot, StopAction


while True:
    bot = HypixelSloveniaDiscordBot()
    bot.runBot()

    if bot.stop_action == StopAction.NONE:
        print("Bot has crashed")
    elif bot.stop_action == StopAction.SHUTDOWN:
        print("Bot has shutdown")
        break
    elif bot.stop_action == StopAction.RESTART:
        print("Bot is restarting")
