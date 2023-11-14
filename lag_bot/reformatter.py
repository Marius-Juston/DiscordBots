import json
import os

LOAD_FILE = 'character.json'
FORMATTED_LOAD_FILE = 'formatted_character.json'

import random
def reformat():
    if os.path.exists(FORMATTED_LOAD_FILE):
        with open(FORMATTED_LOAD_FILE, 'r') as f:
            character_data_formatted = json.load(f)

        for c, v in character_data_formatted.items():
            for i in range(len(v['attacks'])):
                if v['attacks'][i]['type'] == 'B' and v['attacks'][i]['p'] == 1.0:
                    v['attacks'][i]['p'] = random.choice([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

        with open(FORMATTED_LOAD_FILE, 'w') as f:
            json.dump(character_data_formatted, f)


if __name__ == '__main__':
    reformat()
