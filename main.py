import discord
import json
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
import sub_process
import os
from dotenv import load_dotenv
import datetime
from datetime import datetime
import time

load_dotenv()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)



@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
    except Exception as e:
        print(e)



def text_process(text):
    with open('src/ocr_data_3.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    results = []
    for item in data['result']:
         if text in item['text']:
            results.append({
                "text": item["text"],
                "episode": item["episode"],
                "frame_start": item["frame_start"],
                "frame_end": item["frame_end"],
            })
    return results



async def text_autocompletion(interaction: discord.Interaction, current: str):
    results = text_process(current)
    filtered_results = [entry['text'] for entry in results if current in entry['text']]
    data = []
    c= 1
    for item in filtered_results:
        c=c+1
        data.append(discord.app_commands.Choice(name=item, value=item))
        if c == 20 :
            break
    return data



@bot.tree.command(name="mygo", description="尋找MyGO台詞")
@app_commands.autocomplete(text=text_autocompletion)
@app_commands.describe(text="需要尋找的台詞")
@app_commands.describe(second="延後秒數(可小數點)")
async def mygo(interaction: discord.Interaction, text: str, second: float= 0.0):
    result = text_process(text)
    start_time = datetime.now()
    await interaction.response.defer()
    episode = result[0]['episode']
    frame_start = result[0]['frame_start']
    image = sub_process.extract_frame(episode=episode, frame_number=frame_start, back_seconds=second)
    try:
        await interaction.followup.send(file=discord.File(fp=image))
        os.remove(image)
        end_time = datetime.now()
        timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
        run_time = end_time - start_time
        total_seconds = run_time.total_seconds()
        print(f"{timestamp}-->伺服器ID: {interaction.guild_id} 台詞: {text} 耗時: {total_seconds:.3f} 秒")
    except Exception as e:
        await interaction.followup.send("發生錯誤")
        print(f"{timestamp}--> 伺服器ID: {interaction.guild_id} 台詞: {text} 錯誤: {e}")
    


bot.run(os.getenv('DISCORD_TOKEN'))

