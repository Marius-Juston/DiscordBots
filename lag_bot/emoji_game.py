import json
import os
import random
import time
from pprint import pprint

import discord
import openai
from discord import Message
from dotenv import load_dotenv
import re

regex = r"^((?:R|SS|SH|SM|H|M|B))(?::(\d+(?:\.\d+)?))?(?:=|:)(?:(\d+)(?:,(A|N|F|L))?|(.+)):\s*(.+)"
load_dotenv('.env_emoji')

OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

openai.api_key = OPEN_AI_KEY

LOAD_FILE = 'character.json'
FORMATTED_LOAD_FILE = 'formatted_character.json'

system = {
    "role": "system",
    "content": "You are a very good game master, creating a game where Emojis battle each other.\n\nYou are tasked to create the character sheet for each Emoji that the user inputs. As such, you must respond with the following rules.\n\nYou must set the base HP of the Emoji as \"HP={number here}\"\n\nYou must respond with a single value or a combination of the following. All the numbers must be positive.\nFor ranged attacks, \"R={input number here},{method}\".  The number means how much the range of attack will be. The method must be one of the following: \"A,\" which means all the people will get that damage; \"F,\" which means only the first person will be damaged. \"L\" means the last person will be damaged.\nFor melee attacks, \"M={input number here}\". It is the amount the person will attack the person ahead of them.\nFor healing, \"H={heal amount}{method}\". The number is the amount that will be added back to the health. The method is the following: \"F\" means the first person will heal that amount, and \"N\" means the people next to this will heal that amount.\nFor blocking, \"B={max blocking amount}\". The number will be the max blocking amount. When played, a random value will be chosen within \"[0, max blocking amount]\" inclusively.\n\nSome emojis will have special abilities:\n\"SS={emoji}\" will summon this emoji once it dies,\n\"SH={heal amount}\" will heal + increase max heal of the emoji if it kills another emoji\n\"SM={heal amount}\" will increase all damage health it kills another emoji\n\nThe emoji can be multiple of each attack mode; however, a probability must be associated with each of them. Each attack mode must be followed by a one-sentence explanation of how the emoji would perform that action. This must reflect the specific emoji.\n\nExample:\n\"User: 🤮\"\n\"\nHP=3\nR:0.5=1,A: Pukes on everyone!\nM:0.5=2: Stumbles and hits them\n\"\nor \n\"User: 🤓\"\n\"\nHP=5\nR:0.7=1,A: Everyone gets bored!\nR:0.3=5,F: This nerd goes to the gym!\n\"\nor\n\"User: 💪🏻\"\n\"\nHP=2\nM=10: Folds you in two.\nSM=3: My man goes to the gym!\n\"\nor\n\"User: 🤰🏻\"\n\"\nHP=10\nB=5: Motherly instinct to protect baby\nSS=👶🏻\n\"\nor\n\"User: 👶🏻\"\n\"\nHP=1\nM=4: Crying attack!\nSH=3: My boy is growing up!\n\"\n\nIn your response, do not include the quotation marks. The range for each of the numbers should be between 1-10."
}

USE_HISTORY = False


# define a retry decorator
def retry_with_exponential_backoff(
        func,
        initial_delay: float = 1,
        exponential_base: float = 2,
        jitter: bool = True,
        max_retries: int = 10,
        errors: tuple = (openai.error.RateLimitError,),
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)

            # Retry on specific errors
            except errors as e:
                # Increment retries
                num_retries += 1

                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )

                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())

                # Sleep for the delay
                time.sleep(delay)

            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e

    return wrapper


@retry_with_exponential_backoff
def completions_with_backoff(**kwargs):
    return openai.ChatCompletion.create(**kwargs)


def get_emoji_data(emoji: str, history: list):
    try:
        user_prompt = {
            'role': 'user',
            'content': emoji
        }

        history.append(user_prompt)

        gpt_input = history

        if not USE_HISTORY:
            gpt_input = [
                system, user_prompt
            ]

        response = completions_with_backoff(
            model="gpt-4",
            messages=gpt_input,
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        response = response.choices[0].message.content
        history.append({
            'role': 'assistant',
            'content': response
        })

        return response
    except openai.error.OpenAIError as e:
        print(e)
        print(e.http_status)
        print(e.error)


def generate_emojis(extra_emojis):
    start = 0x1f600
    end = 0x1f644

    n = end - start

    print('Using ', n, ' emojis')

    emojis = []

    for i in range(n):
        print(hex(start), start, chr(start))
        emojis.append(chr(start))

        start += 1

    emojis.extend(extra_emojis)

    print(emojis)

    character_data = {'characters': {}, 'history': []}

    chatpgpt_history = [system]

    if os.path.exists(LOAD_FILE):
        with open(LOAD_FILE, 'r') as f:
            character_data = json.load(f)

        for c in character_data['characters']:
            if c in emojis:
                emojis.remove(c)

        chatpgpt_history = character_data['history']

    if os.path.exists(FORMATTED_LOAD_FILE):
        with open(FORMATTED_LOAD_FILE, 'r') as f:
            character_data_formatted = json.load(f)

        for c, v in character_data_formatted.items():
            print(c)
            for a in v['specials']:
                if a is None:
                    continue

                q = a['type']

                print(q, )
                if q == 'SS':
                    e = a['summon']

                    print("Summon", e)
                    if e not in character_data_formatted:
                        emojis.append(e)

    print(emojis)

    random.shuffle(emojis)

    new = False

    for i, emoji in enumerate(emojis):
        emoji_data = get_emoji_data(emoji, chatpgpt_history)

        if emoji_data is not None:

            character_data['characters'][emoji] = emoji_data
            character_data['history'] = chatpgpt_history

            print(emoji, (i + 1) / len(emojis) * 100)
            print(emoji_data)
            new = True

            with open(LOAD_FILE, 'w') as f:
                json.dump(character_data, f)

            # time.sleep(10)
        else:
            print("Failure with emoji", emoji)

    return new


def extract_attack(attack):
    matches = re.finditer(regex, attack)

    for matchNum, match in enumerate(matches, start=1):

        # print("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum=matchNum, start=match.start(),
        #                                                                     end=match.end(), match=match.group()))

        data = {}

        groups = match.groups()

        for i, group in enumerate(groups):
            if i == 0:
                data['type'] = group
            if i == 1:
                if group is None:
                    data['p'] = 1.0
                else:
                    data['p'] = float(group)
            if i == 2:
                if group is not None:
                    data['amount'] = int(group)
            if i == 3:
                if group is not None:
                    data['mode'] = group
            if i == 4:
                if group is not None:
                    data['summon'] = group
            if i == 5:
                if group is not None:
                    data['text'] = group.strip()

        return data


def reformat_emojis():
    with open(LOAD_FILE, 'r') as f:
        data = json.load(f)
        characters_raw = data['characters']

    formatted_characters = dict()

    for c, val in characters_raw.items():

        attacks = val.strip().split('\n')

        moves = []

        formatted_characters[c] = dict()

        formatted_characters[c]['HP'] = int(attacks[0].split('=')[-1])

        special_moves = []

        for attack in attacks[1:]:
            output = extract_attack(attack)

            if output['type'].startswith("S"):
                special_moves.append(output)
            else:
                moves.append(output)

        formatted_characters[c]['attacks'] = moves
        formatted_characters[c]['specials'] = special_moves

    pprint(formatted_characters)

    with open(FORMATTED_LOAD_FILE, 'w') as f:
        json.dump(formatted_characters, f)


class EmojiGame(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message: Message):
        if message.author.bot:
            return


class User:
    def __init__(self, hp=10):
        self.base_deck = []
        self.rep = []
        self.hp = hp

        self.deck = []
        self.hps = []
        self.initial_ranges = []
        self.blocks = []

    def add(self, emoji):
        self.base_deck.append(emoji)

    def swap(self, index1, index2):
        self.deck[index1], self.deck[index2] = self.deck[index2], self.deck[index1]

    def reset(self):
        self.deck = self.base_deck.copy()
        self.hps = [[i, Game.EMOJIS[e]['HP'], 0] for i, e in enumerate(
            self.deck)]  # TODO NEED TO MAKE THIS A COPY OF EMOJI REPRESENTATION ENHANCE DICTIONARY WITH EMOJI + EXTRA DAMMAGE QUANTIFIER
        self.initial_ranges = self.ranges_moves()
        self.reset_blocks()

    def reset_blocks(self):
        self.blocks = [0 for _ in range(len(self.deck))]

    def step(self):
        if len(self.initial_ranges) > 0:
            return self.initial_ranges.pop(0), True
        else:
            first = max(self.hps, key=lambda x: x[0])[0]

            emoji = self.deck[first]

            emoji_ = Game.EMOJIS[emoji]

            melee = []
            prob = []

            ranges = []
            ranges_prob = []

            for a in emoji_['attacks']:
                if a['type'] == 'R':
                    ranges.append(a)
                    ranges_prob.append(a['p'])
                else:
                    melee.append(a)
                    prob.append(a['p'])

            if len(melee) > 0:
                move = random.choices(melee, prob)
            else:
                move = random.choices(ranges, ranges_prob)

            move = move[0]

            damage = True

            if move['type'] == 'B':
                self.blocks[first] += move['amount']
                damage = False

            elif move['type'] == 'H':
                amount = move['amount']

                if move['mode'] == 'F':
                    self.hps[-1][1] += amount

                    self.hps[-1][1] = min(Game.EMOJIS[self.deck[self.hps[-1][0]]]['HP'] * 2,  self.hps[-1][1])
                elif move['mode'] == 'N':
                    for i in range(len(self.hps)):
                        if self.hps[i][0] == i:
                            prev = i - 1
                            ne = i + 1

                            if prev > 0:
                                self.hps[prev][1] += amount

                                self.hps[prev][1] = min(Game.EMOJIS[self.deck[self.hps[prev][0]]]['HP'] * 2, self.hps[prev][1])
                            if ne < len(self.hps):
                                self.hps[ne][1] += amount

                                self.hps[ne][1] = min(Game.EMOJIS[self.deck[self.hps[ne][0]]]['HP'] * 2, self.hps[ne][1])
                damage = False

            elif move['type'] == 'M':
                move = move.copy()
                move['amount'] += self.hps[first][2]

            return (first, emoji_, move), damage

    def ranges_moves(self):
        moves = []

        range_moves = 0

        for i, _, _ in self.hps:
            e = self.deck[i]
            emoji = Game.EMOJIS[e]

            probabilities = [m['p'] for m in emoji['attacks']]
            indexes = list(range(len(probabilities)))

            choice = random.choices(indexes, weights=probabilities)[0]
            move = emoji['attacks'][choice]

            if move['type'] == "R":
                moves.insert(range_moves, [i, e, move])
                range_moves += 1

        return moves

    def manage_hps(self):
        deaths = []
        summons = []

        i = len(self.hps) - 1

        while i >= 0:
            if self.hps[i][1] <= 0:
                hp = self.hps[i]

                deaths.append([hp[0], self.deck[hp[0]]])

                specials = Game.EMOJIS[self.deck[hp[0]]]['specials']

                self.deck.pop(i)
                self.hps.pop(i)

                summoned = -1

                shift = 0

                for s in specials:
                    if s['type'] == 'SS':
                        a = s['summon']

                        self.deck.insert(i + shift, a)
                        self.hps.insert(i + shift, [i + shift, Game.EMOJIS[a]['HP'], 0])

                        summons.append(a)

                        summoned += 1
                        shift += 1

                for index in range(len(self.hps)):
                    if self.hps[index][0] > i + shift:
                        self.hps[index][0] += summoned

            i -= 1
        return deaths, summons

    def hit(self, move):
        _, emoji, move = move

        amount = move['amount']

        if move['type'] == 'M':
            self.hps[-1][1] += min(self.blocks[-1] - amount, 0)

        elif move['type'] == 'R':
            mode = move['mode']

            if mode == 'L':
                self.hps[0][1] += min(self.blocks[0] - amount, 0)
            elif mode == 'F':
                self.hps[-1][1] += min(self.blocks[-1] - amount, 0)
            elif mode == 'A':
                for i in range(len(self.hps)):
                    self.hps[i][1] += min(self.blocks[i] - amount, 0)

        deaths, summons = self.manage_hps()

        return deaths, summons

    def special(self, move):
        index, _, _ = move
        emoji = self.deck[index]

        print("Checking specials for", emoji, index)

        for s in Game.EMOJIS[emoji]['specials']:
            if s['type'] == 'SH':
                print("Performing Max Healing")
                for i in range(len(self.hps)):
                    if self.hps[i][0] == index:
                        self.hps[i][1] += s['amount']
            if s['type'] == 'SM':
                print("Performing Max Attack")
                for i in range(len(self.hps)):
                    if self.hps[i][0] == index:
                        self.hps[i][2] += s['amount']


class Game:
    EMOJIS = dict()

    def __init__(self):
        self.user1 = User()
        self.user2 = User()

        self.user1.add('😵')
        self.user1.add('🥶')
        self.user1.add('💀')

        self.user2.add('🤑')
        self.user2.add('🤐')
        self.user2.add('🥵')
        self.user2.add('😇')

        self.count = 0

        self.users = [self.user1, self.user2]

        self.user_flip = random.randint(0, len(self.users) - 1)

    def reset_user_moves(self):
        for u in self.users:
            u.reset()

    def prepare_game(self):
        self.reset_user_moves()

    def reset_blocks(self, active_user):
        for u in self.users:
            if u == active_user:
                u.reset_blocks()

    def step(self):
        print("USER's", self.user_flip, "TURN")

        current = self.users[self.user_flip]
        target = self.users[1 - self.user_flip]

        self.reset_blocks(current)

        output = current.step()
        move, damage = output

        if damage:
            death, summons = target.hit(move)

            if len(death) > 0:
                print("DEATHS", death)
                current.special(move)
            if len(summons) > 0:
                print("SUMMONS", summons)

        self.user_flip = 1 - self.user_flip
        self.count += 1

        print(target.blocks)

        return move

    def winner(self):
        if len(self.user1.hps) == 0:
            return 1
        elif len(self.user2.hps) == 0:
            return 0
        else:
            return -1

    def finished(self):
        return self.winner() != -1 or (self.count // 2) > 30


if __name__ == '__main__':
    random.seed(42)
    generate = False

    if generate:
        extra_emojis = ['🥶', '💀', '🤑', '🤐', '🥵']
        new = True

        while new:
            new = generate_emojis(extra_emojis)

            reformat_emojis()

            if new:
                print("NEW EMOJI GOING AGAIN")

    with open(FORMATTED_LOAD_FILE, 'r') as f:
        Game.EMOJIS = json.load(f)

    print("STARTING DISCORD")

    intents = discord.Intents.default()
    intents.message_content = True

    client = EmojiGame(intents=intents)

    game = Game()

    for i in range(2):
        game.prepare_game()

        while not game.finished():
            print(game.user1.hps, game.user2.hps)
            print(game.user1.deck, game.user2.deck)
            index, _, move = game.step()
            print(index, move)
            print()
            print()

        print(game.user1.hps, game.user2.hps)

    # client.run(BOT_TOKEN)
