import os

from discord.ext import commands
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()

    TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD = os.getenv('DISCORD_GUILD')

    bot = commands.Bot(command_prefix='!')
    # bot.load_extension('cogs.StyleCompleter')
    # bot.load_extension('cogs.StyleCompleterEmulator')
    bot.load_extension('cogs.StyleCompleterEmulatorNiji')
    # bot.load_extension('cogs.StyleCompleterEmulatorAnime')
    # bot.load_extension('cogs.HTMLParser')

    bot.run(TOKEN)
