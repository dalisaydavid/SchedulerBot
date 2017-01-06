import asyncio
import json
import time
from datetime import datetime, timedelta
import discord
from tinydb import TinyDB, Query

# Class that represents a rule in order to check discord command inputs.
# InputRule checks if the arguments of those discord commands pass or fail.
# And then provides a fail message if it fails.
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

# Represents the Discord bot.
class SchedulerBot(discord.Client):
    def __init__(self, discord_token):
        super(SchedulerBot, self).__init__()

        self.discord_token = discord_token

        # Represents very small database inside a json file using TinyDB
        self.db = TinyDB("db.json")

    def run(self):
        # Calling superclass to do discord.Client's run.
        super(SchedulerBot, self).run(self.discord_token)

    # Discord client function that is called when the bot has logged into the registered server.
    @asyncio.coroutine
    def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    # Helper function that handles tokens captured within quotations.
    # If there are tokens captured in two quotes, it will treat said tokens as a single token.
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

    # Database helper function that strictly pulls events from the database.
    # Pulls events based on desired fields.
    # @param: field="date", field_value="2017-01-06"
    # @TODO: Allow this function to query multiple parameters at once.
    def get_events(self, field=None, field_value=None):
        table = self.db.table('Event')
        if field:
            all_events = table.search(Query()[field] == field_value)
        else:
            all_events = table.all()
        return all_events

    # Bot function that creates an event in the database.
    def create_event(self, event_name, event_date, event_time, event_timezone, event_description, event_author):
        table = self.db.table('Event')

        # Checks if the event has already been created.
        # If it has, don't override the event.
        if table.search(Query().name == event_name):
            return "Event {} already created. Cannot override this event.".format(event_name)

        # Calculates the date, time, and timezone that the event was created.
        # This helps with logging purposes.
        now_date = time.strftime("%Y-%m-%d")
        now_time = time.strftime("%I:%M%p")
        now_tz = time.tzname[0]
        now_tz_tokens = now_tz.split(" ")
        if len(now_tz_tokens) > 1:
            now_tz = "".join([token[0] for token in now_tz_tokens])

        # Create the dictionary that represents the record in the event table.
        event_record = {
            'name': event_name, 'date': event_date, 'time': event_time, 'timezone': event_timezone,
            'description': event_description, 'author': event_author, 'created_date': now_date,
            'created_time': now_time, 'created_timezone': now_tz
        }

        # Try to insert the record into the table.
        try:
            table.insert(event_record)
            return "{} event successfully recorded. Others may now reply to this event.".format(event_name)
        except:
            return "Cannot insert record into the Event table."

    # Bot function that creates a reply [to an event] in the database.
    def create_reply(self, event_name, reply_status, reply_author):
        table = self.db.table('Reply')

        # Checks if the event has been created.
        # If it hasn't been created, there is no event to reply to.
        event_table = self.db.table('Event')
        if not event_table.search(Query().name == event_name):
            return "This event hasn\'t been scheduled yet."

        # Checks if the user has already submitted a reply to this event.
        # If they have already replied, the reply is overwritten and the user is notified of it's updated value.
        if table.search((Query().author == reply_author) & (Query().event_name == event_name)):
            table.update({'status': reply_status}, ((Query().author == reply_author) & (Query().event_name == event_name)))
            return "Your old reply has been updated to {}.".format(reply_status)


        # Calculates the date, time, and timezone that the event was created.
        # This helps with logging purposes.
        now_date = time.strftime("%Y-%m-%d")
        now_time = time.strftime("%I:%M %p")
        now_tz = time.tzname[0]

        # Create the dictionary that represents the record in the reply table.
        reply_record = {
            'event_name': event_name, 'status': reply_status, 'author': reply_author,
            'created_date': now_date, 'created_time': now_time, 'created_timezone': now_tz
        }

        # Try to insert the record into the table.
        try:
            table.insert(reply_record)
            return "Your reply has been successfully recorded."
        except:
            return "Cannot insert record into the Reply table."

    # Helper function that determines whether or not a string is of the correct date format.
    # @param: date i.e. "2017-06-01"
    def is_date(self, date):
        # Try to convert the date into a struct_time. If it works, it's of a correct format.
        try:
            format_correct = isinstance(time.strptime(date, "%Y-%m-%d"), time.struct_time)
            return format_correct
        except:
            return False

    # Helper function that determines whether or not a string is of the correct time format.
    # @param: time_str i.e. "5:30PM"
    def is_time(self, time_str):
        time_str = time_str.lower()
        time_period = time_str.split(":")
        time_ = (":".join(time_period[:2]))[:-2]
        period = time_str[-2:]

        # Try to convert the date into a struct_time. If it works, it's of a correct format.
        try:
            time_correct = isinstance(time.strptime(time_, '%H:%M'), time.struct_time)
            period_correct = period in ("am","pm")
            return period_correct
        except:
            return False

    # Helper function that determines whether or not a string has a digit.
    # This is used as quick hack to look for input strings that may have dates.
    def has_digit(self, input_str):
        return any(char.isdigit() for char in input_str)

    # String formatter function that determines how the events are displayed in the Discord client.
    def format_events(self, events):
        events_str = "**EVENTS**\n"
        events_str += "```{:12} {:15} {:10} {:6} {:8}\n".format("Author", "Name", "Date", "Time", "Timezone")
        for event in events:
            author = event["author"]
            name = event["name"]
            date = event["date"]
            time = event["time"]
            timezone = event["timezone"]

            events_str += "{:12} {:15} {:10} {:6} {:8}\n".format(author, name[:15], date, time, timezone)

        events_str += "```"

        # Just for debugging purposes.
        print("events_str: {}".format(events_str))

        return events_str

    # Discord client function that determines how to handle a new message when it appears on the Discord server.
    @asyncio.coroutine
    def on_message(self, message):

        # !schedule command.
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

        # !reply command.
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

        # !events command.
        elif message.content.startswith('!events'):
            tokens = message.content.split(' ')[1:]
            if tokens:
                date = tokens[0].lower()

                # Setup input rules to check inputs.
                date_rule = InputRule(self.is_date, "Invalid date format. Use: YYYY-MM-DD i.e. 2017-01-01")
                today_tomorrow_rule = InputRule(lambda x: x.lower() in ("today","tomorrow"), "Invalid day format. Use: today or tomorrow.")

                if self.has_digit(date):
                    if not date_rule.passes(date):
                        create_events_response = date_rule.fail_msg
                    else:
                        all_events_str = self.format_events(self.get_events("date", date))
                        create_events_response = all_events_str
                else:
                    if not today_tomorrow_rule.passes(date):
                        create_events_response = today_tomorrow_rule.fail_msg
                    else:
                        date_ = datetime.now().strftime("%Y-%m-%d") if date is "today" else (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                        all_events_str = self.format_events(self.get_events("date", date_))
                        create_events_response = all_events_str
            else:
                create_events_response = self.format_events(self.get_events())

            yield from self.send_message(message.channel, create_events_response)

        


if __name__ == '__main__':
    with open('tokens.json') as jfile:
        tokens = json.load(jfile)

    bot = SchedulerBot(tokens["discord"])
    bot.run()
