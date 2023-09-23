import codecs
import os

import discord
import requests
from bs4 import BeautifulSoup
from discord import Message
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def download(url, col, row_index):
    response = requests.get(url, stream=True)
    name = None
    if response.ok:
        name = f'imgs/{col}{row_index}.jpg'
        with open(name, 'wb') as handle:
            for block in response.iter_content(1024):
                if not block:
                    break

                handle.write(block)

    return name


class HTMLParser(commands.Cog):
    # If modifying these scopes, delete the file credentials.json.
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __int__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        self.load()

    def load(self):
        load_dotenv('../..')
        GUILD = os.getenv('DISCORD_GUILD')
        SAMPLE_SPREADSHEET_ID = os.getenv('SAMPLE_SPREADSHEET_ID')

        self.guild_id = GUILD
        self.spreadsheet = SAMPLE_SPREADSHEET_ID

        self.sheet = self.load_spreadsheet()
        self.init = True
        self.channel = None
        self.completed = dict()

    def load_spreadsheet(self):
        print(os.getcwd())
        creds = None
        # The file credentials.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', HTMLParser.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', HTMLParser.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        return service.spreadsheets()

    @commands.command()
    async def html(self, ctx: Context):
        f = codecs.open("Artists V2 V1.html", 'r', 'utf-8')
        s = f.read()

        f = BeautifulSoup(s, features='lxml')

        f.find('table', attrs={'class': 'waffle'})
        table_body = f.find('tbody')

        rows = table_body.find_all('tr')
        channel = ctx.channel

        i = 0

        for row in rows:
            if i <= 1:
                i += 1
                continue

            row_index = int(row.find_all("th")[0].text.strip())
            cols = row.find_all('td')

            url = cols[3].div.img['src']
            url = url.replace("=w400-h99", '')
            name = download(url, 'C', row_index)
            if name is not None:
                out: Message = await channel.send(file=discord.File(name))
                self.set_val(f"Artists V2/V1!C{row_index}", f'=IMAGE("{out.attachments[0].url}")')

            if cols[4].div is not None:
                url = cols[4].div.img['src']
                url = url.replace("=w400-h99", '')
                name = download(url, 'D', row_index)

                if name is not None:
                    out: Message = await channel.send(file=discord.File(name))
                    self.set_val(f"Artists V2/V1!D{row_index}", f'=IMAGE("{out.attachments[0].url}")')

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


def setup(client):
    client.add_cog(HTMLParser(client))
