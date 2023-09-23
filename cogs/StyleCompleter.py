import os
import platform
import random
import re
from collections import OrderedDict

import discord
import pyautogui
import pyperclip
import requests
from PIL import Image
from discord import Message
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

options = {
    "env": {
        'prompt': 'environment design by ',
        'ar': '16:9',
        'output_col': 'E',
        'ver_col': 'G'
    },
    'port': {
        'prompt': 'portrait of a person by ',
        'ar': '2:3',
        'output_col': 'D',
        'ver_col': 'I'
    }, 'art': {
        'prompt': 'artwork by ',
        'ar': '1:1',
        'output_col': 'C',
        'ver_col': 'C'
    }
}

EXCLUDE = {'Yuri Ivanovich Pimenov', 'by Steven Cox'}

SHEET = 'Artists V3'


class StyleCompleter(commands.Cog):
    # If modifying these scopes, delete the file credentials.json.
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    MAX_COUNTER = 13

    def __init__(self, client, output_channel_id):
        print(client)
        print(output_channel_id)
        self.output_channel_id = output_channel_id
        self.client: discord.ext.commands.bot.Bot = client

    async def get_output_channel(self):
        channel = await self.client.fetch_channel(self.output_channel_id)

        return channel

    @commands.Cog.listener()
    async def on_ready(self):
        print("READY TO START")
        self.init = False
        self.output_channel = await self.get_output_channel()
        print(self.output_channel, type(self.output_channel))
        self.load()

    def initialized(self):
        try:
            return self.init
        except AttributeError:
            self.init = False
            return False

    def load(self):
        if not self.initialized():
            load_dotenv('..')
            GUILD = os.getenv('DISCORD_GUILD')
            SAMPLE_SPREADSHEET_ID = os.getenv('SAMPLE_SPREADSHEET_ID')

            self.guild_id = GUILD
            self.spreadsheet = SAMPLE_SPREADSHEET_ID

            self.sheet = self.load_spreadsheet()
            self.init = True
            self.messages = []
            self.global_counter = 0
            self.channel = None
            self.completed = dict()

    def load_spreadsheet(self):
        creds = None
        # The file credentials.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', StyleCompleter.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', StyleCompleter.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        return service.spreadsheets()

    def get_verification_index(self, ver_col: str):
        return ord(ver_col.upper()) - ord('A')

    def get_width_height(self, ar):
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

        return width, height

    def collect_variations(self, msg, ar, attachment=0):
        image = msg.attachments[attachment]
        image = image.url
        print(image)
        img = Image.open(requests.get(image, stream=True).raw)

        width, height = self.get_width_height(ar)
        p1 = img.crop((0, 0, width * 2, height))
        p2 = img.crop((0, height, width * 2, height * 2))

        dst = Image.new('RGB', (p1.width + p2.width, p1.height))
        dst.paste(p1, (0, 0))
        dst.paste(p2, (width * 2, 0))

        return dst

    def refresh_users(self):
        names = self.sheet.values().get(spreadsheetId=self.spreadsheet,
                                        range=f'{SHEET}!A2:A').execute()
        values = names.get('values', [])

        artists = dict()

        if values:
            for i in range(len(values)):
                row = values[i]
                if len(row) > 0:
                    name = row[0].strip()
                    artists[name] = 2 + i

        self.max_index = len(values) + 2
        self.artists = artists

    async def reload_commands(self):
        self.refresh_users()

        self.commands = OrderedDict()

        authors = self.sheet.values().get(spreadsheetId=self.spreadsheet,
                                          range=f'WIP!A2:A').execute()
        authors = authors.get('values', [])

        for conf_key, conf_val in options.items():
            print(f"LOADING FOR {conf_key}")
            used = self.sheet.values().get(spreadsheetId=self.spreadsheet,
                                           range=f'WIP!{conf_val["ver_col"]}2:{conf_val["ver_col"]}').execute()
            used = used.get('values', [])[:len(authors)]

            if authors:
                for i, (name, val) in enumerate(zip(authors, used)):
                    name = name[0].strip()
                    val = val[0]

                    if name in EXCLUDE:
                        continue

                    if name != '' and name in self.artists:
                        # if val == "Yes":
                        #     del self.artists[key]
                        if val == 'NO':
                            out_key = f'{conf_val["output_col"]}{self.artists[name]}'
                            prompt = f'{conf_val["prompt"]}{name} --ar {conf_val["ar"]}'

                            if prompt not in self.completed:
                                self.commands[prompt] = {'key': out_key,
                                                         'ar': conf_val["ar"]}

        print(self.commands)

    @commands.command()
    async def start(self, ctx: Context, global_counter=None):
        print("Starting")
        self.load()

        if global_counter is not None:
            self.global_counter = int(global_counter)
        self.channel = ctx.channel
        await self.reload_commands()
        print(self.commands)

        if not self.save_and_upload.is_running():
            self.save_and_upload.start()
        if not self.go_through_artists.is_running():
            self.go_through_artists.start()

    @commands.command()
    async def set_count(self, ctx, global_num=0):
        self.global_counter = global_num

    @commands.command()
    async def stop(self, ctx: Context):
        if self.go_through_artists.is_running():
            self.go_through_artists.stop()

        if self.save_and_upload.is_running():
            self.save_and_upload.stop()

    @commands.command()
    async def save(self, ctx: Context):
        if not self.save_and_upload.is_running():
            self.save_and_upload.start()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        content = message.content

        if message.author.name == 'Midjourney Bot':
            valid = not ("Waiting" in content or "%" in content) and any(
                c['prompt'] in content for c in options.values())

            print("Message from MJ", content)

            if valid:
                print("Valid")
                if len(message.attachments) > 0:
                    print("Adding to messages")
                    self.messages.append(message)

    @tasks.loop(seconds=1)
    async def save_and_upload(self):
        if self.initialized() and len(self.messages) == 0:
            return

        message: Message = self.messages.pop(0)

        name: str = message.content
        name = re.findall(r'\*\*.+\*\*', name)[0]
        name = name[2:-2].strip()

        completed = name in self.completed
        unknown = name in self.commands
        used = completed or unknown

        if not used:
            print("REFRESHED COMMANDS")
            await self.reload_commands()

        if used:
            if unknown:
                data = self.commands[name]
                self.completed[name] = data
                del self.commands[name]
            else:
                data = self.completed[name]

            out = self.collect_variations(message, data['ar'])
            # rand = random.randint(0, 10000)
            temp_name = f"{name.replace(' ', '_').replace('--', '_').replace(':', '_')}.png"

            out.save(temp_name)

            out = await self.output_channel.send(file=discord.File(temp_name))
            os.remove(temp_name)
            out = out.attachments[0].url

            print("SAVING", f"'{name}'")

            cell = f"{SHEET}!{data['key']}"
            command = f'=IMAGE("{out}")'

            print("SAVING TO Spreadsheet", cell, command)
            success = self.set_val(cell, command)
            if success:
                self.global_counter -= 1
            else:
                self.messages.append(message)

    def set_val(self, cell, val):
        try:
            has_val = self.sheet.values().get(spreadsheetId=self.spreadsheet,
                                              range=cell).execute()
            has_val = has_val.get('values', [])

            if len(has_val) > 0:
                return True

            names = self.sheet.values().update(spreadsheetId=self.spreadsheet,
                                               range=cell,
                                               body={
                                                   'range': cell,
                                                   'values': [[val]]
                                               }, valueInputOption='USER_ENTERED').execute()
            return True
        except HttpError as err:
            print(err)
            return False

    @tasks.loop(seconds=1)
    async def go_through_artists(self):
        while len(self.commands) > 0:
            if self.global_counter >= StyleCompleter.MAX_COUNTER:
                return

            (prompt, data) = self.commands.popitem(last=True)

            pyautogui.write(f'/imagine ', interval=.1)
            self.type_to_console(prompt)
            pyautogui.press('enter')

            self.global_counter += 1
            print(self.global_counter)
            self.completed[prompt] = data

    def type_to_console(self, text: str):
        pyperclip.copy(text)
        if platform.system() == "Darwin":
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")


def setup(client):
    load_dotenv()

    OUTPUT_CHANNEL = os.getenv('OUTPUT_CHANNEL')

    client.add_cog(StyleCompleter(client, OUTPUT_CHANNEL))
