import asyncio
import datetime
import io
import json
import logging
import os
from collections import Counter
from datetime import datetime

import discord
import ffmpeg
import requests
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
base_url = "https://mygo-api.yichen0403.us.kg/api"
API_TOKEN = os.getenv("API_TOKEN")


intents = discord.Intents.default()
bot = commands.AutoShardedBot(command_prefix="!", intents=intents)
error_gif_link = "https://raw.githubusercontent.com/eason102/mygo_serifu_bot/refs/heads/main/src/error.gif"


# logging
log_filename = datetime.now().strftime("logs/%Y-%m-%d.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s --> %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(),
    ],
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
    app_info = await bot.application_info()
    user_count = app_info.approximate_user_install_count
    response = requests.get(f"{base_url}/ranks/total")
    if response.status_code == 200:
        data = response.json()
        await bot.change_presence(
            activity=discord.CustomActivity(
                name="GO了{data['total_times']}次 | {server_count} 個伺服器"
            )
        )
        logging.info(
            f"伺服器狀態更新為: GO了{data['total_times']}次 | {server_count} 個伺服器"
        )
        response = requests.post(
            f"{base_url}/record_server_count",
            json={"server_count": server_count, "user_count": user_count},
        )
        if response.status_code == 200:
            logging.info(f"伺服器狀態更新成功: {response.status_code}")
        else:
            logging.error(f"伺服器狀態更新失敗: {response.status_code}")

    else:
        logging.error(f"伺服器狀態更新失敗: {response.status_code}")


def text_process(text):
    with open("src/ocr_data_3.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    results = []
    for item in data["result"]:
        if text.lower() in item["text"].lower():
            results.append(
                {
                    "text": item["text"],
                    "episode": item["episode"],
                    "frame_start": item["frame_start"],
                    "frame_end": item["frame_end"],
                }
            )
    return results


def text_process_precise(text):  # answer value
    try:
        text = json.loads(text)
        with open("src/ocr_data_3.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        results = []
        for item in data["result"]:
            try:
                if (
                    item["episode"] == text["episode"]
                    and item["frame_start"] == text["frame_start"]
                ):
                    results.append(
                        {
                            "text": item["text"],
                            "episode": item["episode"],
                            "frame_start": item["frame_start"],
                            "frame_end": item["frame_end"],
                        }
                    )
            except:
                pass
    except (
        Exception
    ) as e:  # 沒有點自動完成或是沒有此台詞會直接 傳入text本身，要傳回空清單，告訴使用者沒有此台詞
        results = []
    # print(results)
    return results


async def text_autocompletion(interaction: discord.Interaction, current: str):
    results = text_process(current)
    filtered_results = [
        entry for entry in results if current.lower() in entry["text"].lower()
    ]
    data = []
    count = 0

    text_counter = Counter(entry["text"] for entry in filtered_results)
    text_occurrence = {text: 0 for text in text_counter}

    for item in filtered_results:
        count += 1
        if len(item["text"]) < 95:
            if text_counter[item["text"]] > 1:
                text_occurrence[item["text"]] += 1
                name = f"{item['text']} ({text_occurrence[item['text']]})"
            else:
                name = item["text"]

            s_data = {
                "frame_start": item["frame_start"],
                "frame_end": item["frame_end"],
                "episode": item["episode"],
            }
            data.append(
                discord.app_commands.Choice(
                    name=name, value=json.dumps(s_data, ensure_ascii=False)
                )
            )

        if count == 20:
            break

    return data


def record(text):
    text = text[0]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_TOKEN}",
    }
    response = requests.post(f"{base_url}/ranks", json=text, headers=headers)
    if response.status_code == 200:
        logging.info(f"status code : {response.status_code} Data updated")
    else:
        logging.error(f"status code : {response.status_code} Data update failed")


def run_ffmpeg_sync(episode, timestamp, end_frame):
    palettegen = (
        ffmpeg.input(filename=f"src/{episode}.mp4", ss=timestamp)
        .trim(start_frame=0, end_frame=end_frame + 1.0)
        .filter(filter_name="scale", width=-1, height=720)
        .filter(filter_name="palettegen", stats_mode="diff")
    )

    scale = ffmpeg.input(filename=f"src/{episode}.mp4", ss=timestamp).filter(
        filter_name="scale", width=-1, height=720
    )

    try:
        buffer2, error = (
            ffmpeg.filter(
                [scale, palettegen],
                filter_name="paletteuse",
                dither="bayer",
                diff_mode="rectangle",
            )
            .output(
                "pipe:1", vframes=round(end_frame + 1.0), format="gif", vcodec="gif"
            )
            .global_args("-loglevel", "error")
            .run(capture_stdout=True)
        )
        return buffer2, error
    except ffmpeg.Error as e:
        return None, str(e)


@bot.tree.command(name="mygo", description="搜尋MyGO台詞")
@app_commands.autocomplete(text=text_autocompletion)
@app_commands.describe(text="需要尋找的台詞")
@app_commands.describe(second="延後秒數(可小數點)")
async def mygo(interaction: discord.Interaction, text: str, second: float = 0.0):
    result = text_process_precise(text)
    if len(result) == 0:
        embed = discord.Embed(
            title="❌錯誤",
            description="請再試一次，或是沒有你要找的台詞...",
            color=discord.Color.red(),
        )
        embed.set_image(url=error_gif_link)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return
    start_time = datetime.now()
    await interaction.response.defer()
    episode = result[0]["episode"]
    frame_number = result[0]["frame_start"]
    back_frames = second * 23.98
    frame_number = frame_number + back_frames + 15
    timestamp = frame_number / 23.98
    # ffmpeg-python
    buffer, error = (
        ffmpeg.input(filename=f"src/{str(episode)}.mp4", ss=timestamp)
        .output("pipe:", vframes=1, format="image2", vcodec="png")
        .global_args("-loglevel", "error")
        .run(capture_stdout=True)
    )
    if error:
        embed = discord.Embed(
            title="❌錯誤.", description="FFMPEG出事啦", color=discord.Color.red()
        )
        embed.set_image(url=error_gif_link)
        await interaction.followup.send(embed=embed)
        logging.error(
            f"伺服器ID: {interaction.guild_id} 台詞: {result['text']} 錯誤: {error}"
        )
        return
    # send
    await interaction.followup.send(
        file=discord.File(fp=io.BytesIO(buffer), filename=f"{str(frame_number)}.png")
    )
    end_time = datetime.now()
    timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
    run_time = end_time - start_time
    total_seconds = run_time.total_seconds()
    logging.info(
        f"伺服器ID: {interaction.guild_id} 台詞: {result[0]['text']} 耗時: {total_seconds:.3f} 秒"
    )
    record(result)


@bot.tree.command(name="mygogif", description="搜尋MyGO台詞並製作GIF")
@app_commands.autocomplete(text=text_autocompletion)
@app_commands.describe(text="需要尋找的台詞")
@app_commands.describe(duration="製作GIF的秒數(可小數點)-未填預設1.5秒-最大3秒")
async def mygogif(interaction: discord.Interaction, text: str, duration: float = 1.5):
    if duration > 3.0:
        embed = discord.Embed(
            title="❌錯誤", description="GIF製作間隔最多3秒", color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    result = text_process_precise(text)
    if len(result) == 0:
        embed = discord.Embed(
            title="❌錯誤",
            description="請再試一次，或是沒有你要找的台詞...",
            color=discord.Color.red(),
        )
        embed.set_image(url=error_gif_link)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    start_time = datetime.now()
    await interaction.response.defer()
    episode = result[0]["episode"]
    frame_number = result[0]["frame_start"]
    frame_number = frame_number + 8
    timestamp = frame_number / 23.98
    embed = discord.Embed(
        title="GIF製作中...",
        description="視畫面複雜程度，可能需要一些時間",
        color=discord.Color.green(),
    )
    msg = await interaction.followup.send(embed=embed, ephemeral=True)
    end_frame = duration * 23.98

    buffer2, error = await asyncio.to_thread(
        run_ffmpeg_sync, episode, timestamp, end_frame
    )

    if error:
        embed = discord.Embed(
            title="❌錯誤", description="FFMPEG出事啦", color=discord.Color.red()
        )
        embed.set_image(url=error_gif_link)
        # await msg.edit(embed=embed)
        end_time = datetime.now()
        timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
        logging.info(
            f"伺服器ID: {interaction.guild_id} 台詞: {result['text']} 錯誤: {error}"
        )
        return

    await msg.edit(
        embed=None,
        attachments=[
            discord.File(fp=io.BytesIO(buffer2), filename=f"{str(frame_number)}.gif")
        ],
    )
    end_time = datetime.now()
    timestamp = end_time.strftime("%Y-%m-%d %H:%M:%S")
    run_time = end_time - start_time
    total_seconds = run_time.total_seconds()
    logging.info(
        f"伺服器ID: {interaction.guild_id} 台詞: {result[0]['text']} {str(duration)}秒GIF耗時: {total_seconds:.3f} 秒"
    )
    record(result)


bot.run(os.getenv("DISCORD_TOKEN"))
