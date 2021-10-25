import os
import berserk
import random
import requests
import re
import datetime

LICHESS_BOT_TOKEN = os.environ.get("LICHESS_BOT_TOKEN")
session = berserk.TokenSession(LICHESS_BOT_TOKEN)
client = berserk.Client(session)

MY_NAME = "Weiawaga"
RATING_MAX = 300
TOTAL_GAMES_MIN = 250
TC_GAMES_MIN = 50
TIME_MIN = datetime.timedelta(minutes=10)

TIME_CONTROLS = [
    60,
    120,
    300,
    420,
    600,
    900,
    1800,
    2400,
]


class Bot:
    def __init__(self, info):
        self.name = info["username"]
        self.last_seen = info["seenAt"].replace(tzinfo=None)

        self._ratings = {}
        self._num_games = {}
        for tc_name in ("bullet", "blitz", "rapid", "classical"):
            self._ratings[tc_name] = info["perfs"][tc_name]["rating"]
            self._num_games[tc_name] = info["perfs"][tc_name]["games"]

    @property
    def total_games(self):
        return sum(self._num_games.values())

    def num_games(self, tc_name):
        return self._num_games[tc_name]

    def rating(self, tc_name):
        return self._ratings[tc_name]

    def challenge(self, tc_seconds, tc_increment=0):
        client.challenges.create(
            self.name,
            rated=True,
            clock_limit=tc_seconds,
            clock_increment=tc_increment,
            days=1,
            # for some reason it requires days to be equal to 1 even though we're not
            # trying to do correspondence?
            color=random.choice([berserk.enums.Color.WHITE, berserk.enums.Color.BLACK]),
            variant=berserk.enums.Variant.STANDARD,
            position="",
        )

    @classmethod
    def get_all(cls):
        # get a list of bots
        r = requests.get("https://lichess.org/player/bots")
        bot_names = re.findall(r"(?<=user=).*?(?=#friend)", r.text)

        # request the bot info from lichess
        bots_info = client.users.get_by_id(*bot_names)
        random.shuffle(bots_info)

        return [cls(bot_info) for bot_info in bots_info if not bot_info.get("disabled")]


def classify_tc(tc_seconds, tc_increment=0):
    duration = tc_seconds + 40 * tc_increment
    if duration < 179:
        return "bullet"

    if duration < 479:
        return "blitz"

    if duration < 1499:
        return "rapid"

    return "classical"


def main():
    # return if we're already playing a game that isn't correspondence
    if games := client.games.get_ongoing():
        if any(game["speed"] != "correspondence" for game in games):
            print("Playing a game. Will not challenge.")
            return

    # select a time control to play
    tc_seconds = random.choice(TIME_CONTROLS)
    tc_name = classify_tc(tc_seconds)

    bots = Bot.get_all()

    me = next(bot for bot in bots if bot.name == MY_NAME)
    my_rating = me.rating(tc_name)

    now = datetime.datetime.utcnow()
    for bot in bots:

        if bot == me:
            print("Don't challenge myself.")
            continue

        if now - bot.last_seen > TIME_MIN:
            print(f"Skipping {bot.name}: not seen in too long.")
            continue

        if abs(bot.rating(tc_name) - my_rating) > RATING_MAX:
            print(f"Skipping {bot.name}: rating difference too large.")
            continue

        if bot.num_games(tc_name) < TC_GAMES_MIN or bot.total_games < TOTAL_GAMES_MIN:
            print(f"Skipping {bot.name}: too few games.")
            continue

        print(
            f"Challenging {bot.name} to a {tc_name} game with time control of {tc_seconds} seconds."
        )
        bot.challenge(tc_seconds)
        return


if __name__ == "__main__":
    main()
