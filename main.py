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
import asyncio
import logging



load_dotenv()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
error_gif_link = 'https://raw.githubusercontent.com/eason102/mygo_serifu_bot/refs/heads/main/src/error.gif'


#logging
log_filename = datetime.now().strftime("logs/%Y-%m-%d.log")  
logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s --> %(levelname)s: %(message)s',  
    datefmt='%Y-%m-%d %H:%M:%S',  
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),  
        logging.StreamHandler() 
    ]
)

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    server_count = len(bot.guilds)
    logging.info(f"已上線: {bot.user} | 在 {server_count} 個伺服器中")
    update_status.start()



@tasks.loop(minutes=15)  
async def update_status():
    server_count = len(bot.guilds)
    record(None)
    with open('logs/ranks.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    times = data['times']
    await bot.change_presence(activity=discord.CustomActivity(name=f'GO了{times}次 | {server_count} 個伺服器'))
    logging.info(f'伺服器狀態更新為: GO了{times}次 | {server_count} 個伺服器')


def text_process(text):
    with open('src/ocr_data_3.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    results = []
    for item in data['result']:
         if text.lower() in item['text'].lower():
            results.append({
                "text": item["text"],
                "episode": item["episode"],
                "frame_start": item["frame_start"],
                "frame_end": item["frame_end"],
            })
    return results



async def text_autocompletion(interaction: discord.Interaction, current: str):
    results = text_process(current)
    filtered_results = [entry['text'] for entry in results if current.lower() in (entry['text']).lower()]
    data = []
    c= 1
    for item in filtered_results:
        c=c+1
        if len(item) < 100:
            data.append(discord.app_commands.Choice(name=item, value=item))
        if c == 20 :
            break
    return data



def record(text):

    if not os.path.exists('logs/ranks.json'):
        with open('logs/ranks.json', 'w', encoding='utf-8') as f:
            json.dump({"title": [], "times": 0}, f, indent=4, ensure_ascii=False)
    

    with open('logs/ranks.json', 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"title": [], "times": 0} 
    
    if text == None:
        return

    # 更新
    data['times'] += 1
    for item in data['title']:
        if item['text'] == text:
            item['times'] += 1
            break
    else:
        new_record = {"text": text, "times": 1}
        data['title'].append(new_record)
        
    

    with open('logs/ranks.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        



def run_ffmpeg_sync(episode, timestamp, end_frame):
    palettegen = ffmpeg.input(filename=f'src/{episode}.mp4', ss=timestamp) \
        .trim(start_frame=0, end_frame=end_frame + 1.0) \
        .filter(filter_name='scale', width=-1, height=720) \
        .filter(filter_name='palettegen', stats_mode='diff')
    
    scale = ffmpeg.input(filename=f'src/{episode}.mp4', ss=timestamp) \
        .filter(filter_name='scale', width=-1, height=720)
    
    try:
        buffer2, error = ffmpeg.filter([scale, palettegen], filter_name='paletteuse', dither='bayer', diff_mode='rectangle') \
            .output('pipe:1', vframes=round(end_frame + 1.0), format='gif', vcodec='gif') \
            .global_args('-loglevel', 'error') \
            .run(capture_stdout=True)
        return buffer2, error
    except ffmpeg.Error as e:
        return None, str(e)



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
        logging.info(f"{timestamp}-->伺服器ID: {interaction.guild_id} 未找到台詞{text}")
        return
    start_time = datetime.now()
    await interaction.response.defer()
    for item in result:
        if len(item['text']) < 100:
            if item['text'] == text:
                episode = item['episode']
                frame_number = item['frame_start']
                back_frames = second * 23.98
                frame_number = frame_number + back_frames + 5
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
                    logging.error(f'伺服器ID: {interaction.guild_id} 台詞: {text} 錯誤: {error}')
                    return
                #send
                await interaction.followup.send(file=discord.File(fp=io.BytesIO(buffer), filename=f'{str(frame_number)}.png'))
                end_time = datetime.now()
                timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
                run_time = end_time - start_time
                total_seconds = run_time.total_seconds()
                logging.info(f"伺服器ID: {interaction.guild_id} 台詞: {text} 耗時: {total_seconds:.3f} 秒")
                record(result[0])
                break
    

@bot.tree.command(name="mygogif", description="搜尋MyGO台詞並製作GIF")
@app_commands.autocomplete(text=text_autocompletion)
@app_commands.describe(text="需要尋找的台詞")
@app_commands.describe(duration="製作GIF的秒數(可小數點)-未填預設1.5秒-最大3秒")
async def mygogif(interaction: discord.Interaction, text: str, duration: float= 1.5):
    if duration > 3.0:
        embed = discord.Embed(title="❌錯誤",description='GIF製作間隔最多3秒', color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    result = text_process(text)
    if len(result) == 0:
        embed = discord.Embed(title="❌錯誤",description='沒有你要找的台詞...', color=discord.Color.red())
        embed.set_image(url=error_gif_link)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    start_time = datetime.now()
    await interaction.response.defer()
    for item in result:
        if len(item['text']) < 100:
            if item['text'] == text:
                episode = item['episode']
                frame_number = item['frame_start']
                frame_number = frame_number + 15
                timestamp = frame_number / 23.98
                embed = discord.Embed(title="GIF製作中...",description='視畫面複雜程度，可能需要一些時間', color=discord.Color.green())
                msg = await interaction.followup.send(embed=embed,ephemeral=True)
                end_frame = duration * 23.98

                buffer2, error = await asyncio.to_thread(run_ffmpeg_sync, episode, timestamp, end_frame)

                if error:
                    embed = discord.Embed(title="❌錯誤",description='FFMPEG出事啦', color=discord.Color.red())
                    embed.set_image(url=error_gif_link)
                    # await msg.edit(embed=embed)
                    end_time = datetime.now()
                    timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
                    logging.info(f"伺服器ID: {interaction.guild_id} 台詞: {text} 錯誤: {error}")
                    return
                
                await msg.edit(embed = None, attachments=[discord.File(fp=io.BytesIO(buffer2), filename=f'{str(frame_number)}.gif')])
                end_time = datetime.now()
                timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
                run_time = end_time - start_time
                total_seconds = run_time.total_seconds()
                logging.info(f"伺服器ID: {interaction.guild_id} 台詞: {text} {str(duration)}秒GIF耗時: {total_seconds:.3f} 秒")
                record(result[0])
                break



bot.run(os.getenv('DISCORD_TOKEN'))

