import unittest
from SchedulerBot import bot
import json

class BotTestSuite(unittest.TestCase):
    def setUp(self):
        with open('tokens.json') as jfile:
            tokens = json.load(jfile)

        self.bot = bot.SchedulerBot(tokens["discord"])

    def test_handle_quotations(self):
        self.assertEqual(self.bot.handle_quotations(["\"Overwatch", "Night\"", "yes"]), ["Overwatch Night", "yes"], "Wrong tokens returned.")

    # This test is kinda dependent on data. But it'll pass even if the db is empty.
    def test_get_data(self):
        self.assertEqual(type(self.bot.get_data("Event", field="name", field_value="Overwatch Night")), list, "List not being returned.")

    def test_get_field_names(self):
        expected_event_fields = ["description", "created_timezone", "author", "created_date", "date", "created_time", "timezone", "name", "time"]
        field_names = self.bot.get_field_names("Event")
        self.assertEqual(sorted(field_names), sorted(expected_event_fields), "Incorrect fields returned.")

    def test_is_date(self):
        self.assertEqual(self.bot.is_date("2017-01-06"), True, "Broken check of correct string dates.")
        self.assertEqual(self.bot.is_date("2017-AA-12"), False, "Broken check of incorrect string dates.")

    def test_is_time(self):
        self.assertEqual(self.bot.is_time("06:30PM"), True, "Broken check of correct string times.")
        self.assertEqual(self.bot.is_time("07:X1AM"), False, "Broken check of incorrect string times.")

    def test_is_timezone(self):
        self.assertEqual(self.bot.is_timezone("AMT"), True, "Broken check of correct string timezones.")
        self.assertEqual(self.bot.is_timezone("XXXXZZ"), False, "Broken check of incorrect string timezones.")

    def test_has_digit(self):
        self.assertEqual(self.bot.has_digit("wwwoooo0wwww"), True, "Invalid check for digit.")

if __name__ == '__main__':
    unittest.main()
