# This example requires the 'message_content' intent.
import ast
import atexit
import json
from dataclasses import dataclass
import openai
import os
import discord
from fuzzywuzzy import fuzz

openai.api_key = os.getenv('openaikey')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

players = {}

characters = {}

characters_history = {}

characters_history['paranoiagamemaster'] = []
characters_history['Computer'] = []

def closest_name(target):
    scored_names = [(fuzz.partial_ratio(target, name), name) for name in characters.keys()]
    closest = sorted(scored_names)[-1]
    return closest[1]

def decide_to_introduce_character(summary):
    messages = [
        {"role": "system", "content": "You are the game master in the roleplaying game Paranoia."},
        {"role": "user", "content": f"I will provide you with a summary of a story and you will decide \
        if a character needs to be fleshed out for the purpose of the story, \
        which can happen when a single character interacts with the player or does something in a scene. \
        Please only answer with Yes or No. The summary is: {summary}"}
    ]
    answer = ask_chatgpt(messages)
    if 'yes' in answer.lower():
        info, name = create_character(f"The following summary should inspire you to introduce a character: {summary}")
        return name, info
    
    return 'Nope', 'Nope'

def summarize(old_messages, degree = ''):
    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes conversations."}
    ]
    messages.append({"role": "user", "content":"I will pass to you messages happening in a roleplaying game and you will summarize them at the end."})
    
    add_to_context_from_history(messages, old_messages)

    messages.append({"role": "user", "content":f"Please write a{degree} concise bullet point summary of what happened so far in this roleplaying game."})

    summary = ask_chatgpt(messages)
    summary = summary + " The previous points are summarized events that have happened so far for context. Please ask the players what they do from now on."
    return summary    

def add_to_context_from_history(messages, history):
    for who, past in history:        
        if who == 'gpt':
            current = {"role": "assistant", "content": past}
        else:
            current = {"role": "user", "content": past}
        messages.append(current)
    return messages

def manage_game(message, speaker = None):
    messages = [
        {"role": "system", "content": "You are the game master in the roleplaying game Paranoia."},
        {"role": "user", "content":"According to my questions, you will describe what the world is like, \
                handle what events occur, ask me how I react, and help me create dramatic moments. \
                There are a few players interacting with you and you should never act as the player characters. \
                Do not normally reveal information that may be secret as all characters may understand what you say. \
                Please only speak as if you are the game master in the roleplaying game and always ask me how I react."}    
    ]

    for author, character in players.items():
        messages.append({"role": "user", 
                         "content": f'Game master, here is a description of a player character that you cannot control: {character[1]}'})
                                  
    history = characters_history['paranoiagamemaster']
                
    add_to_context_from_history(messages, history)

    if speaker in players:
        messages.append({"role": "user", 
                         "content": message.replace('Game master,', f"Game master, this is {players[speaker][0]} speaking,")})
    else:
        messages.append({"role": "user", "content": message})

    history.append(('player', message))
    answer = ask_chatgpt(messages, raw = True)
    history.append(('gpt', extract_answer(answer)))

    handle_many_tokens(answer, history)

    if len(history) > 15:
        compress_history(history)

    return extract_answer(answer)

def create_character(optional_info):
    messages = [
        {"role": "system", "content": "You are the game master in the roleplaying game Paranoia."}
    ]
    
    messages.append({"role": "user", "content": 
                    f"Provide a description of a citizen living in the dystopic city of Alpha Complex. \
                    Describe what speaking style and accent they adopt and what area or department they work in. \
                    Optionally, mention a secret society or a mutant power. Most citizens do not have powers. \
                    Provide name and clearance level in the format Name: <name>-<ID>, Clearance: <color>. \n{optional_info}"})

    answer = ask_chatgpt(messages)
    name = answer.split('Name: ')[1].split(',')[0]
    characters[name] = answer
    characters_history[name] = []
    return answer, name

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
    
    add_to_context_from_history(messages, history)
    messages.append({"role": "user", "content": message})

    history.append(('player', message))
    answer = ask_chatgpt(messages)
    history.append(('gpt', answer))
    cull_history(history)

    return answer

# maybe keep the old summary?
def compress_history(history, degree = ''):
    summary = summarize(history, degree)
    to_save = history[-2:]
    history.clear()
    history.append(('player', summary))
    history.extend(to_save)

def handle_many_tokens(answer, history):
    if history:
        total_tokens = answer['usage']['total_tokens'] 
        if total_tokens > 3700:
            if len(history) < 4:
                compress_history(history, degree = 'n extremely')
            compress_history(history)        
        
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

def ask_chatgpt(context, raw = False):
    answer = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=context)
    print(answer)
    if raw:
        return answer 
    return extract_answer(answer)

def ask_computer(message):
    messages = [
        {"role": "system", "content": "You are the Computer managing Alpha Complex from the roleplaying game Paranoia."}    
    ]

    history = characters_history['Computer']

    add_to_context_from_history(messages, history)

    messages.append({"role": "user", "content": message})

    answer = ask_chatgpt(messages)
    history.append(('player', message))
    history.append(('gpt', answer))
    cull_history(history)
    
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

    if message.content.startswith('(decide_character)'):
        summary = summarize(characters_history["paranoiagamemaster"])
        name, info = decide_to_introduce_character(summary)
        await message.channel.send(info)

    if message.content.startswith('(generate)'):
        text, name = create_character()
        member = message.author
        await member.send(text)

    if message.content.startswith('register_character:'):
        member = message.author
        content = message.content[len('register_character:'):]

        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        messages.append({"role": "user", "content": f"What is the name of the following character: {content}. Please only reply with the name alone without punctuation."})
        answer = ask_chatgpt(messages)

        players[member.name] = (answer, content)

        await member.send(f'{answer} registered. If the name is wrong, please register again with a clearer indication of your name')

    if message.content.startswith('Psst, hey, '):
        text = ask_character(message)

        mode = 'whisper'
        if mode == 'whisper':
            member = message.author
            await member.send(text)
        else:
            await message.channel.send(text)
    
    if message.content.startswith('(summarise)'):
        print(characters_history["paranoiagamemaster"])
        answer = summarize(characters_history["paranoiagamemaster"])
        await message.channel.send(answer)

    if message.content.startswith('Game master,') or message.content.startswith('GM,'):
        content = message.content
        content = content.replace('GM,', 'Game master,')
        answer = manage_game(content, speaker = message.author.name)
        await message.channel.send(answer)

    if message.content.startswith('Computer, can I see'):
        prompt = message.content[19:]
        expanded_prompt = expand_prompt(prompt)
        image_url = generate_image(expanded_prompt)
        await message.channel.send(image_url)

    elif message.content.startswith('Computer,'):
        answer = ask_computer(message.content)
        await message.channel.send(answer)

@atexit.register
def save_state():
    with open('backup_characters.json', 'w') as opened:
        opened.write(json.dumps(characters))
    with open('backup_history.json', 'w') as opened:
        opened.write(json.dumps(characters_history))
    with open('backup_players.json', 'w') as opened:
        opened.write(json.dumps(players))

loading = True

def main():
    try: 
        if loading: 
            with open('backup_characters.json', 'r') as opened:
                characters.update(json.loads(opened.read()))
            with open('backup_history.json', 'r') as opened:
                characters_history.update(json.loads(opened.read()))
            with open('backup_players.json', 'r') as opened:
                players.update(json.loads(opened.read()))
    except:
        print('Nothing to load')

    client.run(os.getenv('bot_token'))

main()