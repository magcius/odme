
from collections import defaultdict
import re
from twisted.internet import protocol
from twisted.words.protocols import irc
from twisted.application import internet, service

STREAMER = "supergreatfrien"
COUNTWORDS = [
    "red",
    "green",
    "blue",
    "leave",
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

def require_voting(func):
    def wrapper(bot, user, args):
        if not bot.voting:
            return
        func(bot, user, args)
    return wrapper

def plural(S, P, N):
    return S if N == 1 else P

def str_list(L):
    L = [w.title() for w in L]
    if len(L) == 1:
        return L[0]
    else:
        return "%s and %s" % (', '.join(L[:-1]), L[-1])

class OdmeBot(irc.IRCClient):
    nickname = 'odme'
    password = open('password', 'r').read().strip()
    username = nickname
    realname = nickname

    def signedOn(self):
        self.join(CHAN)
        self.voting = False

    def say(self, msg):
        self.msg(CHAN, msg)

    def sorted_counts(self):
        return sorted(self.countnumbers.iteritems(), key=(lambda (w, c): c), reverse=True)

    def winners(self):
        first = True
        maxcount = None
        counts = self.sorted_counts()
        if maxcount == 0:
            return []

        for i, (word, count) in enumerate(counts):
            if i == 0:
                maxcount = count
                continue
            if count != maxcount:
                break
        return counts[:i]

    def summary(self, done):
        winners = self.winners()
        if len(winners) == 0:
            self.say("Nobody voted! How did that happen?")
        else:
            word, count = winners[0]
            words = [word for word, count in winners]
            if len(winners) == 1:
                message = "%s %s with %d %s!"
                winning = "won" if done else "is winning"
            else:
                message = "It's a tie! %s %s with %d %s!"
                winning = "all won" if done else "are winning"

            self.say(message % (str_list(words), winning,
                                count, plural("vote", "votes", count)))

    def new_vote(self, extra_choices):
        self.words = COUNTWORDS + extra_choices
        self.regex = re.compile(r'\b%s\b' % (r'\b|\b'.join(self.words),))
        self.counts = defaultdict(lambda: set())
        self.update_counts()
        self.voting = True

    def end_vote(self):
        self.summary(True)
        self.voting = False

    def privmsg(self, user, channel, message):
        nick, _, host = user.partition('!')
        message = message.strip()

        if message.startswith('!'):
            self.command(nick, message[1:])
        else:
            self.count(nick, message)

    def update_counts(self):
        self.countnumbers = {}
        for word in self.words:
            self.countnumbers[word] = 0

        for user, words in self.counts.iteritems():
            for word in words:
                self.countnumbers[word] += 1

    @require_voting
    def count(self, user, message):
        message = message.lower()
        words = self.regex.findall(message)
        self.counts[user] = set(words)
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
        self.update_counts()

    def do_help(self, user, args):
        self.say("%s: Say what color you want. Don't do '!choose green' or '!vote green' like a moron. That's it!" % (user,))

    @require_mod
    def do_newvote(self, user, args):
        self.new_vote(args)

    @require_mod
    @require_voting
    def do_endvote(self, user, args):
        self.end_vote()

    @require_mod
    def do_votes(self, user, args):
        self.say("Counts for %s" % ', '.join(("%s: %d") % (word, count) for word, count in self.sorted_counts()))

    @require_mod
    def do_summary(self, user, args):
        self.summary(False)

class OdmeFactory(protocol.ReconnectingClientFactory):
    protocol = OdmeBot

application = service.Application('Odme')
ircService = internet.TCPClient(HOST, PORT, OdmeFactory())
ircService.setServiceParent(application)
