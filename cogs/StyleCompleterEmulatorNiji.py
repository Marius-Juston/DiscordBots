import http.client
import json
import os
import re
from collections import OrderedDict

import discord
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
from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# SHEET = 'NijiJourney V1'
SHEET = 'Temp'
options = {
    # "env": {
    #     'prompt': 'environment design by ',
    #     'ar': '16:9',
    #     'output_col': 'E',
    #     'ver_col': 'E',
    #     'split': True
    # },
    # 'port': {
    #     'prompt': 'portrait of a person by ',
    #     'ar': '2:3',
    #     'output_col': 'D',
    #     'ver_col': 'G',
    #     'split': True
    # },

    'port': {
        'prompt': 'portrait of a person by ',
        'ar': '2:3',
        'output_col': 'D',
        'ver_col': 'I',
        'split': True
    },
    'bunny': {
        'prompt': 'bikini bunny girl by ',
        'ar': '2:3',
        'output_col': 'E',
        'ver_col': 'K',
        'split': True
    },
    'spaceship': {
        'prompt': 'spaceship by ',
        'ar': '3:2',
        'output_col': 'F',
        'ver_col': 'M',
        'split': True
    },
    'horror': {
        'prompt': 'horror by ',
        'ar': '2:3',
        'output_col': 'G',
        'ver_col': 'O',
        'split': True
    },
    'demon angel': {
        'prompt': 'demon angel by ',
        'ar': '2:3',
        'output_col': 'H',
        'ver_col': 'Q',
        'split': True
    },

    # ,
    # 'art': {
    #     'prompt': 'artwork by ',
    #     'ar': '1:1',
    #     'output_col': 'C',
    #     'ver_col': 'C',
    #     'split': True
    # }
}

EXCLUDE = {'Yuri Ivanovich Pimenov', 'Steven Cox', 'Dick Bickenbach'}


class StyleCompleterEmulator(commands.Cog):
    # If modifying these scopes, delete the file credentials.json.
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    MAX_COUNTER = 13

    def __init__(self, client, output_channel_id, username, password):
        self.password = password
        self.username = username
        print(client)
        print(output_channel_id)
        self.output_channel_id = output_channel_id
        self.client: discord.ext.commands.bot.Bot = client
        self.view_history = True

        self.init = True
        self.messages = []
        self.global_counter = 0
        self.channel = None
        self.completed = dict()
        self.message_ids = set()
        self.DEFAULT_HISTORY = 50
        self.history_scale = self.DEFAULT_HISTORY

        self.commands = OrderedDict()

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

    def start_chrome(self):
        self.driver = webdriver.Chrome()
        self.driver.get(os.getenv("DISCORD_OUTPUT_CHANNEL_2"))
        self.action = ActionChains(self.driver)

        try:
            button = self.driver.find_element(By.XPATH, '//button[contains(string(), "Continue in browser")]')
            self.action.click(button)
            self.action.perform()
        except:
            pass

        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//input[@name="email"]'))  # This is a dummy element
        )

        username = self.driver.find_element(By.XPATH, '//input[@name="email"]')
        password = self.driver.find_element(By.XPATH, '//input[@name="password"]')

        username.send_keys(self.username)
        password.send_keys(self.password)

        button = self.driver.find_element(By.XPATH, '//button[contains(string(), "Log In")]')
        self.action.click(button).perform()

        self.driver.get(os.getenv("DISCORD_OUTPUT_CHANNEL_2"))

        WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="textbox"]'))  # This is a dummy element
        )

        self.text = self.driver.find_element(By.XPATH, '//div[@role="textbox"]')

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

            self.load_https()
            self.start_chrome()

    def load_spreadsheet(self):
        creds = None
        # The file credentials.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', StyleCompleterEmulator.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', StyleCompleterEmulator.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        return service.spreadsheets()

    def get_verification_index(self, ver_col: str):
        return ord(ver_col.upper()) - ord('A')

    def collect_variations(self, msg, split, attachment=0):
        image = msg["attachments"][attachment]
        image = image["url"]
        print(image)
        img = Image.open(requests.get(image, stream=True).raw)

        if split:
            width, height = img.size
            width = width // 2
            height = height // 2
            p1 = img.crop((0, 0, width * 2, height))
            p2 = img.crop((0, height, width * 2, height * 2))

            dst = Image.new('RGB', (p1.width + p2.width, p1.height))
            dst.paste(p1, (0, 0))
            dst.paste(p2, (width * 2, 0))

            return dst
        else:
            return img

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
        self.sheet = self.load_spreadsheet()

        self.refresh_users()

        authors = self.sheet.values().get(spreadsheetId=self.spreadsheet,
                                          range=f'WIP!A2:A').execute()
        authors = authors.get('values', [])

        for conf_key, conf_val in options.items():
            print(f"LOADING FOR {conf_key}")
            used = self.sheet.values().get(spreadsheetId=self.spreadsheet,
                                           range=f'WIP!{conf_val["ver_col"]}2:{conf_val["ver_col"]}').execute()
            used = used.get('values', [])[:len(authors)]

            if authors:
                for i, (name, val) in enumerate(zip(authors[::-1], used[::-1])):
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

                            if 'test' in conf_val:
                                if conf_val['test']:
                                    prompt += ' --test'

                            if prompt not in self.completed:
                                self.commands[prompt] = {'key': out_key,
                                                         'ar': conf_val["ar"],
                                                         'split': conf_val['split']}

        print(self.commands)

    @commands.command()
    async def start(self, ctx: Context, global_counter=None):
        print("Starting")
        self.load()

        self.view_history = True

        self.text = self.driver.find_element(By.XPATH, '//div[@role="textbox"]')

        if global_counter is not None:
            self.global_counter = int(global_counter)
        self.channel = ctx.channel
        await self.reload_commands()
        print(self.commands)

        if not self.save_and_upload.is_running():
            self.save_and_upload.start()
        if not self.go_through_artists.is_running():
            self.go_through_artists.start()

        if not self.check_new.is_running():
            self.check_new.start()

    @commands.command()
    async def set_count(self, ctx, global_num=0):
        self.global_counter = global_num

    @commands.command()
    async def stop(self, ctx: Context):
        if self.go_through_artists.is_running():
            self.go_through_artists.stop()

        if self.save_and_upload.is_running():
            self.save_and_upload.stop()

        if self.check_new.is_running():
            self.check_new.stop()

    @commands.command()
    async def save(self, ctx: Context):
        if not self.save_and_upload.is_running():
            self.save_and_upload.start()

        self.view_history = True
        if not self.check_new.is_running():
            self.check_new.start()

    def load_https(self):
        self.conn = http.client.HTTPSConnection("discord.com")
        self.payload = ''
        self.headers = os.getenv("AUTHENTICATION")

    def return_messages(self, messages=1):
        self.conn.request("GET", f"/api/v9/channels/{os.getenv('DISCORD_OUTPUT_CHANNEL_ID_2')}/messages?limit={messages}", self.payload,
                          self.headers)
        res = self.conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))

    @commands.command()
    async def history(self, ctx: Context, history=None):
        self.view_history = True
        if history is not None:
            self.history_scale = min(100, int(history))

    @tasks.loop(seconds=5)
    async def check_new(self):
        total_messages = 5

        if self.view_history:
            total_messages = self.history_scale
            self.view_history = False
            self.history_scale = self.DEFAULT_HISTORY

        for msg in self.return_messages(total_messages):
            print(msg)
            if len(msg['attachments']) == 1 and msg['id'] not in self.message_ids and "%" not in msg['content']:
                self.messages.append(msg)
                print(msg)
                self.message_ids.add(msg['id'])

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        content = message.content

        if message.author.name == 'Midjourney Bot' or message.author.name == "niji・journey Bot":
            valid = not ("Waiting" in content or "%" in content) and any(
                c['prompt'] in content for c in options.values())

            print("Message from MJ", content)

            if valid:
                print("Valid")
                if len(message.attachments) > 0:
                    print("Adding to messages")
                    self.messages.append(message)

    def __del__(self):
        self.driver.close()

    @tasks.loop(seconds=1)
    async def save_and_upload(self):
        if self.initialized() and len(self.messages) == 0:
            return

        message: Message = self.messages.pop(0)

        name: str = message["content"]
        name = re.findall(r'\*\*.+\*\*', name)[0]
        name = name[2:-2].strip()

        completed = name in self.completed
        unknown = name in self.commands
        used = completed or unknown

        # if not used:
        #     print("REFRESHED COMMANDS")
        # await self.reload_commands()

        if used:
            if unknown:
                data = self.commands[name]
                self.completed[name] = data
                del self.commands[name]
            else:
                data = self.completed[name]

            out = self.collect_variations(message, data['split'])
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
                if not unknown:
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
            if self.global_counter >= StyleCompleterEmulator.MAX_COUNTER:
                return

            (prompt, data) = self.commands.popitem(last=True)

            self.type_to_console(f'/imagine prompt:{prompt}')

            self.global_counter += 1
            print(self.global_counter)
            self.completed[prompt] = data

    def type_to_console(self, text: str):
        self.text.send_keys(text)
        self.text.send_keys(Keys.ENTER)
        self.text.send_keys(Keys.ENTER)


def setup(client):
    load_dotenv()

    OUTPUT_CHANNEL = os.getenv('OUTPUT_CHANNEL')
    PASSWORD = os.getenv("DISCORD_PASSWORD")
    USERNAME = os.getenv("DISCORD_USERNAME")

    client.add_cog(StyleCompleterEmulator(client, OUTPUT_CHANNEL, USERNAME, PASSWORD))
