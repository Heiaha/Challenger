import os
import berserk
import random
import requests
import re
import datetime

LICHESS_BOT_TOKEN = os.environ.get('LICHESS_BOT_TOKEN')
session = berserk.TokenSession(LICHESS_BOT_TOKEN)
client = berserk.Client(session)

RATING_MAX = 300
TOTAL_GAMES_MIN = 250
TC_GAMES_MIN = 50
TIME_MIN = datetime.timedelta(minutes=10)

TIME_CONTROL_MAP = {
    60: 'bullet',
    120: 'bullet',
    180: 'blitz',
    300: 'blitz',
    600: 'rapid',
    900: 'rapid',
    1200: 'classical',
    1800: 'classical',
}


class Bot:
    def __init__(self, info):
        self.last_seen = info['seenAt'].replace(tzinfo=None)
        self.name = info['username']
        self._ratings = {
            'bullet': info['perfs']['bullet']['rating'],
            'blitz': info['perfs']['blitz']['rating'],
            'rapid': info['perfs']['rapid']['rating'],
            'classical': info['perfs']['classical']['rating']
        }
        self._num_games = {
            'bullet': info['perfs']['bullet']['games'],
            'blitz': info['perfs']['blitz']['games'],
            'rapid': info['perfs']['rapid']['games'],
            'classical': info['perfs']['classical']['games'],
        }

    @property
    def total_games(self):
        return sum(self._num_games.values())

    def num_games(self, tc_name):
        return self._num_games[tc_name]

    def rating(self, tc_name):
        return self._ratings[tc_name]

    def challenge(self, tc_seconds):
        client.challenges.create(self.name,
                                 rated=True,
                                 clock_limit=tc_seconds,
                                 clock_increment=0,
                                 days=1,
                                 # for some reason it requires days to be equal to 1 even though we're not
                                 # trying to do correspondence?
                                 color=random.choice([berserk.enums.Color.WHITE, berserk.enums.Color.BLACK]),
                                 variant=berserk.enums.Variant.STANDARD,
                                 position="")

    @classmethod
    def get_all(cls):
        # get a list of bots
        r = requests.get("https://lichess.org/player/bots")
        bot_names = re.findall(r"(?<=user=).*?(?=#friend)", r.text)

        # request the bot info from lichess
        bots_info = client.users.get_by_id(*bot_names)

        return [cls(bot_info) for bot_info in bots_info]


def main():
    # return if we're already playing a game
    if client.games.get_ongoing(count=1):
        print('Playing a game. Will not challenge.')
        return

    # select a time control to play
    tc_seconds, tc_name = random.choice(list(TIME_CONTROL_MAP.items()))

    bots = Bot.get_all()
    random.shuffle(bots)

    me = next(bot for bot in bots if bot.name == 'Weiawaga')
    my_rating = me.rating(tc_name)

    now = datetime.datetime.utcnow()
    for bot in bots:

        if bot == me:
            print('Don\'t challenge myself.')
            continue

        if now - bot.last_seen > TIME_MIN:
            print(f'Skipping {bot.name}: not seen in too long.')
            continue

        if abs(bot.rating(tc_name) - my_rating) > RATING_MAX:
            print(f'Skipping {bot.name}: rating difference too large.')
            continue

        if bot.num_games(tc_name) < TC_GAMES_MIN or bot.total_games < TOTAL_GAMES_MIN:
            print(f'Skipping {bot.name}: too few games.')
            continue

        print(f'Challenging {bot.name}')
        bot.challenge(tc_seconds)
        return


if __name__ == '__main__':
    main()