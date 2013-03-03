
COUNTWORDS = [
    "red",
    "blue",
    "green",
    "leave",
]

SPECIAL_COLORS = {
    "red": "red",
    "blue": "#1DB7D3",
    "green": "#1DD32A",
    "leave": "#D3661D",
}

FONT = "Arial 24 bold"

STREAMER = "supergreatfrien"

HOST = "%s.jtvirc.com" % (STREAMER,)
CHAN = "#" + STREAMER
PORT = 6667

MODS = [
    STREAMER,
    "jstpierre",
]

import Tkinter

def stop_reactor():
    from twisted.internet import reactor
    reactor.stop()

class CounterGUI(object):
    def __init__(self):
        self.root = Tkinter.Tk()
        self.root.protocol('WM_DELETE_WINDOW', stop_reactor)

        self.frame = Tkinter.Frame(self.root)
        self.frame.pack(expand=True, fill=Tkinter.X)

        self.novote_label = Tkinter.Label(self.frame, text="No vote.", font=FONT)
        self.pack_label(self.novote_label)

        self.labels = {}

    def pack_label(self, label):
        label.pack(side="left", padx=6, expand=True)

    def make_choice_label(self, choice):
        if choice in SPECIAL_COLORS:
            color = SPECIAL_COLORS[choice]
        else:
            color = "black"

        label = Tkinter.Label(self.frame, fg=color, font=FONT)
        self.pack_label(label)
        self.labels[choice] = label
        return label

    def end_vote(self):
        for label in self.labels.itervalues():
            label.destroy()

        self.pack_label(self.novote_label)

    def new_vote(self, choices):
        self.novote_label.pack_forget()

        for choice in choices:
            self.make_choice_label(choice)

    def needs_text_prefix(self, choice):
        return choice not in SPECIAL_COLORS

    def get_choice_text(self, choice, count):
        if self.needs_text_prefix(choice):
            return "%s: %02d" % (choice.title(), count)
        else:
            return "%02d" % (count,)

    def update_counts(self, countnumbers):
        for choice, count in countnumbers.iteritems():
            self.labels[choice]["text"] = self.get_choice_text(choice, count)

gui = CounterGUI()

from twisted.internet import tksupport
tksupport.install(gui.root)

from collections import defaultdict
import re
from twisted.internet import protocol
from twisted.words.protocols import irc
from twisted.application import internet, service

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
        maxcount = None
        counts = self.sorted_counts()

        for i, (word, count) in enumerate(counts):
            if maxcount is None:
                maxcount = count
                continue

            if count != maxcount:
                break

        if maxcount is None:
            return []

        return counts[:i]

    def summary(self, done):
        winners = self.winners()
        if len(winners) != 0:
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
        gui.new_vote(self.words)

        self.regex = re.compile(r'\b%s\b' % (r'\b|\b'.join(self.words),))
        self.counts = defaultdict(lambda: set())
        self.update_counts()
        self.voting = True

    def end_vote(self):
        self.summary(True)
        self.voting = False
        gui.end_vote()

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

        gui.update_counts(self.countnumbers)

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
