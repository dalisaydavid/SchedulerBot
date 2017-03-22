import bot
import json

if __name__ == "__main__":
    with open('tokens.json') as jfile:
        tokens = json.load(jfile)
    bot = bot.SchedulerBot(tokens["discord"])
    bot.run()

