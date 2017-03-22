import asyncio
import json
import time
from datetime import datetime, timedelta
import sys
import discord
import unicodedata
from tinydb import TinyDB, Query, where
from tinydb.operations import delete
import operator

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
class InputRuleChecker:
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

		# Represents all available commands and how to use them.
		# @TODO: Make command classes?!
		#!schedule "Hearthstone Tourney 4" 2017-06-07 7:30PM PST "Bring your best decks!"
		self.commands = {
			"!schedule": {
				"examples": ["!schedule \"Game Night\" 2017-06-01 05:30PM PST \"Bring your own beer.\""]
			},
			"!reply": {
				"examples": ["!reply \"Game Night\" yes"]
			},
			"!events": {
				"examples": ["!events 2017-06-01"]
			},
			"!scheduler-bot": {
				"examples": ["!scheduler-bot"]
			},
			"!delete-event":{
				"examples": ["!delete-event \"Game Night\""]
			},
			"!edit-event":{
				"examples": ["!edit-event \"Game Night\" date 2017-06-06 time 5:30PM"]
			}
			#,
			#"!remind":{
			#	"examples": ["!remind \"Game Night\" 30 minutes"]
			#}

		}


	@asyncio.coroutine
	def check_for_reminders(self, task_name, seconds_to_sleep=3):
		while True:
			yield from asyncio.sleep(seconds_to_sleep)
			now = datetime.now().strftime("%Y-%m-%d %I:%M:%p")
			reminders = self.get_data("Reminder", "reminder_datetime", now)
			if len(reminders) > 0:
				yield from self.handle_reminders(reminders)


	def main(self):
		pass
		# @TODO: Commenting this out for reminders.
		# loop = asyncio.get_event_loop()
		# try:
			# asyncio.async(self.check_for_reminders('reminder_task',1))
			# asyncio.async(self.run())
			# loop.run_forever()
		# except KeyboardInterrupt:
			# pass
		# finally:
			# print('step: loop.close()')
			# loop.close()

	def run(self):
		print("superclass being called...")
		# Calling superclass to do discord.Client's run.
		super(SchedulerBot, self).run(self.discord_token)

	# Discord client function that is called when the bot has logged into the registered server.
	@asyncio.coroutine
	def on_ready(self):
		print('Logged in as')
		print(self.user.name)
		print(self.user.id)
		print('------')
	
	# Bot function that handles the reminders of a certain time and alerts all attendies.
	@asyncio.coroutine
	def handle_reminders(self, reminders):
		names = [reminder["attendie"] for reminder in reminders]
		reminders_by_name = {}
		for reminder in reminders:
			if reminder["attendie"] not in reminders_by_name:
				reminders_by_name[reminder["attendie"]] = []
			reminders_by_name[reminder["attendie"]].append(reminder)
				
		print("Handling unique reminders for the following events: {}".format(set([reminder["event_name"] for reminder in reminders])))
		for i in self.get_all_members():
			if i.name in names:
				user = i
				for reminder in reminders_by_name[i.name]:
					event_date = self.get_data(table_name="Event", field="name", field_value=reminder["event_name"])[0]["date"]
					event_time = self.get_data(table_name="Event", field="name", field_value=reminder["event_name"])[0]["time"]
					event_timezone = self.get_data(table_name="Event", field="name", field_value=reminder["event_name"])[0]["timezone"]
					yield from self.send_message(user, 'Reminding you that {} starts at {} {} {}.'.format(reminder["event_name"],event_date,event_time,event_timezone))
				self.delete_reminder(reminders_by_name[i.name])
				break

	# Delete reminder from db.
	def delete_reminder(self, reminders):
		for reminder in reminders:
			self.db.table("Reminder").remove(eids=[reminder.eid])
		#self.db.table("Reminder").update(delete('eid'), where('eid') == reminder["eid"])
		#self.db.update(delete(), User.name == 'John')

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
	# @TODO: Allow this function to query multiple parameters at once
	# @TODO: Allow this function to look at differ
	def get_data(self, table_name, field=None, field_value=None):
		table = self.db.table(table_name)
		if field:
			all_results = table.search(Query()[field] == field_value)
		else:
			all_results = table.all()
		return all_results

	# Database helper function that gets all the field names from a given table.
	def get_field_names(self, table_name):
		table = self.db.table(table_name)
		all_keys = table.all()[0].keys()
		return all_keys

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

	# Bot function that edits an event that has already been created.
	# @format field_values: {"name": "event1", "date": 2017-01-01}
	def edit_event(self, event_name, reply_author, field_values):
		table = self.db.table("Event")

		response = ""

		if table.search(Query().name == event_name):
			if table.search((Query().author == reply_author) & (Query().name == event_name)):
				table.update(field_values, ((Query().author == reply_author) & (Query().name == event_name)))
				# If date, time, or timezone changed in the event, delete the reminder and make a new one with the updated times.
				#if set(["date","time","timezone"]).intersection(set(field_values.keys())):
					#reminder_data = [(reminder_record['attendie'], reminder_record['time_metric'], reminder_record['diff_value']) for reminder_record in self.get_data('Reminder', 'event_name', event_name)] 
					# print("Editing event, reminder_data: {}".format(reminder_data))
					# self.delete_reminders_by_event_name(event_name, reply_author)
					#for reminder in reminder_data:
						# self.create_reminder(event_name, reminder[0], reminder[1], reminder[2])
				response += "Event table has been edited with new values: {}".format(field_values)
			else:
				response += "You do not have permission to edit this event."
		else:
			response += "Event {} does not exist.".format(event_name)

		return response

	# Database function that creates a reminder in the database.
	def create_reminder(self, event_name, attendie, time_metric, diff_value):
		event_data = self.get_data('Event', 'name', event_name)[0]
		event_time = event_data['time']
		event_date = event_data['date']
		
		reminder_table = self.db.table('Reminder')
		
		reply_data = [reply_record for reply_record in self.get_data('Reply') if reply_record['event_name'] == event_name and reply_record['author'] == attendie and reply_record['status'] == 'yes']
		if len(reply_data) <= 0:
			return "Attendie did not reply yes to the event."
		if time_metric not in ("minutes","hours","days"):
			return "Invalid time metric."
		print("event_date: {}, event_time: {}".format(event_date, event_time))
		event_dt = datetime.strptime(" ".join((event_date, event_time)), '%Y-%m-%d %I:%M%p')

		if time_metric == "minutes":
			reminder_dt = event_dt - timedelta(minutes=diff_value)
		elif time_metric == "hours":
			reminder_dt = event_dt - timedelta(hours=diff_value)
		elif time_metric == "days":
			reminder_dt = event_dt - timedelta(days=diff_value)

		reminder_dt = reminder_dt.strftime("%Y-%m-%d %I:%M:%p")	
		print("reminder_dt: {}".format(reminder_dt))

		reply_data = self.get_data('Reply', 'event_name', event_name)
		print("attendie: {}".format(attendie))
		reminder_record = {
			"event_name": event_name,
			"attendie": attendie,
			"reminder_datetime": reminder_dt,
			"time_metric": time_metric,
			"diff_value": diff_value,
			"is_sent": False
		}
		try:
			reminder_table.insert(reminder_record)
		except:
			return "Reminder not recorded into db. Check connection."

		return "Reminder set. You'll be alerted {} {} before {} begins.".format(diff_value, time_metric, event_name) 

		# @TODO finish reminder stuff right here.

	# Bot function that creates a reply [to an event] in the database.
	def create_reply(self, event_name, reply_status, reply_author):
		reply_table = self.db.table('Reply')

		# Checks if the event has been created.
		# If it hasn't been created, there is no event to reply to.
		event_table = self.db.table('Event')
		if not event_table.search(Query().name == event_name):
			return "This event hasn\'t been scheduled yet."

		# Checks if the user has already submitted a reply to this event.
		# If they have already replied, the reply is overwritten and the user is notified of it's updated value.
		if reply_table.search((Query().author == reply_author) & (Query().event_name == event_name)):
			reply_table.update({'status': reply_status}, ((Query().author == reply_author) & (Query().event_name == event_name)))
			#if reply_status == "yes":
				# print(self.create_reminder(event_name, reply_author, "hours", 1))
				#print(self.create_reminder(event_name, reply_author, "days", 1))
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
			reply_table.insert(reply_record)
			#if reply_status == "yes":
				# Create error handling for this. @TODO
				# print(self.create_reminder(event_name, reply_author, "hours", 1))
			#	print(self.create_reminder(event_name, reply_author, "days", 1))
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

	# Helper function that determines whether or not a string is a valid time zone abbreviation.
	def is_timezone(self, tz_str):
		known_timezones = [
			"ACDT",     "ACST", "ACT",  "ACT",  "ADT",  "AEDT", "AEST", "AFT",  "AKDT", "AKST", "AMST", "AMT",  "AMT",  "ART",  "AST",  "AST",  "AWST", "AZOST",        "AZOT", "AZT",
			"BDT",      "BIOT", "BIT",  "BOT",  "BRST", "BRT",  "BST",  "BST",  "BST",  "BTT",  "CAT",  "CCT",  "CDT",  "CDT",  "CEST", "CET",  "CHADT",        "CHAST",        "CHOT", "CHOST",
			"CHST",     "CHUT", "CIST", "CIT",  "CKT",  "CLST", "CLT",  "COST", "COT",  "CST",  "CST",  "ACST", "ACDT", "CST",  "CT",   "CVT",  "CWST", "CXT",  "DAVT", "DDUT",
			"DFT",      "EASST", "EAST",        "EAT",  "ECT",  "ECT",  "EDT",  "AEDT", "EEST", "EET",  "EGST", "EGT",  "EIT",  "EST",  "AEST", "FET",  "FJT",  "FKST", "FKT",  "FNT",
			"GALT",     "GAMT", "GET",  "GFT",  "GILT", "GIT",  "GMT",  "GST",  "GST",  "GYT",  "HADT", "HAEC", "HAST", "HKT",  "HMT",  "HOVST",        "HOVT", "ICT",  "IDT",  "IOT",
			"IRDT",     "IRKT", "IRST", "IST",  "IST",  "IST",  "JST",  "KGT",  "KOST", "KRAT", "KST",  "LHST", "LHST", "LINT", "MAGT", "MART", "MAWT", "MDT",  "MET",  "MEST",
			"MHT",      "MIST", "MIT",  "MMT",  "MSK",  "MST",  "MST",  "MUT",  "MVT",  "MYT",  "NCT",  "NDT",  "NFT",  "NPT",  "NST",  "NT",   "NUT",  "NZDT", "NZST", "OMST",
			"ORAT",     "PDT",  "PET",  "PETT", "PGT",  "PHOT", "PHT",  "PKT",  "PMDT", "PMST", "PONT", "PST",  "PST",  "PYST", "PYT",  "RET",  "ROTT", "SAKT", "SAMT", "SAST",
			"SBT",      "SCT",  "SGT",  "SLST", "SRET", "SRT",  "SST",  "SST",  "SYOT", "TAHT", "THA",  "TFT",  "TJT",  "TKT",  "TLT",  "TMT",  "TRT",  "TOT",  "TVT",  "ULAST",
			"ULAT",     "USZ1", "UTC",  "UYST", "UYT",  "UZT",  "VET",  "VLAT", "VOLT", "VOST", "VUT",  "WAKT", "WAST", "WAT",  "WEST", "WET",  "WIT",  "WST",  "YAKT", "YEKT"
		]

		return (tz_str in known_timezones)

	# Helper function that determines whether or not a string has a digit.
	# This is used as quick hack to look for  strings that may have dates.
	def has_digit(self, input_str):
		return any(char.isdigit() for char in input_str)

	# Helper function that determines whether or not an event exists.
	def event_exists(self, event_name):
		table = self.db.table("Event")
		return len(table.search(Query().name == event_name)) > 0

	# String formatter function that determines how the events are displayed in the Discord client.
	def format_events(self, events):
		events_str = "**EVENTS**\n"
		events_str += "```{:12} {:25} {:10} {:6} {:8}\n".format("Host", "Name", "Date", "Time", "Timezone")

		# Sort the events by date.
		date_string = '2009-11-29 03:17 PM'
		events_by_datetime = { event["name"]:(datetime.strptime(event["date"] + " " + event["time"],'%Y-%m-%d %I:%M%p')) for event in events}
		sorted_events = sorted(events_by_datetime.items(), key=lambda p: p[1], reverse=False)
		print("events_sorted_by_datetime: {}".format(sorted_events))
	
		for target_event in sorted_events:	
			for event in events:
				if target_event[0] == event["name"]:
					author = event["author"]
					name = event["name"]
					date = event["date"]
					time = event["time"]
					timezone = event["timezone"]

					events_str += "{:12} {:25} {:10} {:6} {:8}\n".format(author, name if len(name) < 25 else name[:22]+"...", date, time, timezone)
					break

		events_str += "```"

		# Just for debugging purposes.
		print("events_str: {}".format(events_str))

		return events_str

	# String formatter function that determines how single events are displayed in the Discord client.
	def format_single_event(self, event, replies):
		event_str = "**{}**".format(event["name"])
		event_str += "```{:12} {:15} {:10} {:6} {:8}\n".format("Host", "Name", "Date", "Time", "Timezone")

		author = event["author"]
		name = event["name"]
		date = event["date"]
		time = event["time"]
		timezone = event["timezone"]
		desc = event["description"]

		event_str += "{:12} {:15} {:10} {:6} {:8}\n\n{}\n\n".format(author, name[:15], date, time, timezone, desc)

		reply_statuses = {"yes": [], "no": [], "maybe": []}

		for reply in replies:
			user = reply["author"]
			status = reply["status"]
			reply_statuses[status].append(user)

		event_str += "Yes: {}\n".format(", ".join(reply_statuses["yes"]))
		event_str += "No: {}\n".format(", ".join(reply_statuses["no"]))
		event_str += "Maybe: {}".format(", ".join(reply_statuses["maybe"]))

		event_str += "```"

		return event_str

	# Bot function that deletes certain reminders from the database based on the event name.
	def delete_reminders_by_event_name(self, event_name, author):
		event_table = self.db.table("Event")

		if not event_table.search(Query().name == event_name):
			return "Event {} not in the table.".format(event_name)
		elif not event_table.search((Query().author == author) & (Query().name == event_name)):
			return "You do not have permission to delete this event."

		reminder_table = self.db.table("Reminder")
	
		# Remove all reminders from the reminder table with that event name.
		try:
			reminder_table.remove(Query().event_name == event_name)
		except:
			return "Cannot connect to Reminder table."

		return "Reminders successfully deleted for event {}.".format(event_name)

	# Bot function that deletes a certain event from the database.
	def delete_event(self, event_name, reply_author):
		event_table = self.db.table("Event")
		reply_table = self.db.table("Reply")
		#reminder_table = self.db.table("Reminder")

		if not event_table.search(Query().name == event_name):
			return "Event {} not in the table.".format(event_name)
		elif not event_table.search((Query().author == reply_author) & (Query().name == event_name)):
			return "You do not have permission to delete this event."

		# Remove event from event table.
		try:
			event_table.remove(Query().name == event_name)
		except:
			return "Cannot connect to the Event table."

		# Remove all replies from the reply table with that event name.
		try:
			reply_table.remove(Query().event_name == event_name)
		except:
			return "Cannot connect to the Reply table."

		# Remove all reminders from the reminder table with that event name.
		# try:
			# reminder_table.remove(Query().event_name == event_name)
		#except:
			#return "Cannot connect to Reminder table."

		return "Event successfully deleted."


	# Discord client function that determines how to handle a new message when it appears on the Discord server.
	@asyncio.coroutine
	def on_message(self, message):
		tokens = message.content.split(' ')
		tokens = [str(token) for token in tokens]
		bot_command = tokens[0].lower()
		# !schedule command.
		if bot_command == '!schedule':
			tokens = tokens[1:]

			if len(tokens):
				tokens = self.handle_quotations(tokens)
				if len(tokens) > 5:
					create_event_response = "Invalid input: too many parameters."
				else:
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
			else:
				create_event_response = "Invalid input: not enough inputs."
			
			yield from self.send_message(message.channel, create_event_response)

		# !reply command.
		elif bot_command == '!reply':
		#	print("message.author: {}, type(message.author): {}".format(message.author, type(message.author)))
			tokens = tokens[1:]
			if len(tokens) >= 2:
				tokens = self.handle_quotations(tokens)

				if len(tokens) == 2:
					event_name = tokens[0].strip()
					reply_status = tokens[1].strip().lower()
					reply_author = message.author.name

					event_created_rule = InputRule(self.event_exists, "Invalid input. Event not yet created.")
					reply_rule = InputRule(lambda v1: (v1 in ("yes","no","maybe")), "Invalid input. Use: yes, no, or maybe.")
					if not event_created_rule.passes(event_name):
						create_reply_response = event_created_rule.fail_msg
					elif not reply_rule.passes(reply_status):
						create_reply_response = reply_rule.fail_msg
					else:
						create_reply_response = self.create_reply(event_name, reply_status, reply_author)
				else:
					create_reply_response = "Invalid input: Too many parameters."
			else:
				create_reply_response = "Invalid input: Not enough inputs. Provide event name and reply status."

			yield from self.send_message(message.channel, create_reply_response)

		# !events command.
		elif bot_command == '!events':
			tokens = tokens[1:]
			if tokens:
				if len(tokens) == 1:
					date = tokens[0].lower()

					# Setup input rules to check inputs.
					date_rule = InputRule(self.is_date, "Invalid date format. Use: YYYY-MM-DD i.e. 2017-01-01")
					today_tomorrow_rule = InputRule(lambda x: x.lower() in ("today","tomorrow"), "Invalid day format. Use: today or tomorrow.")

					if self.has_digit(date):
						if not date_rule.passes(date):
							create_events_response = date_rule.fail_msg
						else:
							all_events_str = self.format_events(self.get_data("Event","date", date))
							create_events_response = all_events_str
					else:
						if not today_tomorrow_rule.passes(date):
							create_events_response = today_tomorrow_rule.fail_msg
						else:
							date_ = datetime.now().strftime("%Y-%m-%d") if date == "today" else (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
							all_events_str = self.format_events(self.get_data("Event","date", date_))
							create_events_response = all_events_str
				else:
					create_events_response = "Invalid input: Too many parameters."
			else:
				create_events_response = self.format_events(self.get_data("Event"))

			yield from self.send_message(message.channel, create_events_response)

		elif bot_command == '!event':
			tokens = tokens[1:]
			if tokens:
				tokens = self.handle_quotations(tokens)

				if len(tokens) == 1:
					event_name = tokens[0]
					all_events = self.get_data("Event", "name", event_name)
					all_replies = self.get_data("Reply", "event_name", event_name)

					if len(all_events) > 0:
						event_response = self.format_single_event(all_events[0], all_replies)
					else:
						event_response = "Invalid input: event not yet created."
				else:
					event_response = "Invalid input: Too many parameters."
			else:
				event_response = "Invalid input: no event name."

			yield from self.send_message(message.channel, event_response)

		# !scheduler-bot command. (list commands)
		elif bot_command == '!scheduler-bot' and len(tokens) == 1:
			list_commands_response = "**COMMANDS**\n```"
			for command in list(self.commands.keys()):
				list_commands_response += "{}: \n\t {}\n\n".format(command, self.commands[command]["examples"][0])
			list_commands_response += "```"

			yield from self.send_message(message.channel, list_commands_response)

		# !delete-event command.
		elif bot_command == '!delete-event':
			tokens = tokens[1:]
			if tokens:
				tokens = self.handle_quotations(tokens)

				if len(tokens) == 1:
					event_name = tokens[0]
					reply_author = message.author.name
					all_events = self.get_data("Event", "name", event_name)

					if len(all_events) > 0:
						delete_event_response = self.delete_event(event_name,reply_author)
					else:
						delete_event_response = "Invalid input: event not yet created."
				else:
					delete_event_response = "Invalid input: Too many parameters."
			else:
				delete_event_response = "Invalid input: no event name."

			yield from self.send_message(message.channel, delete_event_response)

		# !remind command.
		# !remind OverwatchNight 2 days
		elif bot_command == "!remind":
			tokens = tokens[1:]
			if tokens:
				if len(tokens) < 3:
					remind_response = "Invalid input: missing arguments."
				else:	
					tokens = self.handle_quotations(tokens)
					event_table = self.db.table('Event')
					reply_table = self.db.table('Reply')
					if not event_table.search(Query().name == tokens[0]):
						remind_response = "Invalid input: This event hasn\'t been scheduled yet."
					elif not tokens[1].isdigit():
						remind_response = "Invalid input: bad numeric."
					elif not tokens[2] in ["minutes","hours","days"]:
						remind_response = "Invalid input: did not use 'minutes','hours', or 'days'."
					elif not reply_table.search((Query().author == message.author.name) & (Query().event_name == tokens[0])):
						remind_response = "Invalid input: User has not replied 'yes' to the event."
					else:
						remind_response = self.create_reminder(tokens[0], message.author.name,  tokens[2], int(tokens[1]))
			else:
				remind_response = "Invalid input: no event name."
			
			yield from self.send_message(message.channel, remind_response)

		# !edit-event command.
		# !edit OverwatchNight date 1/6/17 time 5:30PM
		# @TODO: InputRule for time and timezone.
		elif bot_command == '!edit-event':
			tokens = tokens[1:]
			if tokens:
				tokens = self.handle_quotations(tokens)
				event_name = tokens[0]
				event_author = message.author.name

				if len(tokens) <= 1:
					edit_event_response = "No fields given to edit."
				else:
					tokens = tokens[1:]

					if len(tokens) % 2 == 0:
						is_event_field_rule = InputRule(lambda x: x.lower() in self.get_field_names("Event"), "Field does not exist.")
						date_rule = InputRule(self.is_date, "Invalid date format. Use: YYYY-MM-DD i.e. 2017-01-01")
						time_rule = InputRule(self.is_time, "Invalid time format. Use: HH:MMPP i.e. 07:58PM")
						timezone_rule = InputRule(self.is_timezone, "Invalid timezone abbreviation.")

						field_values = {}
						rule_fail = False
						for p in range(0, len(tokens), 2):
							if not is_event_field_rule.passes(tokens[p]):
								return is_event_field_rule.fail_msg
							else:
								# @TODO Rulechecker would fix this awful redundancy.
								if tokens[p] == "date":
									if not date_rule.passes(tokens[p+1]):
										edit_event_response = date_rule.fail_msg
										rule_fail = True
										break
								elif tokens[p] == "time":
									if not time_rule.passes(tokens[p+1]):
										edit_event_response = time_rule.fail_msg
										rule_fail = True
										break
								elif tokens[p] == "timezone":
									if not timezone_rule.passes(tokens[p+1]):
										edit_event_response = timezone_rule.fail_msg
										rule_fail = True
										break

								field_values[tokens[p]] = tokens[p+1]

						if not rule_fail:
							edit_event_response = self.edit_event(event_name, event_author, field_values)
					else: edit_event_response = "Invalid input: incorrect number of parameters."
			else:
				edit_event_response = "Invalid input: no event name."

			yield from self.send_message(message.channel, edit_event_response)
