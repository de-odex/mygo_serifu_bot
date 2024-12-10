import discord
import json
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import datetime
from datetime import datetime
import ffmpeg
import io
from discord.ext import commands, tasks



load_dotenv()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
error_gif_link = 'https://raw.githubusercontent.com/eason102/mygo_serifu_bot/refs/heads/main/src/error.gif'


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    server_count = len(bot.guilds)
    activity = discord.Game(f"{server_count} 個伺服器")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"已上線: {bot.user} | 在 {server_count} 個伺服器中")
    update_status.start()



@tasks.loop(minutes=60)  
async def update_status():
    server_count = len(bot.guilds)
    activity = discord.Game(f"{server_count} 個伺服器")
    await bot.change_presence(status=discord.Status.online, activity=activity)



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
        if len(item) < 100:
            data.append(discord.app_commands.Choice(name=item, value=item))
        if c == 20 :
            break
    return data



@bot.tree.command(name="mygo", description="搜尋MyGO台詞")
@app_commands.autocomplete(text=text_autocompletion)
@app_commands.describe(text="需要尋找的台詞")
@app_commands.describe(second="延後秒數(可小數點)")
async def mygo(interaction: discord.Interaction, text: str, second: float= 0.0):
    result = text_process(text)
    if len(result) == 0:
        embed = discord.Embed(title="❌錯誤",description='沒有你要找的台詞...', color=discord.Color.red())
        embed.set_image(url=error_gif_link)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp}-->伺服器ID: {interaction.guild_id} 未找到台詞{text}")
        return
    start_time = datetime.now()
    await interaction.response.defer()
    episode = result[0]['episode']
    frame_number = result[0]['frame_start']
    back_frames = second * 23.98
    frame_number = frame_number + back_frames + 15
    timestamp = frame_number / 23.98
    #ffmpeg-python
    buffer, error = ffmpeg.input(filename=f'src/{str(episode)}.mp4', ss=timestamp) \
            .output('pipe:', vframes=1, format='image2', vcodec='png') \
            .global_args('-loglevel', 'error')\
            .run(capture_stdout=True)
    if error:
        embed = discord.Embed(title="❌錯誤.",description='FFMPEG出事啦', color=discord.Color.red())
        embed.set_image(url=error_gif_link)
        await interaction.followup.send(embed=embed)
        end_time = datetime.now()
        timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp}-->伺服器ID: {interaction.guild_id} 台詞: {text} 錯誤: {error}")
        return
    #send
    await interaction.followup.send(file=discord.File(fp=io.BytesIO(buffer), filename=f'{str(frame_number)}.png'))
    end_time = datetime.now()
    timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
    run_time = end_time - start_time
    total_seconds = run_time.total_seconds()
    print(f"{timestamp}-->伺服器ID: {interaction.guild_id} 台詞: {text} 耗時: {total_seconds:.3f} 秒")

    


bot.run(os.getenv('DISCORD_TOKEN'))

