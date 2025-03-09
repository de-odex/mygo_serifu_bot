import asyncio
import datetime
import io
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import discord
import ffmpeg
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from loguru import logger

import api

load_dotenv()

self_path = Path(__file__)
project_path = self_path.parent.parent
assets_path = project_path / "assets"
error_gif_link = "https://raw.githubusercontent.com/eason102/mygo_serifu_bot/refs/heads/main/src/error.gif"

intents = discord.Intents.default()
bot = commands.AutoShardedBot(command_prefix="!", intents=intents)

logger.add(
    (project_path / "logs" / self_path.stem).with_suffix("log"),
    rotation="at 00:00",
    retention="7 days",
    compression="lzma",
)


@bot.event
async def on_ready():
    await bot.tree.sync()
    server_count = len(bot.guilds)
    logger.info(f"Online: {bot.user} | in {server_count} servers")
    api.update_status.start(bot)


def text_process(text):
    with open(assets_path / "ocr_data_3.json", "r", encoding="utf-8") as f:
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
        with open(assets_path / "ocr_data_3.json", "r", encoding="utf-8") as f:
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
    except Exception as e:
        # If there is no autocomplete suggestion or if the specified line does
        # not exist, the text itself will be directly passed in.
        # An empty list should be returned to inform the user that the specified
        # line does not exist.
        # (Wow, translating Chinese comments into English directly is quite the
        # experience)
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


def run_ffmpeg_sync(episode, timestamp, end_frame):
    palettegen = (
        ffmpeg.input(filename=assets_path / f"{episode}.mp4", ss=timestamp)
        .trim(start_frame=0, end_frame=end_frame + 1.0)
        .filter(filter_name="scale", width=-1, height=720)
        .filter(filter_name="palettegen", stats_mode="diff")
    )

    scale = ffmpeg.input(filename=assets_path / f"{episode}.mp4", ss=timestamp).filter(
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


@bot.tree.command(name="mygo", description="Search for MyGO lines")
@app_commands.autocomplete(text=text_autocompletion)
@app_commands.describe(text="The line to search for")
@app_commands.describe(second="Delayed seconds (can be decimal)")
async def mygo(interaction: discord.Interaction, text: str, second: float = 0.0):
    result = text_process_precise(text)
    if len(result) == 0:
        embed = discord.Embed(
            title="❌Error",
            description="Please try again, or the line you are looking for does not exist...",
            color=discord.Color.red(),
        )
        embed.set_image(url=error_gif_link)
        await interaction.response.send_message(embed=embed, ephemeral=True)
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
        ffmpeg.input(filename=assets_path / f"{episode}.mp4", ss=timestamp)
        .output("pipe:", vframes=1, format="image2", vcodec="png")
        .global_args("-loglevel", "error")
        .run(capture_stdout=True)
    )
    if error:
        embed = discord.Embed(
            title="❌Error",
            description="Something happened to FFMPEG",
            color=discord.Color.red(),
        )
        embed.set_image(url=error_gif_link)
        await interaction.followup.send(embed=embed)
        logger.error(
            f"Server ID: {interaction.guild_id} Line: {result['text']} Error: {error}"
        )
        return
    # send
    await interaction.followup.send(
        file=discord.File(fp=io.BytesIO(buffer), filename=f"{str(frame_number)}.png")
    )
    end_time = datetime.now()
    run_time = end_time - start_time
    total_seconds = run_time.total_seconds()
    logger.info(
        f"Server ID: {interaction.guild_id} Line: {result[0]['text']} Time taken: {total_seconds:.3f} seconds"
    )
    api.record(result)


@bot.tree.command(name="mygogif", description="Search for MyGO lines and create GIFs")
@app_commands.autocomplete(text=text_autocompletion)
@app_commands.describe(text="The line to search for")
@app_commands.describe(
    duration="Number of seconds to make GIF (decimal point) - default 1.5 s, max 3 s."
)
async def mygogif(interaction: discord.Interaction, text: str, duration: float = 1.5):
    if duration > 3.0:
        embed = discord.Embed(
            title="❌Error",
            description="The maximum interval for GIF creation is 3 seconds.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    result = text_process_precise(text)
    if len(result) == 0:
        embed = discord.Embed(
            title="❌Error",
            description="Please try again, or the line you are looking for does not exist...",
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
        title="GIF is being produced...",
        description="Depending on the complexity of the picture, it may take some time.",
        color=discord.Color.green(),
    )
    msg = await interaction.followup.send(embed=embed, ephemeral=True)
    end_frame = duration * 23.98

    buffer2, error = await asyncio.to_thread(
        run_ffmpeg_sync, episode, timestamp, end_frame
    )

    if error:
        embed = discord.Embed(
            title="❌Error",
            description="Something happened to FFMPEG",
            color=discord.Color.red(),
        )
        embed.set_image(url=error_gif_link)
        # await msg.edit(embed=embed)
        logger.info(
            f"Server ID: {interaction.guild_id} Line: {result['text']} Error: {error}"
        )
        return

    await msg.edit(
        embed=None,
        attachments=[
            discord.File(fp=io.BytesIO(buffer2), filename=f"{str(frame_number)}.gif")
        ],
    )
    end_time = datetime.now()
    run_time = end_time - start_time
    total_seconds = run_time.total_seconds()
    logger.info(
        f"Server ID: {interaction.guild_id} Line: {result[0]['text']} Duration: {str(duration)} seconds GIF processing time: {total_seconds:.3f} seconds"
    )
    api.record(result)


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
