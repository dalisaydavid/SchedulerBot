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

class InputRule:
    def __init__(self, cond, fail_msg):
        self.cond = cond
        self.fail_msg = fail_msg

    def passes(self, args):
        if isinstance(args, list):
            return self.cond(*args)
        else:
            return self.cond(args)

# @TODO: Use a RuleChecker soon.
class RuleChecker:
    def check_rules(self, rule_args):
        checked_rules = [rule_arg[0].passes(rule_arg[1]) for rule_arg in rule_args]
        return all(checked_rules)

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

    # i.e. name, start_date, created_by, deleted_by, last_modified_date, modified_by, description
    def create_event(self, event_name, event_date, event_time, event_timezone, event_description, event_author):
        table = self.db.table('Event')

        if table.search(Query().name == event_name):
            # raise AlreadyCreatedException(event_name)
            return "Event {} already created. Cannot override this event.".format(event_name)

        now_date = time.strftime("%Y-%m-%d")
        now_time = time.strftime("%I:%M%p")
        now_tz = time.tzname[0]
        now_tz_tokens = now_tz.split(" ")
        if len(now_tz_tokens) > 1:
            now_tz = "".join([token[0] for token in now_tz_tokens])

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

    # event_name, reply_status, created_by, start_date, last_modified_date
    def create_reply(self, event_name, reply_status, reply_author):
        table = self.db.table('Reply')

        event_table = self.db.table('Event')
        if not event_table.search(Query().name == event_name):
            return "This event hasn\'t been scheduled yet."

        if table.search((Query().author == reply_author) & (Query().event_name == event_name)):
            table.update({'status': reply_status}, ((Query().author == reply_author) & (Query().event_name == event_name)))
            return "Your old reply has been updated to {}.".format(reply_status)

        now_date = time.strftime("%Y-%m-%d")
        now_time = time.strftime("%I:%M %p")
        now_tz = time.tzname[0]

        reply_record = {
            'event_name': event_name, 'status': reply_status, 'author': reply_author,
            'created_date': now_date, 'created_time': now_time, 'created_timezone': now_tz
        }

        try:
            table.insert(reply_record)
            return "Your reply has been successfully recorded."
        except:
            return "Cannot insert record into the Reply table."

    def is_date(self, date):
        try:
            format_correct = isinstance(time.strptime(date, "%Y-%m-%d"), time.struct_time)
            return format_correct
        except:
            return False

    def is_time(self, time_str):
        time_str = time_str.lower()
        time_period = time_str.split(":")
        time_ = (":".join(time_period[:2]))[:-2]
        period = time_str[-2:]

        try:
            time_correct = isinstance(time.strptime(time_, '%H:%M'), time.struct_time)
            period_correct = period in ("am","pm")
            return period_correct
        except:
            return False

#    def is_timezone(self, tz):


    @asyncio.coroutine
    def on_message(self, message):
        # !schedule "Overwatch Night" 2017-01-11 5:00PM EST "Lets play duh games."
        if message.content.startswith('!schedule'):
            tokens = message.content.split(' ')[1:]
            tokens = self.handle_quotations(tokens)
            event_name = tokens[0].strip()
            event_date = tokens[1]
            event_time = tokens[2]
            event_timezone = tokens[3]
            event_description = tokens[4].strip()
            event_author = message.author.name

            # Setup input rules to check inputs.
            date_rule = InputRule(self.is_date, "Invalid date format. Use: YYYY-MM-DD i.e. 2017-01-01")
            time_rule = InputRule(self.is_time, "Invalid time format. Use: HH:MMPP i.e. 07:58PM")

            if date_rule.passes(event_date) is False:
                create_event_response = date_rule.fail_msg
            elif time_rule.passes(event_time) is False:
                create_event_response = time_rule.fail_msg
            else:
                create_event_response = self.create_event(event_name, event_date, event_time, event_timezone, event_description, event_author)

            yield from self.send_message(message.channel, create_event_response)

        # !reply "Overwatch Night" yes
        elif message.content.startswith('!reply'):
            tokens = message.content.split(' ')[1:]
            tokens = self.handle_quotations(tokens)

            event_name = tokens[0].strip()
            reply_status = tokens[1].strip()
            reply_author = message.author.name

            reply_rule = InputRule(lambda v1: (v1.lower() in ("yes","no","maybe")), "Invalid reply status. Use: yes, no, or maybe.")
            if not reply_rule.passes(reply_status):
                create_reply_response = reply_rule.fail_msg
            else:
                create_reply_response = self.create_reply(event_name, reply_status, reply_author)

            yield from self.send_message(message.channel, create_reply_response)

        # !events today
        elif message.content.startswith('!events'):
            tokens = message.content.split(' ')[1:]


if __name__ == '__main__':
    bot = SchedulerBot("Discord API Key")
    bot.run()
