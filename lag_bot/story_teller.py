import discord
import os
import openai
import openai.error
from dotenv import load_dotenv

# https://stackoverflow.com/questions/55462226/how-can-i-keep-a-python-script-on-a-remote-server-running-after-closing-out-of-s

load_dotenv('.env_story_teller')


OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')
BOT_TOKEN = os.getenv('BOT_TOKEN')

openai.api_key = OPEN_AI_KEY


system = {"role": "system", "content": "You are an expert illustrator for storytelling. You know precisely when something important has happened and are able to create an image prompt from the conversation to illustrate what was said. If nothing interesting happened, then return \"STOP\". Remember you must ONLY respond with \"STOP\" or an image prompt description of the conversation, nothing else!\n\nWhen responding with the image prompt, do not have any extra text other than the image description itself. The image description must be very detailed."}

MAX_MESSAGE_HISTORY = 20

class MyClient(discord.Client):

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        self.history = dict()

    def generate_chat_gpt_response(self, message_history):
        try:
            messages = []

            messages.append(system)
            messages.extend(message_history[-MAX_MESSAGE_HISTORY:])

            print("Generating ChatGPT response from", messages)
            completion = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=
                                                    messages,
                                                    temperature=1,
                                                    max_tokens=100,
                                                    top_p=1,
                                                    frequency_penalty=0,
                                                    presence_penalty=0,
                                                    stop=["STOP"]
                                                    )
                                                    
            
            chat_response = completion.choices[0].message.content
            print(chat_response)

            if chat_response is None or chat_response == '' or chat_response == "STOP":
                print("Do not respond with anything")
                chat_response = None

        except openai.error.OpenAIError as e:
            print("Rate Limit Reached")
            print(e.http_status)
            print(e.error)
            chat_response = None

        return chat_response
    
    def generate_dalle_output(self, image_prompt):
        try:
            print("Generating DallE image from prompt", image_prompt)
            response = openai.Image.create(
                                            prompt=image_prompt,
                                            n=1,
                                            size="1024x1024"
                                            )
            image_url = response['data'][0]['url']
            print(image_url)
        except openai.error.OpenAIError as e:
            print("Rate Limit Reached")
            print(e.http_status)
            print(e.error)
            image_url = None

        return image_url
    async def on_message(self, message):
        if message.author.bot:
            return

        channel = message.channel

        channel_messages = []

        async for history_message in channel.history(limit=MAX_MESSAGE_HISTORY):
            channel_messages.insert(0, {'role':'user', "content": history_message.content})

        image_prompt = self.generate_chat_gpt_response(channel_messages)

        if image_prompt is not None:
            image_url = self.generate_dalle_output(image_prompt)

            if image_prompt is not None:
                await message.channel.send(image_prompt)
                await message.channel.send(image_url)


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True

    client = MyClient(intents=intents)
    client.run(BOT_TOKEN)
