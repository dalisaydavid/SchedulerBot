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
