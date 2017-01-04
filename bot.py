import discord
import asyncio
import time
from datetime import datetime
from tinydb import TinyDB, Query


class AlreadyCreatedException(Exception):
    def __init__(self, arg):
        self.msg = "{} has already been created.".format(arg)
    def __str__(self):
        return self.msg

class SchedulerBot(discord.Client):
    def __init__(self, discord_token):
        super(SchedulerBot, self).__init__()

        self.discord_token = discord_token
        self.db = TinyDB("db.json")

    def run(self):
        super(SchedulerBot, self).run(self.discord_token)

    @asyncio.coroutine
    def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    def handle_quotations(self, tokens):
        new_tokens = []

        phrase_found = False
        phrase = ""

        for token in tokens:
            if "\"" in token:
                token_ = token.strip("\"")
                phrase += (token_ + " ")
                if phrase_found or token.count("\"") == 2:
                    new_tokens.append(phrase.strip())
                    phrase = " "
                    phrase_found = False
                else:
                    phrase_found = True
            else:
                if phrase_found:
                    phrase += (token + " ")
                else:
                    new_tokens.append(token.strip())

        return new_tokens

    # name, start_date, created_by, deleted_by, last_modified_date, modified_by, description
    def create_event(self, event_name, event_date, event_time, event_timezone, event_description, event_author):
        table = self.db.table('Event')

        if table.search(Query().name == event_name):
            return "Event {} already created. Cannot override this event.".format(event_name)

        now_date = time.strftime("%Y-%m-%d")
        now_time = time.strftime("%I:%M %p")
        # now_time = time.strftime("%H:%M")
        now_tz = time.tzname[0]

        event_record = {
            'name': event_name, 'date': event_date, 'time': event_time, 'timezone': event_timezone,
            'description': event_description, 'author': event_author, 'created_date': now_date,
            'created_time': now_time, 'created_timezone': now_tz
        }

        try:
            table.insert(event_record)
            return "{} event successfully recorded. Others may now reply to this event.".format(event_name)
        except:
            return "Cannot insert record into the Event table."

    @asyncio.coroutine
    def on_message(self, message):
        # !schedule "Overwatch Night" 1/5/17 5:00PM EST "Lets play duh games."
        if message.content.startswith('!schedule'):
            tokens = message.content.split(' ')[1:]
            print("Original Tokens: {}".format(tokens))
            tokens = self.handle_quotations(tokens)
            print("Handled Tokens: {}".format(tokens))
            event_name = tokens[0].strip()
            event_date = tokens[1]
            event_time = tokens[2]
            event_timezone = tokens[3]
            event_description = tokens[4].strip()
            event_author = message.author.name

            create_event_response = self.create_event(event_name, event_date, event_time, event_timezone, event_description, event_author)

        try:
            yield from self.send_message(message.channel, create_event_response)
        except:
            print("Cannot send message.")

if __name__ == '__main__':
    bot = SchedulerBot("YOUR DISCORD KEY")
    bot.run()
