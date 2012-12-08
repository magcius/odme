
from collections import defaultdict
import random
import re
from twisted.internet import reactor, protocol
from twisted.python import log
from twisted.words.protocols import irc
from twisted.application import internet, service

STREAMER = "supergreatfrien"
COUNTWORDS = [
    "red",
    "green",
    "blue",
]

HOST = "%s.jtvirc.com" % (STREAMER,)
CHAN = "#" + STREAMER
PORT = 6667

MODS = [
    STREAMER,
    "jstpierre",
]

def require_mod(func):
    def wrapper(bot, user, args):
        if user not in MODS:
            return
        func(bot, user, args)
    return wrapper

class OdmeBot(irc.IRCClient):
    nickname = 'odme'
    password = open('password', 'r').read().strip()
    username = nickname
    realname = nickname

    def signedOn(self):
        self.join(CHAN)
        self.ignore = set()
        self.regex = re.compile(r'\b%s\b' % (r'\b|\b'.join(COUNTWORDS),))
        self.new_vote()

    def say(self, msg):
        self.msg(CHAN, msg)

    def new_vote(self):
        self.counts = defaultdict(lambda: set())
        self.update_counts()

    def privmsg(self, user, channel, message):
        nick, _, host = user.partition('!')
        message = message.strip()

        if message.startswith('!'):
            self.command(nick, message[1:])
        else:
            self.count(nick, message)

    def update_counts(self):
        self.countnumbers = {}
        for word in COUNTWORDS:
            self.countnumbers[word] = 0

        for user, words in self.counts.iteritems():
            if user in self.ignore:
                return

            for word in words:
                self.countnumbers[word] += 1

    def count(self, user, message):
        message = message.lower()
        words = self.regex.findall(message)
        self.counts[user] |= set(words)
        self.update_counts()

    def command(self, user, command):
        parts = command.split(None)
        command, args = parts[0], parts[1:]
        command = command.lower()

        func = getattr(self, 'do_%s' % (command,), None)
        if func is not None:
            func(user, args)

    def do_novote(self, user, args):
        del self.counts[user]

    @require_mod
    def do_ignore(self, user, users):
        self.ignore |= set(users)
        self.update_counts()

    @require_mod
    def do_unignore(self, user, users):
        self.ignore -= set(users)
        self.update_counts()

    @require_mod
    def do_newvote(self, user, args):
        self.new_vote()

    @require_mod
    def do_votes(self, user, args):
        self.say("Counts for %s" % ', '.join(("%s: %d") % (word, self.countnumbers[word])
                                             for word in COUNTWORDS))

    def do_choose(self, user, args):
        self.say("%s." % (random.choice(COUNTWORDS).title(),))

class OdmeFactory(protocol.ReconnectingClientFactory):
    protocol = OdmeBot

application = service.Application('Odme')
ircService = internet.TCPClient(HOST, PORT, OdmeFactory())
ircService.setServiceParent(application)
