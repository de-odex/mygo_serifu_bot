import discord
import json
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
import sub_process
import os
import logging


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
    except Exception as e:
        print(e)


def text_process(text):
    # 加载 JSON 数据
    with open('src/ocr_data_3.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    # 搜索台词
    results = []
    for item in data['result']:
         if text in item['text']:
            results.append({
                "text": item["text"],
                "episode": item["episode"],
                "frame_start": item["frame_start"],
                "frame_end": item["frame_end"],
            })


    # 返回搜索结果
    return results





async def text_autocompletion(interaction: discord.Interaction, current: str):
    # 假设 text_process 返回包含字典的列表
    results = text_process(current)
    # 筛选出包含当前输入的文本
    filtered_results = [entry['text'] for entry in results if current in entry['text']]
    # 返回自动完成建议
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
async def mygo(interaction: discord.Interaction, text: str, second: float= 0.0):
    result = text_process(text)
    await interaction.response.defer()
    episode = result[0]['episode']
    frame_start = result[0]['frame_start']
    frame_end = result[0]['frame_end']
    image = sub_process.extract_frame(episode=episode, frame_number=frame_start, back_seconds=second)
    await interaction.followup.send(file=discord.File(fp=image))
    os.remove(image)
    



bot.run('OTY0NDI0OTE2MzI3ODgyNzgy.GjxlFc.om4Gk3GmAJqpEBA6lCeWHymMvW_QDZlmc1rJGU')
