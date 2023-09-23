import discord
import pyautogui
import pyperclip
import platform
import locale
import time
import random
import threading
import os
from dotenv import load_dotenv

load_dotenv('.env_mathing')

CHANNEL_ID = os.getenv('CHANNEL_ID')
MARIUS_ID = os.getenv('MARIUS_ID')
BUBBLES_ID = os.getenv('BUBBLES_ID')
BOT_TOKEN = os.getenv('BOT_TOKEN')

def type_to_console(text: str):
    pyperclip.copy(text)
    if platform.system() == "Darwin":
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.hotkey("ctrl", "v")

    pyautogui.press('enter')

class MyClient(discord.Client):

    def emergency(self):
        print("CALLING EMERGENCY FUNCTION")

        self.emergency_call += 1

        print("Calling function", self.emergency_call + 1, "th time. Non responsive")

        if self.play == 1:
            type_to_console(f">lower {self.stake_amount_leveling} 99")
        elif self.play == 5:
            type_to_console(f">rps {self.money * self.rps_percent} rock")
            time.sleep(1 + random.randint(2, 3))
            type_to_console("+:octogonal_sign:")


        self.timer_continous.cancel()
        self.timer_continous = threading.Timer(self.timer_time, self.emergency)
        self.timer_continous.start()

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        self.channel = self.get_channel(CHANNEL_ID)

        locale.setlocale(locale.LC_ALL, '')

        self.play = 0
        self.money = 0

        self.logging_file = None

        self.counter = 0

        self.play_crash_for_reals = False

        self.running_crash = False

        self.finished_messages = set()

        self.initial_money = 0


        self.stake_amount_leveling = 10000000
        self.timer_time = 120
        self.emergency_call = 0

        self.rps_percent = 10/100.

        self.timer_continous = threading.Timer(self.timer_time, self.emergency)

    async def on_resume(self):
        if self.play == 1:
            type_to_console(f">lower {self.money * 0.23} 93")

        elif self.play == 2:
            stake_amount= self.money * 1/100
            num_bets = max(1, int(self.money / stake_amount * 0.25))

            type_to_console(f">stake {stake_amount} {num_bets}")
        elif self.play == 3:
            stake_amount = 1
            self.play_crash_for_reals = False
            self.running_crash = True

            type_to_console(f">crash {stake_amount}")
        elif self.play == 4:
            
            self.timer_continous.cancel()

            stake_amount = self.stake_amount_leveling
            self.initial_money = self.money

            if self.money > stake_amount:
                type_to_console(f">lower {stake_amount} 99")
                self.timer_continous = threading.Timer(self.timer_time, self.emergency)
                self.timer_continous.start()
                
    

    async def on_message_edit(self, before, after):
        
        if self.play == 3 and after.channel.id == CHANNEL_ID and after.author.id == BUBBLES_ID:
            # print(after)

            if after.id in self.finished_messages:
                return 


            emeds = after.embeds[-1]
            output = emeds.fields

            multiplier = locale.atof(output[0].value[1:])

            # if not self.running_crash:
            #     if self.play_crash_for_reals:
            #         type_to_console(f">crash {self.money * 0.2}")
            #         self.play_crash_for_reals = False
            #         self.running_crash = True
            #     else:
            #         type_to_console(f">crash 0.01")
            #         self.play_crash_for_reals = False
            #         self.running_crash = True
            
            if self.running_crash and multiplier >= 1.2:
                type_to_console(f">stop")
                
                self.timer_continous.cancel()
                self.play_crash_for_reals = False
                self.running_crash = False

            # print(output)

            if output[-1].name == "Balance:" or output[-1].name == "Final Crash Point:":
                self.finished_messages.add(after.id)
                self.running_crash = False

                if multiplier <= 1.2:# or random.random() < 0.2:
                    self.play_crash_for_reals = True
                else:
                    self.play_crash_for_reals = False

                if output[-1].name == "Balance:":
                    money_amount = locale.atof(output[-1].value[1:])
                else:
                    money_amount = locale.atof(output[-2].value[1:])

                self.money = money_amount
                print("Current money", self.money)
                self.logging_file.write(str(self.money) + ',' + str(multiplier) +'\n')
                # print("Running flag", self.running_crash)

                if not self.running_crash:
                    if self.play_crash_for_reals:
                        type_to_console(f">crash {self.money * 0.2}")
                        self.play_crash_for_reals = False
                        self.running_crash = True
                    else:
                        type_to_console(f">crash 1")
                        self.play_crash_for_reals = False
                        self.running_crash = True


        if self.play == 5 and after.channel.id == CHANNEL_ID and after.author.id == BUBBLES_ID:

            if after.id in self.finished_messages:
                return 


            emeds = after.embeds[-1]
            output = emeds.fields

            # print(output)


            if output[-1].name == "Balance:":
                self.timer_continous.cancel()
                self.finished_messages.add(after.id)

                money_amount = locale.atof(output[-1].value[1:])

                self.money = money_amount
                print("Current money", self.money)

                self.logging_file.write(str(self.money) +'\n')

                time.sleep(random.randint(3, 5))
                type_to_console(f">rps {self.money * self.rps_percent} rock")
                time.sleep(1 + random.randint(2, 3))
                type_to_console("+:octagonal_sign:")

                self.timer_continous = threading.Timer(self.timer_time, self.emergency)
                self.timer_continous.start()

               

    async def on_message(self, message):
        if self.is_ready():

            if self.counter >= 50000:
                self.play = 0
                
                self.timer_continous.cancel()
                self.counter = 0

                type_to_console(">deposit all")
                if self.logging_file is not None:
                    self.logging_file.flush()
                    self.logging_file.close()
                    self.logging_file = None
            if self.counter % 100 == 0:
                if self.logging_file is not None:
                    self.logging_file.flush()


            if message.channel.id == CHANNEL_ID:
                if message.author.id not in [MARIUS_ID, BUBBLES_ID]:
                    self.play = False
                    return

                if message.author.id == MARIUS_ID:
                    if message.content.lower() == 'start stake':
                        self.play = 2
                        print("Starting")
                        type_to_console(">profile")
                        self.counter = 0

                        if self.logging_file is None:
                            self.logging_file = open("stake", 'w')
                    if message.content.lower() == 'start lower':
                        self.play = 1
                        self.counter = 0
                        print("Starting")
                        type_to_console(">profile")

                        self.logging_file = open("lower", 'w')
                    if message.content.lower() == 'start crash':
                        self.play = 3
                        self.counter = 0
                        print("Starting")
                        type_to_console(">profile")

                        self.logging_file = open("crash", 'w')
                    if message.content.lower() == 'start rps':
                        self.play = 5
                        self.counter = 0
                        print("Starting")
                        type_to_console(">profile")

                        self.logging_file = open("rps", 'w')

                    if message.content.lower().startswith('start leveling'):
                        self.play = 4
                        self.counter = 0
                        print("Starting")
                        type_to_console(">profile")

                        if not (len(message.content) == len('start leveling')):
                            self.stake_amount_leveling= int(message.content[len('start leveling'):].strip())
                            print("Starting leveling amount", self.stake_amount_leveling)

                        self.logging_file = open("leveling", 'w')

                    if message.content == 'end':
                        self.play = 0
                        self.counter = 0
                        
                        self.timer_continous.cancel()

                        type_to_console(">deposit all")

                        if self.logging_file is not None:
                            self.logging_file.flush()
                            self.logging_file.close()
                            self.logging_file = None

                if message.author.id == BUBBLES_ID:
                    if len(message.embeds) > 0:
                        emeds = message.embeds[-1]
                        output = emeds.fields

                        if len(output) == 0:
                            return

                        if output[0].name == "**On Hand**:":
                            money_amount = locale.atof(output[0].value[1:])
                            self.money = money_amount

                            print("Initial Money amount", money_amount)

                            if self.logging_file is not None:
                                self.logging_file.write(str(self.money) + '\n')

                            if self.play == 1:
                                type_to_console(f">lower {self.money * 0.23} 93")

                            elif self.play == 2:
                                stake_amount= self.money * 1/100
                                num_bets = max(1, int(self.money / stake_amount * 0.25))

                                type_to_console(f">stake {stake_amount} {num_bets}")
                            elif self.play == 3:
                                stake_amount = 1
                                self.play_crash_for_reals = False
                                self.running_crash = True

                                type_to_console(f">crash {stake_amount}")
                            elif self.play == 5:
                                type_to_console(f">rps {self.money * self.rps_percent} rock")
                                time.sleep(1 + random.randint(2, 3))
                                type_to_console("+:octagonal_sign:")

                                self.timer_continous = threading.Timer(self.timer_time, self.emergency)
                                self.timer_continous.start()
                            elif self.play == 4:
                                
                                self.timer_continous.cancel()
                                stake_amount = self.stake_amount_leveling
                                self.initial_money = self.money

                                if self.money > stake_amount:
                                    type_to_console(f">lower {stake_amount} 99")
                                    self.timer_continous = threading.Timer(self.timer_time, self.emergency)
                                    self.timer_continous.start()
                                    

                        if self.play == 1 and output[0].name == "Bubbles' Number":
                            money_amount = locale.atof(output[-1].value[1:])
                            self.money = money_amount

                            self.counter += 1

                            print(self.counter,"Current money", money_amount)
                            self.logging_file.write(str(self.money) + '\n')

                            type_to_console(f">lower {self.money  * 0.23} 93")

                        # print(output[0].name)
                        if self.play == 2 and output[0].name == "Total Earnings:":
                            money_amount = locale.atof(output[-1].value[1:])
                            self.money = money_amount

                            self.counter = 0

                            print("Current money", money_amount)
                            self.logging_file.write(str(self.money) + '\n')

                            stake_amount= self.money * 1/100
                            num_bets = max(1, int(self.money / stake_amount * 1))

                            type_to_console(f">stake {stake_amount} {num_bets}")

                        # if self.play == 5 and output[0].name == "You picked:":
                        #     money_amount = locale.atof(output[-1].value[1:])
                        #     self.money = money_amount

                        #     self.counter = 0

                        #     print("Current money", money_amount)
                        #     self.logging_file.write(str(self.money) + '\n')

                        #     type_to_console(f">rps {self.money * self.rps_percent} rock")
                        #     time.sleep(1 + random.randint(2, 3))
                        #     type_to_console("+:octagonal_sign:")

                        #     self.timer_continous = threading.Timer(self.timer_time, self.emergency)
                        #     self.timer_continous.start()

                        if self.play == 4 and output[0].name == "Bubbles' Number":
                            
                            self.timer_continous.cancel()
                            money_amount = locale.atof(output[-1].value[1:])
                            bubbles_number = int(output[0].value)

                            self.money = money_amount

                            self.counter += 1

                            if self.money >= self.stake_amount_leveling * 4.5:
                                self.stake_amount_leveling = self.stake_amount_leveling * 2

                            # while self.money <= self.stake_amount_leveling*2:
                                # self.stake_amount_leveling /= 2
                            
                            stake_amount = self.stake_amount_leveling

                            print(self.counter,"Current money", money_amount, "Bubbles Number", bubbles_number, "Betting Amount", stake_amount)
                            self.logging_file.write(str(self.money) + "," + str(bubbles_number) + "," + str(stake_amount) + '\n')

                            if self.money >= stake_amount:
                                sleep_time = 2 + random.uniform(0, 4)
                                print("Sleeping for", sleep_time)
                                time.sleep(sleep_time)
                                type_to_console(f">lower {stake_amount} 99")
                                self.timer_continous = threading.Timer(self.timer_time, self.emergency)
                                self.timer_continous.start()
                                
                        # current_balance = float(output[-1].value[1:])

                        # print(f'Message from {message.author.id} {type(message.author)}: {message.content}, {emeds}, {output}')

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True

    client = MyClient(intents=intents)
    client.run(BOT_TOKEN)
