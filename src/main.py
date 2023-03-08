# This example requires the 'message_content' intent.
import openai
import os
import discord

openai.api_key = os.getenv('openaikey')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

history = []

def compose(message):
    if len(history) > 30:
        goodbye = history.pop(0)
    
    messages = [
        {"role": "system", "content": "You are the Computer managing Alpha Complex from the roleplaying game Paranoia."}    
    ]

    for past in history:
        if past.startswith('Computer,'):
            current = {"role": "user", "content": past}
        else:
            current = {"role": "assistant", "content": past}
        messages.append(current)
    messages.append({"role": "user", "content": message})

    answer = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    history.append(answer['choices'][0]['message']['content'])
    return answer

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello troubleshooter! I am your friendly Computer')

    if message.content.startswith('Computer, can I see'):
        response = openai.Image.create(prompt=message.content[19:], n=1, size="256x256")
        image_url = response['data'][0]['url']
        await message.channel.send(image_url)

    elif message.content.startswith('Computer,'):
        answer = compose(message.content)
        print(answer)
        history.append(message.content)
        text = answer['choices'][0]['message']['content']
        await message.channel.send(text)

client.run(os.getenv('bot_token'))