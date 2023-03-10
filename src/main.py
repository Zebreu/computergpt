# This example requires the 'message_content' intent.
import openai
import os
import discord

openai.api_key = os.getenv('openaikey')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

history = []

def create_character(message):
    messages = [
        {"role": "system", "content": "You are a citizen of Alpha Complex from the roleplaying game Paranoia. You only speak in secret."}    
    ]
    if False:
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



def generate_image(message):
    response = openai.Image.create(prompt=message, n=1, size="512x512")
    image_url = response['data'][0]['url']
    return image_url

def expand_prompt(message):
    messages = [
        {"role": "system", "content": "You are a helpful prompt writing assistant for Dall-e."}    
    ]
    style = "in the style of the classic science fiction illustrator Tim White"
    style = "in the style of Norman Rockwell"
    base_prompt = f"{message}"
    messages.append({"role": "user", "content": f"Can you edit a prompt into a detailed prompt for Dall-e so it creates an amazing illustration. Keep it under 50 words and use classic science fiction as an inspiration. The prompt is: {base_prompt} {style}."})
    expanded_prompt = ask_chatgpt(messages)
    if len(expanded_prompt) > 400:
        print('Too long', expanded_prompt)
    return expanded_prompt

def extract_answer(answer):
    return answer['choices'][0]['message']['content']

def ask_chatgpt(context):
    answer = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=context)
    print(answer)
    return extract_answer(answer)

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

    if message.content.startswith('Hey '):
        answer = create_character(message.content)
        print(answer)
        #history.append(message.content)
        text = answer['choices'][0]['message']['content']
        member = message.author
        await member.send(text)


    if message.content.startswith('Computer, can I see'):
        prompt = message.content[19:]
        expanded_prompt = expand_prompt(prompt)
        image_url = generate_image(expanded_prompt)
        await message.channel.send(image_url)

    elif message.content.startswith('Computer,'):
        answer = compose(message.content)
        print(answer)
        history.append(message.content)
        text = answer['choices'][0]['message']['content']
        await message.channel.send(text)

client.run(os.getenv('bot_token'))