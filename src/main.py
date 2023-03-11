# This example requires the 'message_content' intent.
from dataclasses import dataclass
import openai
import os
import discord
from fuzzywuzzy import fuzz

openai.api_key = os.getenv('openaikey')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

computer_history = []

characters = {}

characters_history = {}

def closest_name(target):
    scored_names = [(fuzz.partial_ratio(target, name), name) for name in characters.keys()]
    closest = sorted(scored_names)[-1]
    return closest[1]

def create_character():
    messages = [
        {"role": "system", "content": "You are the game master in the roleplaying game Paranoia."}
    ]
    
    messages.append({"role": "user", "content": 
                    'Provide a description of a citizen living in the dystopic city of Alpha Complex. \
                    Describe what speaking style and accent they adopt and what area or department they work in. \
                    Optionally, mention a secret society or a mutant power. Most citizens do not have powers. \
                    Provide name and clearance level in the format Name: <name>-<ID>, Clearance: <color>'})

    answer = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    answer = extract_answer(answer)
    name = answer.split('Name: ')[1].split(',')[0]
    characters[name] = answer
    characters_history[name] = []
    print(name)
    return answer

# Need to add a bit that describes the speaker
def ask_character(message):
    message = message.content
    name = message.split('Hey ')[1].split(',')[0]
    correct_name = closest_name(name)
    description = characters[correct_name]
    history = characters_history[correct_name]
    messages = [
        {"role": "system", "content": "You speak as in a roleplaying game of Paranoia."},
        {"role": "user", "content": f"You will roleplay as the following character: {description}"},
        {"role": "assistant", "content": f"Great, I'd love to roleplay as {correct_name} and I will pay great attention to the character speaking style."},
    ]

    for who, past in history:        
        if who == 'gpt':
            current = {"role": "assistant", "content": past}
        else:
            current = {"role": "user", "content": past}
        messages.append(current)
    messages.append({"role": "user", "content": message})

    print(messages)

    history.append(('player', message))
    answer = ask_chatgpt(messages)
    history.append(('gpt', answer))
    cull_history(history)

    return answer

def cull_history(history):
    if len(history) > 30:
        goodbye = history.pop(0)

def generate_image(message):
    response = openai.Image.create(prompt=message, n=1, size="512x512")
    image_url = response['data'][0]['url']
    return image_url

def expand_prompt(message):
    messages = [
        {"role": "system", "content": "You are a helpful prompt writing assistant for Dall-e. You only write exact Dall-e prompts."}    
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

def ask_computer(message):
    if len(computer_history) > 30:
        goodbye = computer_history.pop(0)
    
    messages = [
        {"role": "system", "content": "You are the Computer managing Alpha Complex from the roleplaying game Paranoia."}    
    ]

    for past in computer_history:
        if past.startswith('Computer,'):
            current = {"role": "user", "content": past}
        else:
            current = {"role": "assistant", "content": past}
        messages.append(current)
    messages.append({"role": "user", "content": message})

    answer = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    computer_history.append(answer['choices'][0]['message']['content'])
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

    if message.content.startswith('(generate)'):
        text = create_character()
        member = message.author
        await member.send(text)

    if message.content.startswith('Hey '):
        text = ask_character(message)

        mode = 'from'
        if mode == 'whisper':
            member = message.author
            await member.send(text)
        else:
            await message.channel.send(text)
        
    if message.content.startswith('Computer, can I see'):
        prompt = message.content[19:]
        expanded_prompt = expand_prompt(prompt)
        image_url = generate_image(expanded_prompt)
        await message.channel.send(image_url)

    elif message.content.startswith('Computer,'):
        answer = ask_computer(message.content)
        print(answer)
        computer_history.append(message.content)
        text = answer['choices'][0]['message']['content']
        await message.channel.send(text)

client.run(os.getenv('bot_token'))