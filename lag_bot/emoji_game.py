import json
import os
import random
import time
from pprint import pprint

import openai
from dotenv import load_dotenv
import re

regex = r"^((?:R|SS|SH|SM|H|M|B))(?::(\d+(?:\.\d+)?))?(?:=|:)(?:(\d+)(?:,(A|N|F|L))?|(.+)):\s*(.+)"
load_dotenv('.env_emoji')

OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')

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


def generate_emojis():
    start = 0x1f600
    end = 0x1f644

    n = end - start

    print('Using ', n, ' emojis')

    emojis = []

    for i in range(n):
        print(hex(start), start, chr(start))
        emojis.append(chr(start))

        start += 1

    print(emojis)

    character_data = {'characters': {}, 'history': []}

    chatpgpt_history = [system]

    if os.path.exists(LOAD_FILE):
        with open(LOAD_FILE, 'r') as f:
            character_data = json.load(f)

        for c in character_data['characters']:
            emojis.remove(c)

        chatpgpt_history = character_data['history']

    random.shuffle(emojis)

    new = False

    for i, emoji in enumerate(emojis):
        emoji_data = get_emoji_data(emoji, chatpgpt_history)

        if emoji_data is not None:

            character_data['characters'][emoji] = emoji_data
            character_data['history'] = chatpgpt_history

            print(emoji, (i + 1) / len(emojis) * 100)
            print(emoji_data)
            with open(LOAD_FILE, 'w') as f:
                json.dump(character_data, f)

            # time.sleep(10)
        else:
            print("Failure with emoji", emoji)


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

        for attack in attacks[1:]:
            output = extract_attack(attack)
            moves.append(output)

        formatted_characters[c]['attacks'] = moves

    pprint(formatted_characters)

    with open(FORMATTED_LOAD_FILE, 'w') as f:
        json.dump(formatted_characters, f)


if __name__ == '__main__':
    generate_emojis()

    reformat_emojis()
