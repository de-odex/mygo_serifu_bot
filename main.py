import discord
import json
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View



intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def text_process(text):
    # 对输入台词进行 HTML 编码
    encoded_text = to_unicode_escape(text)

    # 加载 JSON 数据
    with open('src/ocr_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

    # 搜索台词
    results = []
    for item in data['result']:
        if item['text'] in encoded_text:
            results.append({
                "episode": item["episode"],
                "frame_start": item["frame_start"],
                "frame_end": item["frame_end"],
                "segment_id": item["segment_id"]
            })

    # 返回搜索结果
    return results



def to_unicode_escape(text):
    """将中文字符转换为 Unicode 转义字符"""
    return ''.join([f"\\u{ord(c):04x}" for c in text])



def unicode_to_string(encoded_text):
    """将 Unicode 转义字符转换为中文字符"""
    return bytes(encoded_text, "utf-8").decode("unicode_escape")



@bot.tree.command(name="mygo", description="尋找MyGO梗圖")
async def mygo(interaction: discord.Interaction, text: str):
    results = text_process(text)
    



bot.run('OTU1NDU3OTU1OTk2NzgyNjUy.GELCIA.CaNXW0bLwQTUCQJYYjgMUYAaTMYv7Ud7IWVtzg')
