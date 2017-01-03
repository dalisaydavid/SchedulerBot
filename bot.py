import discord
import asyncio

class SchedulerBot(discord.Client):
    def __init__(self, discord_token):
        super(SchedulerBot, self).__init__()

        self.discord_token = discord_token
        self.commands = {
            #"commands": self.output_commands
        }

    def run(self):
        super(SchedulerBot, self).run(self.discord_token)

    @asyncio.coroutine
    def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    @asyncio.coroutine
    def handle_quotations(self, tokens):
        new_tokens = []

        space_phrased_found = False
        phrase = ""

        for token in tokens:
            if "\"" in token:
                token = token.strip("\"")
                phrase += (token + " ")
                if space_phrased_found:
                    new_tokens.append(phrase)
                    space_phrase_found = False
                else:
                    space_phrased_found = True
            else:
                if space_phrased_found:
                    phrase += (token + " ")
                else:
                    new_tokens.append(token)

        return new_tokens

    @asyncio.coroutine
    def on_message(self, message):
        # !schedule OverwatchNight 1/5/17 5:00PM EST "Lets play duh games."
        if message.content.startswith('!schedule'):
            tokens = message.content.split(' ')[1:]
            tokens = yield from self.handle_quotations(tokens)
            print(tokens)
            try:
                yield from self.send_message(message.channel, " | ".join(tokens))
            except:
                print("Cannot send message.")

if __name__ == '__main__':
    bot = SchedulerBot("Discord Bot Key")
    bot.run()
