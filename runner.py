import os.path
import platform
import random
import re

import discord
import pyautogui
import pyperclip
import requests
from PIL import Image
from discord import TextChannel, Message
from discord.ext import commands, tasks
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file credentials.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

setup = "PORTd"

if setup == "ENV":

    PROMPT = 'environment design by '

    ar = '16:9'
    OUTPUT_COLUMN = 'E'
    VERIFICATION_CHECK_COLUMN = 'G'
elif setup == "PORT":
    PROMPT = 'portrait of a person by '

    ar = '2:3'
    OUTPUT_COLUMN = 'D'
    VERIFICATION_CHECK_COLUMN = 'I'
else:
    PROMPT = 'artwork by '
    ar = '1:1'
    OUTPUT_COLUMN = 'C'
    VERIFICATION_CHECK_COLUMN = 'C'

VERIFICATION_CHECK_INDEX = ord(VERIFICATION_CHECK_COLUMN) - ord('A')

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
SAMPLE_SPREADSHEET_ID = os.getenv('SAMPLE_SPREADSHEET_ID')

bot = commands.Bot(command_prefix='!')
channel: TextChannel = None
max_counter = 13
global_counter = 0
current_list = dict()
EXCLUDE = {'Yuri Ivanovich Pimenov', 'by Steven Cox'}

if ar == '1:1':
    width = 256
    height = 256
elif ar == '16:9':
    width = 896 // 2
    height = 512 // 2
elif ar == '9:16':
    width = 512 // 2
    height = 896 // 2
elif ar == '2:3':
    width = 512 // 2
    height = 768 // 2
else:
    raise ValueError(f"--ar {ar} is not defined")

"""Shows basic usage of the Sheets API.
Prints values from a sample spreadsheet.
"""
creds = None
# The file credentials.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())


def type_to_console(text: str):
    pyperclip.copy(text)
    if platform.system() == "Darwin":
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.hotkey("ctrl", "v")


def get_artworks_to_test():
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        names = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                   range='Artists V3!A2:A').execute()
        values = names.get('values', [])

        artists = dict()

        if values:
            for i in range(len(values) - 1, -1, -1):
                row = values[i]
                print(row)
                artists[row[0].strip()] = f'Artists V3!{OUTPUT_COLUMN}{2 + i}'

        names = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                   range=f'WIP!A2:{VERIFICATION_CHECK_COLUMN}').execute()
        values = names.get('values', [])

        if values:
            for row in values:
                key = row[0].strip()
                if key != '' and key in artists.keys():
                    if row[VERIFICATION_CHECK_INDEX] == "Yes":
                        del artists[key]

        print('Name, Major:')

        return artists


    except HttpError as err:
        print(err)


def set_val(cell, val):
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        names = sheet.values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                      range=cell,
                                      body={
                                          'range': cell,
                                          'values': [[val]]
                                      }, valueInputOption='USER_ENTERED').execute()
    except HttpError as err:
        print(err)


artist_list = get_artworks_to_test()
print(artist_list)


@bot.event
async def on_command_error(ctx, error):
    print(error)
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')


@tasks.loop(seconds=1)
async def go_through_artists():
    # print("Going through artists")
    global artist_list, global_counter, max_counter, current_list

    while len(artist_list) > 0:
        # print(global_counter)
        if global_counter >= max_counter:
            return

        art = artist_list.popitem()
        print(art)

        while art[0] in EXCLUDE:
            stop = len(artist_list) == 0

            if stop:
                return

            art = artist_list.popitem()
            print(art)

        current_list[art[0]] = art[1]

        pyautogui.write(f'/imagine ', interval=.1)
        type_to_console(f'{PROMPT}{art[0]} --ar {ar}')
        pyautogui.press('enter')

        print(current_list)
        global_counter += 1

        # break


messages = []


@tasks.loop(seconds=1)
async def save_and_upload():
    global messages, global_counter

    if len(messages) == 0:
        return

    message = messages.pop(0)

    out = collect_variations(message)
    rand = random.randint(0, 10000)
    temp_name = f'temp{rand}.png'

    out.save(temp_name)
    out = await channel.send(file=discord.File(temp_name))
    os.remove(temp_name)
    out = out.attachments[0].url

    name: str = message.content
    name = re.findall(r'\*\*.+\*\*', name)[0]
    name = name[2:-2].strip()
    name = name[len(PROMPT):-len(f' --ar {ar}')]

    print("SAVING", f"'{name}'")
    if name in artist_list:
        a = artist_list.pop(name)
        current_list[name] = a
        # global_counter -= 1
    if name in current_list:
        cell = current_list[name]
        command = f'=IMAGE("{out}")'

        print("SAVING TO SPreadsheet", cell, command)
        set_val(cell, command)
        global_counter -= 1


@bot.command(name='start')
async def start(ctx, num=0):
    global global_counter
    global_counter = num
    print("SETTING GLOBAL COUNTER", global_counter)
    if not save_and_upload.is_running():
        save_and_upload.start()
    if not go_through_artists.is_running():
        go_through_artists.start()


@bot.command(name='reload')
async def reload(ctx):
    global artist_list

    artist_list = get_artworks_to_test()

    if go_through_artists.is_running():
        go_through_artists.stop()
    go_through_artists.start()


@bot.command(name='listen')
async def listen(ctx):
    if not save_and_upload.is_running():
        save_and_upload.start()


@bot.command(name='stop')
async def stop(ctx):
    save_and_upload.stop()
    go_through_artists.stop()


@bot.event
async def on_ready():
    global channel
    channel = discord.utils.get(bot.get_all_channels(), guild__name=GUILD, name='mj-bot')

    print(channel, type(channel))


def collect_variations(msg, attachment=0):
    image = msg.attachments[attachment]
    image = image.url
    print(image)
    img = Image.open(requests.get(image, stream=True).raw)

    p1 = img.crop((0, 0, width * 2, height))
    p2 = img.crop((0, height, width * 2, height * 2))

    dst = Image.new('RGB', (p1.width + p2.width, p1.height))
    dst.paste(p1, (0, 0))
    dst.paste(p2, (width * 2, 0))

    return dst


@bot.event
async def on_message(message: Message):
    global channel, global_counter, artist_list, current_list

    print(global_counter)

    if message.author == bot.user:
        return

    content = message.content

    print("LENGTHS: ", len(message.attachments))

    print(message)
    if message.channel == channel:
        if content == 'cmd':
            async for msg in message.channel.history(limit=1000):  # As an example, I've set the limit to 10000
                if msg.author != bot.user:
                    if msg.author.name == 'Midjourney Bot':
                        name: str = msg.content
                        valid = not ("Waiting" in name or "%" in name)

                        print(name)
                        name = re.findall(r'\*\*.+\*\*', name)

                        if len(name) == 1:
                            name = name[0]
                            name = name[2:-2].strip()
                            valid = valid and name.startswith(PROMPT)
                            name = name[len(PROMPT):-len(f' --ar {ar}')]

                            if valid and name in artist_list:
                                if len(msg.attachments) > 0:
                                    out = collect_variations(msg)
                                    rand = random.randint(0, 10000)
                                    temp_name = f'temp{rand}.png'

                                    out.save(temp_name)
                                    out = await channel.send(file=discord.File(temp_name))
                                    os.remove(temp_name)
                                    out = out.attachments[0].url
                                    print(msg.content)

                                    if name in artist_list:
                                        a = artist_list.pop(name)
                                        current_list[name] = a
                                        global_counter += 1
                                    if name in current_list:
                                        cell = current_list[name]
                                        command = f'=IMAGE("{out}")'

                                        print("SAVING TO SPreadsheet", cell, command)
                                        set_val(cell, command)
                                        global_counter -= 1

                                    print(name)

        if message.author.name == 'Midjourney Bot':
            valid = not ("Waiting" in content or "%" in content)
            print("Message from MJ", content)

            if valid:
                print("Valid")
                if len(message.attachments) > 0:
                    print("Adding to messages")
                    messages.append(message)

    await bot.process_commands(message)


bot.run(TOKEN)
